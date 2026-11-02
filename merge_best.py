"""merge_best.py -- build a submission from best/*.npz plus the grid fallback.

Rules of engagement (plan.md):
  * never regress   -- keep whichever packing has the smaller L for each n
  * positive gap    -- every packing from best/ is expanded slightly, because
                       the grader rejects overlaps of 1e-16 and contacts it
                       cannot certify, and double precision sees neither
  * gate            -- grader_check must accept every puzzle; one that keeps
                       failing falls back to the grid

    python merge_best.py --out submission_final.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import pathlib

import numpy as np

import grader_check
import squares_core as sc
import verify_poly

BEST = pathlib.Path("best")
# above this size the O(n^2) Python clipping check is skipped; it is only a
# cross-check now that grader_check gates every puzzle
POLY_CHECK_MAX_N = 400
START_GAP = 1e-12
MAX_GAP = 1e-8


def load_best() -> dict[int, tuple[np.ndarray, np.ndarray, float]]:
    out = {}
    for f in sorted(BEST.glob("n*.npz")):
        d = np.load(f)
        n = int(f.stem[1:])
        if len(d["xy"]) != n:
            continue
        out[n] = (d["xy"], d["th"], float(d["L"]))
    return out


def load_csv(path: str) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    by_n: dict[int, list[tuple[float, float, float]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_n.setdefault(int(row["n"]), []).append(
                (float(row["x"]), float(row["y"]), float(row["angle"])))
    out = {}
    for n, rows in by_n.items():
        if len(rows) != n:
            continue
        out[n] = (np.array([(r[0], r[1]) for r in rows]),
                  np.array([r[2] for r in rows]))
    return out


def separate(xy: np.ndarray, th: np.ndarray, factor: float = START_GAP):
    """Push every centre away from the centroid by `factor`.

    Distances between centres only ever grow, so every contact opens up.
    The witnesses are exact-touching, so what is left after float rounding is
    ~1e-15 of dust; a 1e-12 relative expansion clears it for ~1e-11 of L.
    """
    c = xy.mean(axis=0)
    return c + (xy - c) * (1.0 + factor), th


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="submission_full.csv")
    ap.add_argument("--out", default="submission_final.csv")
    ap.add_argument("--n-max", type=int, default=1000)
    args = ap.parse_args()

    sol = load_csv(args.base)
    best = load_best()

    raw: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    kept = 0
    for n, (xy, th, Lb) in best.items():
        cur = sol.get(n)
        Lc = sc.container_side(*cur) if cur is not None else math.inf
        if Lb < Lc - 1e-12:
            raw[n] = (xy, th)
            sol[n] = separate(xy, th)
        else:
            kept += 1
    print(f"best/    : {len(best)} packings  ({len(raw)} beat the base, "
          f"{kept} did not)")

    # Gate on the grader's own rules, on the coordinates as they get written.
    # A rejected puzzle retries with a wider gap, then falls back to the grid.
    gap = START_GAP
    while True:
        lit = {n: grader_check.as_literals(*sc.centered(*sol[n])) for n in sol}
        bad = grader_check.rejected(lit)
        print(f"grader check at gap {gap:.0e}: {len(bad)} rejected {sorted(bad)[:12]}")
        if not bad:
            break
        gap *= 10.0
        for n in bad:
            if n in raw and gap <= MAX_GAP:
                sol[n] = separate(*raw[n], gap)
            else:
                print(f"  n={n} falls back to the grid: {bad[n]}")
                raw.pop(n, None)
                sol[n] = sc.grid(n)

    sc.write_submission(args.out, sol)
    res = sc.evaluate_submission(args.out, n_max=args.n_max)

    # Independent second opinion on the packings we actually changed. The
    # polygon-clipping test is pure Python and O(n^2), so above a few hundred
    # squares it takes minutes per puzzle; SAT has already been applied to
    # every one of them, and this is a spot cross-check rather than a gate.
    worst, wwhere = 0.0, None
    checked = 0
    for n in sorted(best):
        if n > POLY_CHECK_MAX_N:
            continue
        area, where = verify_poly.max_overlap_area(*sol[n])
        checked += 1
        if area > worst:
            worst, wwhere = area, (n, where)
    grid = sum(sc.grid_side(n) / math.sqrt(n) - 1.0 for n in range(1, args.n_max + 1))
    print(f"wrote {args.out}")
    print(f"score {res['total']:.10f}   grid {grid:.10f}   "
          f"({grid - res['total']:+.4f} better)")
    invalid = [d for d in res["detail"] if d[2].startswith("invalid")]
    print(f"invalid puzzles {len(invalid)}   poly cross-check on {checked} puzzles, "
          f"worst overlap {worst:.2e}" + (f" at {wwhere}" if worst > 1e-12 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
