"""
diagnose_submission.py -- read a submission CSV and say where the points are.

    python diagnose_submission.py submission.csv
    python diagnose_submission.py submission.csv --no-check   # skip validation

It recomputes everything from the coordinates (it does not trust the file),
scores each puzzle exactly as the leaderboard does, and ranks the puzzles by
how much score you are still leaving on the table.

The point is to answer one question: *what do I do next?* -- not to admire the
total.
"""

from __future__ import annotations

import argparse
import csv
import sys

import numpy as np

import squares_core as sc

# published best-known s(n) for n <= 20 (Friedman DS7 / squaremath.org frontier)
BEST_KNOWN = {
    1: 1.0, 2: 2.0, 3: 2.0, 4: 2.0,
    5: 2 + 0.5 ** 0.5, 6: 3.0, 7: 3.0, 8: 3.0, 9: 3.0,
    10: 3 + 0.5 ** 0.5, 11: 3.87708359, 12: 4.0, 13: 4.0, 14: 4.0, 15: 4.0,
    16: 4.0, 17: 4.67553009, 18: 4.822875655, 19: 4.885618083, 20: 5.0,
}
# puzzles whose optimum is proved -- no score is available there
PROVED = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16}


def load(path):
    rows: dict[int, list[tuple[float, float, float]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n = int(r["n"])
            rows.setdefault(n, []).append(
                (float(r["x"]), float(r["y"]), float(r["angle"]))
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--no-check", action="store_true",
                    help="skip the overlap check (much faster)")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    rows = load(args.path)
    print(f"file      : {args.path}")
    print(f"puzzles   : {len(rows)} / 1000")
    print()

    per = {}          # n -> (L, score, status)
    bad = []
    for n in range(1, 1001):
        g = sc.grid_side(n)
        gscore = g / np.sqrt(n) - 1.0
        if n not in rows or len(rows[n]) != n:
            per[n] = (float(g), gscore, "missing")
            continue
        xy = np.array([(x, y) for x, y, _ in rows[n]])
        th = np.array([t for _, _, t in rows[n]])
        if not np.isfinite(xy).all() or not np.isfinite(th).all():
            per[n] = (float(g), gscore, "non-finite")
            bad.append(n)
            continue
        if args.no_check:
            L, status = sc.container_side(xy, th), "packed"
        else:
            ok, info = sc.is_valid(xy, th)
            if not ok:
                per[n] = (float(g), gscore,
                          f"invalid (pen {info['max_penetration']:.1e})")
                bad.append(n)
                continue
            L, status = info["L"], "packed"
        per[n] = (L, L / np.sqrt(n) - 1.0, status)

    total = sum(v[1] for v in per.values())
    grid_total = sum(sc.grid_side(n) / np.sqrt(n) - 1.0 for n in range(1, 1001))

    print(f"total score   : {total:.10f}")
    print(f"grid baseline : {grid_total:.10f}   "
          f"(you are {grid_total - total:+.4f} against it)")
    print(f"floor         : 0.0000000000   "
          f"({total / grid_total * 100:.1f}% of the baseline still there)")
    nbad = sum(1 for v in per.values() if v[2] != "packed")
    if nbad:
        print(f"charged grid  : {nbad} puzzles "
              f"({sum(per[n][1] for n in per if per[n][2] != 'packed'):.4f} of score)")
    print()

    # ---- where the total comes from -------------------------------------
    print("where your total comes from")
    for lo, hi in [(1, 20), (21, 100), (101, 300), (301, 600), (601, 1000)]:
        s = sum(per[n][1] for n in range(lo, hi + 1))
        print(f"  n {lo:>4}-{hi:<5} {s:8.4f}   {s / total * 100:5.1f}%")
    print()

    # ---- biggest liabilities --------------------------------------------
    print(f"biggest single scores (fix these first)  -- top {args.top}")
    print(f"{'n':>5} {'L':>10} {'score':>9} {'ref s(n)':>9} "
          f"{'gap':>7}  note")
    order = sorted(per, key=lambda n: -per[n][1])
    for n in order[: args.top]:
        L, s, st = per[n]
        bk = BEST_KNOWN.get(n)
        if bk is None:
            ref_s, gap_s = "-", "-"
        else:
            ref_s = f"{sc.score(bk, n):.4f}"
            gap_s = f"{s - sc.score(bk, n):.4f}"

        if st != "packed":
            note = "NOT SUBMITTED"
            if n in PROVED:
                note += " (grid already optimal)"
        elif n in PROVED:
            note = "proved optimal"
        elif bk is not None:
            note = "OPEN -- room exists"
        else:
            note = "no published record"
        print(f"{n:>5} {L:>10.4f} {s:>9.4f} {ref_s:>9} {gap_s:>7}  {note}")
    print()

    # ---- biggest wins already banked ------------------------------------
    print("your biggest wins over the grid")
    print(f"{'n':>5} {'grid L':>7} {'your L':>9} {'saved':>8}")
    saved = sorted(((n, sc.grid_side(n) - per[n][0]) for n in per),
                   key=lambda t: -t[1])[: min(10, len(per))]
    for n, d in saved:
        if d <= 1e-9:
            break
        print(f"{n:>5} {sc.grid_side(n):>7} {per[n][0]:>9.4f} {d:>8.4f}")
    print()

    if bad:
        print(f"puzzles charged the grid ({len(bad)}): {bad[:20]}"
              + (" ..." if len(bad) > 20 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
