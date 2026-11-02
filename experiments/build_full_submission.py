"""build_full_submission.py -- Phase 0: a legal, complete 1000-puzzle file.

Takes whatever packings we already have (submission.csv), fills every missing
puzzle with the plain grid, and writes submission_full.csv. Score is unchanged
(missing puzzles are charged the grid anyway) but the file is now complete and
validated, which is the base every later merge builds on.

    python experiments/build_full_submission.py [--src submission.csv] [--out submission_full.csv]
"""
from __future__ import annotations

import argparse
import csv
import numpy as np

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import squares_core as sc


def load(path: str) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    by_n: dict[int, list[tuple[float, float, float]]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_n.setdefault(int(row["n"]), []).append(
                (float(row["x"]), float(row["y"]), float(row["angle"])))
    out = {}
    for n, rows in by_n.items():
        if len(rows) != n:
            continue
        xy = np.array([(r[0], r[1]) for r in rows])
        th = np.array([r[2] for r in rows])
        ok, _ = sc.is_valid(xy, th)
        if ok:
            out[n] = (xy, th)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="submission.csv")
    ap.add_argument("--out", default="submission_full.csv")
    ap.add_argument("--n-max", type=int, default=1000)
    args = ap.parse_args()

    sol = load(args.src)
    have = sorted(sol)
    added = []
    for n in range(1, args.n_max + 1):
        if n not in sol:
            sol[n] = sc.grid(n)
            added.append(n)

    sc.write_submission(args.out, sol)
    res = sc.evaluate_submission(args.out, n_max=args.n_max)
    grid_total = sum(sc.grid_side(n) / np.sqrt(n) - 1.0 for n in range(1, args.n_max + 1))
    print(f"kept {len(have)} existing puzzles, added {len(added)} grids")
    print(f"wrote {args.out}")
    print(f"score {res['total']:.10f}   (grid {grid_total:.10f}, "
          f"{grid_total - res['total']:+.4f} better)")
    bad = [(n, L, why) for n, L, why in res["detail"] if why.startswith("invalid")]
    print(f"invalid puzzles: {len(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
