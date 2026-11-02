"""lift_packings.py -- apply the three free closure rules to best/.

    lift    a packing of n squares in side L gains an L-shaped strip of unit
            squares: n + 2*floor(L) + 1 squares in side L + 1
    delete  a packing of n + 1 squares is also one of n squares
    crop    the squares inside a corner box of side s are a packing of that
            many squares in side s (a subset of a valid packing is valid);
            the reverse of lift is one case

All are repeated until nothing changes. A packing is written to best/ only if
it beats what is there, so this is safe to rerun.

    python src/lift_packings.py            # update best/
    python src/lift_packings.py --report
"""
from __future__ import annotations

import argparse
import math
import pathlib

import numpy as np

import squares_core as sc

OUT = pathlib.Path("best")
N_MAX = 1000
EPS = 1e-10


def load_all() -> dict[int, tuple[np.ndarray, np.ndarray, float]]:
    """n -> (xy, th, L), the best packing on disk or the grid."""
    pack = {}
    for n in range(1, N_MAX + 1):
        path = OUT / f"n{n:03d}.npz"
        if path.exists():
            d = np.load(path)
            L = float(d["L"])
            if L < sc.grid_side(n) - 1e-9:
                pack[n] = (*sc.centered(d["xy"], d["th"]), L)
                continue
        pack[n] = (*sc.grid(n), float(sc.grid_side(n)))
    return pack


def lift(xy: np.ndarray, th: np.ndarray, L: float):
    """Add the strip along the top and right of a packing centred at the origin."""
    k = math.floor(L)
    col = np.array([(L + 0.5, i + 0.5) for i in range(k + 1)])
    row = np.array([(i + 0.5, L + 0.5) for i in range(k)])
    return np.vstack([xy, col, row]), np.concatenate([th, np.zeros(2 * k + 1)])


def crops(xy: np.ndarray, th: np.ndarray):
    """Per corner: (sides, order) where the squares order[:k] fit a box of side sides[k-1]."""
    P = sc.corners(xy, th)
    X, Y = P[..., 0], P[..., 1]
    x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
    for dx in (X.max(1) - x0, x1 - X.min(1)):
        for dy in (Y.max(1) - y0, y1 - Y.min(1)):
            need = np.maximum(dx, dy)
            order = np.argsort(need, kind="stable")
            yield need[order], order


def close(pack) -> set[int]:
    """Apply the rules in place until stable. Returns the n that changed."""
    touched: set[int] = set()
    changed = True
    while changed:
        changed = False
        for n in range(1, N_MAX + 1):
            xy, th, L = pack[n]
            if n < N_MAX and pack[n + 1][2] < L - EPS:
                bigger = pack[n + 1]
                pack[n] = (bigger[0][:n], bigger[1][:n], bigger[2])
                xy, th, L = pack[n]
                touched.add(n)
                changed = True
            m = n + 2 * math.floor(L) + 1
            if m <= N_MAX and L + 1 < pack[m][2] - EPS:
                pack[m] = (*lift(xy, th, L), L + 1)
                touched.add(m)
                changed = True
            best = np.array([pack[k][2] for k in range(1, n)])
            for sides, order in crops(xy, th):
                for k in np.flatnonzero(sides[:n - 1] < best - EPS) + 1:
                    sub = order[:k]
                    side = sc.container_side(xy[sub], th[sub])
                    if side < pack[k][2] - EPS:
                        pack[k] = (*sc.centered(xy[sub], th[sub]), side)
                        best[k - 1] = side
                        touched.add(int(k))
                        changed = True
    return touched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    pack = load_all()
    before = sum(v[2] / math.sqrt(n) - 1.0 for n, v in pack.items())
    touched = close(pack)
    after = sum(v[2] / math.sqrt(n) - 1.0 for n, v in pack.items())

    bad = 0
    for n in sorted(touched):
        xy, th, _ = pack[n]
        ok, _info = sc.is_valid(xy, th)
        if len(xy) != n or not ok:
            bad += 1
            print(f"  invalid lifted packing at n={n}")
            continue
        if not args.report:
            sc.store_best(n, xy, th, OUT)

    print(f"improved {len(touched)} puzzles, {bad} invalid")
    print(f"score {before:.6f} -> {after:.6f}  ({before - after:+.4f})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
