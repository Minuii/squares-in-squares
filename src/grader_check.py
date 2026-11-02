"""grader_check.py -- reject exactly what the Kaggle metric rejects.

The functions below follow metric/squares-in-squares (Apache 2.0): a float SAT
sorts near pairs into separated / overlapping / undecided, and undecided pairs
(within 1e-8) go to mpmath interval arithmetic at 50, 100, 200 and 500 digits.
A true overlap of any size fails the puzzle, and so does a contact that stays
undecided at 500 digits. A failed puzzle is charged the grid ceiling.

Kaggle reads the CSV as correctly rounded doubles, so a packing is checked as
repr(float), which is also what squares_core.write_submission emits.

    python src/grader_check.py submission_final.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import multiprocessing
import os

import mpmath

ESCALATION = (50, 100, 200, 500)
UNDECIDED_TOL = 1e-8
AABB_PAD = 1e-7


def _corners(cx, cy, c, s):
    h = 0.5
    dx1, dy1 = h * c - h * s, h * s + h * c
    dx2, dy2 = -h * c - h * s, -h * s + h * c
    return [(cx + dx1, cy + dy1), (cx + dx2, cy + dy2),
            (cx - dx1, cy - dy1), (cx - dx2, cy - dy2)]


def _float_pair(p, q):
    """'separated', 'overlapping' or 'undecided' for two (x, y, angle, corners)."""
    c1, s1 = math.cos(p[2]), math.sin(p[2])
    c2, s2 = math.cos(q[2]), math.sin(q[2])
    low = math.inf
    for ax, ay in ((c1, s1), (-s1, c1), (c2, s2), (-s2, c2)):
        a = [ax * x + ay * y for x, y in p[3]]
        b = [ax * x + ay * y for x, y in q[3]]
        overlap = min(max(a), max(b)) - max(min(a), min(b))
        if overlap < -UNDECIDED_TOL:
            return "separated"
        low = min(low, overlap)
    return "overlapping" if low > UNDECIDED_TOL else "undecided"


def _iv_min(values):
    return mpmath.iv.mpf([min(v.a for v in values), min(v.b for v in values)])


def _iv_max(values):
    return mpmath.iv.mpf([max(v.a for v in values), max(v.b for v in values)])


def _iv_le_zero(v):
    try:
        return v <= mpmath.iv.mpf("0")
    except ValueError:
        return None


def _iv_pair(a, b):
    """True if certified apart, False if certified overlapping, else None."""
    iv = mpmath.iv
    xi, yi, ti = iv.mpf(a[0]), iv.mpf(a[1]), iv.mpf(a[2])
    xj, yj, tj = iv.mpf(b[0]), iv.mpf(b[1]), iv.mpf(b[2])
    ci, si, cj, sj = iv.cos(ti), iv.sin(ti), iv.cos(tj), iv.sin(tj)
    h = iv.mpf("0.5")
    di =(h * ci - h * si, h * si + h * ci, -h * ci - h * si, -h * si + h * ci)
    dj = (h * cj - h * sj, h * sj + h * cj, -h * cj - h * sj, -h * sj + h * cj)
    pi = [(xi + di[0], yi + di[1]), (xi + di[2], yi + di[3]),
          (xi - di[0], yi - di[1]), (xi - di[2], yi - di[3])]
    pj = [(xj + dj[0], yj + dj[1]), (xj + dj[2], yj + dj[3]),
          (xj - dj[0], yj - dj[1]), (xj - dj[2], yj - dj[3])]

    undecided = False
    for ax, ay in ((ci, si), (-si, ci), (cj, sj), (-sj, cj)):
        p1 = [ax * x + ay * y for x, y in pi]
        p2 = [ax * x + ay * y for x, y in pj]
        lo1, hi1 = _iv_min(p1), _iv_max(p1)
        lo2, hi2 = _iv_min(p2), _iv_max(p2)
        verdict = _iv_le_zero(_iv_min([hi1, hi2]) - _iv_max([lo1, lo2]))
        if verdict is True:
            return True
        if verdict is None:
            undecided = True
    return None if undecided else False


def verify(rows: list[tuple[str, str, str]]) -> tuple[bool, str]:
    """rows: (x, y, angle) literals for one puzzle. (feasible, reason)."""
    sq = []
    x0, y0 = float(rows[0][0]), float(rows[0][1])
    for x, y, a in rows:
        dx, dy, t = float(x) - x0, float(y) - y0, float(a) % (2 * math.pi)
        sq.append((dx, dy, t, _corners(dx, dy, math.cos(t), math.sin(t))))

    boxes = []
    for i, s in enumerate(sq):
        xs = [c[0] for c in s[3]]
        ys = [c[1] for c in s[3]]
        boxes.append((min(xs) - AABB_PAD, min(ys) - AABB_PAD,
                      max(xs) + AABB_PAD, max(ys) + AABB_PAD, i))
    boxes.sort()

    near = []
    for u in range(len(boxes)):
        a = boxes[u]
        for v in range(u + 1, len(boxes)):
            b = boxes[v]
            if b[0] > a[2]:
                break
            if a[3] < b[1] or b[3] < a[1]:
                continue
            verdict = _float_pair(sq[a[4]], sq[b[4]])
            if verdict == "overlapping":
                return False, f"squares {a[4]},{b[4]} overlap (float)"
            if verdict == "undecided":
                near.append((a[4], b[4]))

    open_pairs = near
    for dps in ESCALATION:
        old_iv, old_mp = mpmath.iv.dps, mpmath.mp.dps
        mpmath.iv.dps = mpmath.mp.dps = dps
        try:
            left = []
            for i, j in open_pairs:
                verdict = _iv_pair(rows[i], rows[j])
                if verdict is False:
                    return False, f"squares {i},{j} overlap (certified)"
                if verdict is None:
                    left.append((i, j))
        finally:
            mpmath.iv.dps, mpmath.mp.dps = old_iv, old_mp
        open_pairs = left
        if not open_pairs:
            return True, "feasible"
    return False, f"{len(open_pairs)} contacts undecidable at 500 digits"


def _job(item):
    n, rows = item
    return (n, *verify(rows))


def rejected(puzzles: dict[int, list[tuple[str, str, str]]]) -> dict[int, str]:
    """n -> reason, for every puzzle the metric would refuse."""
    with multiprocessing.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        out = pool.map(_job, sorted(puzzles.items(), reverse=True), chunksize=4)
    return {n: why for n, ok, why in out if not ok}


def as_literals(xy, th) -> list[tuple[str, str, str]]:
    """Literals as the submission writer emits them for centred coordinates."""
    return [(repr(float(a)), repr(float(b)), repr(float(c)))
            for (a, b), c in zip(xy, th)]


def load(path: str) -> dict[int, list[tuple[str, str, str]]]:
    rows: dict[int, list[tuple[str, str, str]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # Kaggle reads doubles, so check the double behind each literal
            rows.setdefault(int(r["n"]), []).append(
                (repr(float(r["x"])), repr(float(r["y"])), repr(float(r["angle"]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    bad = rejected(load(args.path))
    print(f"{args.path}: {len(bad)} puzzles rejected")
    for n, why in sorted(bad.items())[:30]:
        print(f"  n={n}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
