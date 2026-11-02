"""flips.py -- free combinatorial moves, then the contact LP.

Our packings are jammed: every first-order move (including rigid shifts of
whole rows) already has dL >= 0, and kicks cost more than the LP wins back
(plan.md). A move that costs nothing is a *window flip*: pick an axis-aligned
rectangle whose border no square crosses and mirror or rotate its contents.
The result is exactly as valid and exactly as large, but the contacts along
the border change, which may give the LP a descent direction again.

Result (n=376, 457, 930, 994): no clean window holds a tilted square, even
at 1e-3 tolerance or anchored at the box corners. The best window with 5+
tilted squares inside still cuts 7 squares (n=994) or 10 (n=457): the blocks
interlock wall to wall, so these packings have no free flips.

    python experiments/flips.py 930 994 --seconds 10
    python experiments/flips.py --check
"""
from __future__ import annotations

import argparse
import math

import numpy as np

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import contact_polish as cp
import squares_core as sc

TOL = 1e-9


def inside(xy, th, win):
    """Per square: 1 inside the window, 0 apart from it, -1 crossing its border."""
    x1, x2, y1, y2 = win
    P = sc.corners(xy, th)
    X, Y = P[..., 0], P[..., 1]
    ins = (X.min(1) >= x1 - TOL) & (X.max(1) <= x2 + TOL) & (Y.min(1) >= y1 - TOL) & (Y.max(1) <= y2 + TOL)
    # rectangle vs rotated square: separated on x, y, or one of the square's axes
    sep = (X.max(1) <= x1 + TOL) | (X.min(1) >= x2 - TOL) | (Y.max(1) <= y1 + TOL) | (Y.min(1) >= y2 - TOL)
    R = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
    for a in (th, th + math.pi / 2):
        u = np.stack([np.cos(a), np.sin(a)], -1)
        c = np.einsum("nd,nd->n", xy, u)
        r = R @ u.T                                   # (4, n)
        sep |= (r.min(0) >= c + 0.5 - TOL) | (r.max(0) <= c - 0.5 + TOL)
    return np.where(ins, 1, np.where(sep, 0, -1))


def flip(xy, th, win, op):
    """Mirror (op 0: x, 1: y), turn 180 (2) or 90 deg (3, square windows) in place."""
    x1, x2, y1, y2 = win
    xy, th = xy.copy(), th.copy()
    k = inside(xy, th, win) == 1
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x, y = xy[k, 0] - cx, xy[k, 1] - cy
    if op == 0:
        xy[k, 0], th[k] = cx - x, -th[k]
    elif op == 1:
        xy[k, 1], th[k] = cy - y, -th[k]
    elif op == 2:
        xy[k] = np.c_[cx - x, cy - y]
    else:
        xy[k], th[k] = np.c_[cx - y, cy + x], th[k] + math.pi / 2
    return xy, th


def windows(xy, th):
    """Clean windows anchored at a corner of the box, borders on axis-square edges.

    Tilted blocks run into the walls and interlock, so a free-floating window
    that holds a tilted square fully almost never has a clean border.
    """
    m = np.mod(th, math.pi / 2)
    ax = np.minimum(m, math.pi / 2 - m) < 1e-4
    P = sc.corners(xy, th).reshape(-1, 2)
    lo, hi = P.min(0), P.max(0)
    xs = np.unique(np.round(np.r_[xy[ax, 0] - 0.5, xy[ax, 0] + 0.5], 6))
    ys = np.unique(np.round(np.r_[xy[ax, 1] - 0.5, xy[ax, 1] + 0.5], 6))
    xs, ys = xs[(xs > lo[0] + 1) & (xs < hi[0] - 1)], ys[(ys > lo[1] + 1) & (ys < hi[1] - 1)]
    C = sc.corners(xy, th)
    bx0, bx1, by0, by1 = C[..., 0].min(1), C[..., 0].max(1), C[..., 1].min(1), C[..., 1].max(1)
    out = []
    for x in np.r_[xs, hi[0]]:
        for y in np.r_[ys, hi[1]]:
            for win in ((lo[0], x, lo[1], y), (lo[0], x, y, hi[1]),
                        (x, hi[0], lo[1], y), (x, hi[0], y, hi[1])):
                x1, x2, y1, y2 = win
                if x2 - x1 < 2 or y2 - y1 < 2:
                    continue
                # ponytail: bounding boxes, so a few clean windows are missed; exact test below
                ins = (bx0 >= x1 - TOL) & (bx1 <= x2 + TOL) & (by0 >= y1 - TOL) & (by1 <= y2 + TOL)
                out_ = (bx1 <= x1 + TOL) | (bx0 >= x2 - TOL) | (by1 <= y1 + TOL) | (by0 >= y2 - TOL)
                # clean border, some tilted squares inside, not the whole packing
                if (ins | out_).all() and ins[~ax].any() and out_.any():
                    out.append(win)
    return [w for w in sorted(set(out)) if (inside(xy, th, w) >= 0).all()]


def check():
    xy, th = sc.grid(9)
    th = th.copy()
    th[0] = 0.1                                    # one tilted square in a 3x3 grid
    xy = xy * 1.2                                  # loosen so it fits
    lo = sc.corners(xy, th).min()
    for op in range(4):
        win = (lo, 2.4, lo, 2.4)                   # holds the 2x2 corner, border clean
        assert (inside(xy, th, win) >= 0).all()
        a, b = flip(xy, th, win, op)
        # contents stay in the window, so the box can only shrink
        assert sc.is_valid(a, b)[0] and sc.container_side(a, b) <= sc.container_side(xy, th) + 1e-9
    assert inside(xy, th, (0.0, 1.2, 0.0, 1.2))[0] == 1
    assert inside(xy, th, (0.5, 3.0, 0.5, 3.0))[0] == -1
    print("ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ns", nargs="*", type=int)
    ap.add_argument("--seconds", type=float, default=10)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check()
        return 0
    for n in a.ns:
        d = np.load(f"best/n{n:03d}.npz")
        xy, th, L0 = d["xy"], d["th"], float(d["L"])
        wins = windows(xy, th)
        best = L0
        for w, op in ((w, op) for w in wins for op in range(4)):
            if op == 3 and abs((w[1] - w[0]) - (w[3] - w[2])) > 1e-9:
                continue
            fx, ft = flip(xy, th, w, op)
            p, steps = cp.polish(cp.to_packing(fx, ft), seed=n, max_seconds=a.seconds)
            px, pt = p[:, :2], p[:, 2]
            L = sc.container_side(px, pt)
            if L < best - 1e-12 and sc.is_valid(px, pt)[0]:
                best, xy, th = L, px, pt
                print(f"  n={n} flip {op} {np.round(w, 2)} -> {L:.10f}", flush=True)
        stored = best < L0 and sc.store_best(n, xy, th)
        print(f"n={n} windows={len(wins)} {L0:.10f} -> {best:.10f} gain {L0 - best:.2e}"
              + (" STORED" if stored else ""), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
