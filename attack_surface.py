"""attack_surface.py -- where is the remaining score, in our own submission?

Reads a submission (default submission_final.csv), compares every puzzle's L
against the grid, and reports the blocks where we are still exactly at the grid.

    python attack_surface.py [submission.csv]
"""
from __future__ import annotations

import csv
import collections
import math
import sys

import numpy as np

import squares_core as sc


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "submission_final.csv"
    by_n: dict[int, list[tuple[float, float, float]]] = collections.defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_n[int(row["n"])].append(
                (float(row["x"]), float(row["y"]), float(row["angle"])))

    at_grid, moved = [], []
    for n in range(1, 1001):
        xy = np.array([(a, b) for a, b, _ in by_n[n]])
        th = np.array([c for _, _, c in by_n[n]])
        L = sc.container_side(xy, th)
        g = sc.grid_side(n)
        row = (n, L, L / math.sqrt(n) - 1.0, g / math.sqrt(n) - 1.0)
        (at_grid if L > g - 1e-9 else moved).append(row)

    print(f"still exactly at the grid : {len(at_grid):4d}  "
          f"worth {sum(r[2] for r in at_grid):.4f}")
    print(f"improved                  : {len(moved):4d}  "
          f"worth {sum(r[2] for r in moved):.4f}")

    def locked(n: int) -> bool:
        k = sc.grid_side(n)
        return n in (k * k, k * k - 1, k * k - 2)

    lock = [r for r in at_grid if locked(r[0])]
    open_ = [r for r in at_grid if not locked(r[0])]
    print(f"  proved optimal anyway   : {len(lock):4d}  "
          f"worth {sum(r[2] for r in lock):.4f}  LOCKED")
    print(f"  genuinely claimable     : {len(open_):4d}  "
          f"worth {sum(r[2] for r in open_):.4f}")

    print(f"\n{'blk':>3} {'n range':>11} {'at grid':>8} {'worth':>8} "
          f"{'improved':>9} {'ours':>8} {'as grid':>8}")
    tot = 0.0
    for k in range(2, 32):
        lo, hi = (k - 1) ** 2 + 1, k * k
        rows = [r for r in range(lo, hi + 1)]
        g = [r for r in at_grid if lo <= r[0] <= hi]
        m = [r for r in moved if lo <= r[0] <= hi]
        ours = sum(r[2] for r in g) + sum(r[2] for r in m)
        grid = sum(r[3] for r in g) + sum(r[3] for r in m)
        tot += ours
        print(f"{k:>3} {lo:>4}-{hi:<6} {len(g):>8} {sum(r[2] for r in g):>8.4f} "
              f"{len(m):>9} {ours:>8.4f} {grid:>8.4f}")
    print(f"{'':>3} {'total':>11} {'':>8} {'':>8} {'':>9} {tot:>8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
