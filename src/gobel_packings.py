"""gobel_packings.py -- instantiate Goebel's family for every n it can serve.

Friedman DS7: for integers a, b with a-1 < b/sqrt(2) < a+1, exactly
2a^2 + 2a + b^2 unit squares pack into a square of side a + 1 + b/sqrt(2).
The b^2 "tilted" squares form a solid b x b block turned 45 degrees -- a solid
diamond, because b x b unit squares tile exactly -- and the axis squares are
the (2a)^2 lattice positions (offsets 1/2, 3/2, ..., a-1/2 from each wall)
minus those that hit the diamond.

Because deleting squares can only shrink the bounding box, the family also
serves every n <= count(a, b). That is what makes it useful above the
literature's n = 324 boundary, where nothing else is published.

    python src/gobel_packings.py            # write best/nNNN.npz where it wins
    python src/gobel_packings.py --report
"""
from __future__ import annotations

import argparse
import math
import pathlib

import numpy as np

import squares_core as sc

OUT = pathlib.Path("best")
SQ2 = math.sqrt(2.0)


def admits(a: int, b: int) -> bool:
    return a >= 1 and b >= 1 and a - 1 < b / SQ2 < a + 1


def build(a: int, b: int):
    """(xy, th) for the full family packing, plus its exact side."""
    side = (a + 1) + b / SQ2
    mid = side / 2.0

    # tilt 45 degrees: a unit square at pi/4 has half-extent (1+1)/2 / sqrt2
    th_tilt = math.pi / 4.0
    r = b / SQ2                                    # diamond radius along an axis

    offs = np.array([k + 0.5 for k in range(a)], dtype=float)
    offs = np.concatenate([offs, side - offs])
    gx, gy = np.meshgrid(offs, offs, indexing="ij")
    cx, cy = gx.ravel(), gy.ravel()

    # Does the unit square centred at (cx, cy) meet the *open* diamond?
    # The boundary matters: the frame squares that sit exactly against a face of
    # the tilted block are legal (touching), and floating point puts their L1
    # distance a few ulps either side of r. Without the epsilon eight of the
    # twelve n=21 frame squares are wrongly discarded.
    dx = np.abs(cx - mid) - 0.5
    dy = np.abs(cy - mid) - 0.5
    hit = (np.maximum(dx, 0.0) + np.maximum(dy, 0.0)) < r - 1e-9
    ax, ay = cx[~hit], cy[~hit]

    # tilted block: a b x b array of squares at 45 degrees, laid out from the
    # centre so the same expression works for odd and even b.
    u, v = np.meshgrid(np.arange(b), np.arange(b), indexing="ij")
    tx = mid + (2 * (u + v) - 2 * (b - 1)) * SQ2 / 4.0
    ty = mid + (2 * (v - u)) * SQ2 / 4.0

    xy = np.concatenate([np.stack([ax, ay], axis=-1),
                         np.stack([tx.ravel(), ty.ravel()], axis=-1)])
    th = np.concatenate([np.zeros(len(ax)), np.full(b * b, th_tilt)])
    assert len(xy) == 2 * a * a + 2 * a + b * b, (len(xy), a, b)
    return xy, th, side


def _frame_minus_diamond(xs, ys, mx, my, r):
    """Axis squares on the lattice xs x ys that miss the open diamond |.-m|_1 < r."""
    gx, gy = np.meshgrid(np.asarray(xs), np.asarray(ys), indexing="ij")
    cx, cy = gx.ravel(), gy.ravel()
    dx = np.abs(cx - mx) - 0.5
    dy = np.abs(cy - my) - 0.5
    hit = (np.maximum(dx, 0.0) + np.maximum(dy, 0.0)) < r - 1e-9
    return cx[~hit], cy[~hit]


def admits_offcentre(a: int, b: int) -> bool:
    return a >= 1 and b >= 1 and a - 0.5 < b / SQ2 < a + 0.5


def build_offcentre(a: int, b: int):
    """Friedman DS7 section 3: 2a^2 + 4a + b^2 + 1 squares in side a + 3/2 + b/sqrt(2).

    The centred family squeezed to an (a + 1/2 + b/sqrt 2) x (a + 3/2 + b/sqrt 2)
    rectangle, block centred in the rectangle, plus a column of 2a + 1 squares
    standing against its short side. Layout follows the Squares Project's
    cases/gobel_offcentre.
    """
    width = a + 0.5 + b / SQ2
    side = width + 1.0
    mx, my = width / 2.0, side / 2.0
    offs = [k + 0.5 for k in range(a)]
    ax, ay = _frame_minus_diamond(offs + [width - o for o in offs],
                                  offs + [side - o for o in offs], mx, my, b / SQ2)
    u, v = np.meshgrid(np.arange(b), np.arange(b), indexing="ij")
    tx = mx + (2 * (u + v) - 2 * (b - 1)) * SQ2 / 4.0
    ty = my + (2 * (v - u)) * SQ2 / 4.0
    col = np.array([(width + 0.5, k + 0.5) for k in range(2 * a + 1)])
    xy = np.concatenate([np.stack([ax, ay], axis=-1),
                         np.stack([tx.ravel(), ty.ravel()], axis=-1), col])
    th = np.concatenate([np.zeros(len(ax)), np.full(b * b, math.pi / 4.0),
                         np.zeros(len(col))])
    assert len(xy) == 2 * a * a + 4 * a + b * b + 1, (len(xy), a, b)
    return xy, th, side


def build_strip(a: int):
    """Goebel's diagonal strip, Friedman DS7 section 2.

    a^2 + a + 2 + (floor((a - 1) sqrt 2) + 1) squares in side a + 1 + sqrt(2)/2:
    a 45-degree strip corner to corner, staircases either side, one square in
    each of the two corners the strip runs toward. Layout follows the Squares
    Project's cases/gobel_strip.
    """
    side = a + 1 + SQ2 / 2
    low = [(i + 0.5, j + 0.5) for i in range(a) for j in range(a - i)]
    high = [(side - x, side - y) for x, y in low]
    corner = [(side - 0.5, 0.5), (0.5, side - 0.5)]
    m = math.isqrt(2 * (a - 1) * (a - 1)) + 1
    tilt = []
    for k in range(m):
        d = (2 * k - (m - 1)) * SQ2 / 2
        tilt.append(((side + d) / 2, (side - d) / 2))
    xy = np.array(low + high + corner + tilt, dtype=float)
    th = np.concatenate([np.zeros(len(xy) - m), np.full(m, math.pi / 4.0)])
    return xy, th, side


def trim(xy, th, n: int):
    """Keep the n squares nearest the centre, so the bounding box shrinks."""
    if n >= len(xy):
        return xy, th
    c = np.array([xy[:, 0].mean(), xy[:, 1].mean()])
    d = np.abs(xy - c).max(axis=1)
    keep = np.argsort(d, kind="stable")[:n]
    return xy[keep], th[keep]


def candidates(n: int):
    """Every (a, b) whose construction holds at least n squares, by side."""
    out = []
    for a in range(1, 26):
        for b in range(1, 40):
            if admits(a, b) and 2 * a * a + 2 * a + b * b >= n:
                out.append((a + 1 + b / SQ2, a, b))
    out.sort()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--n-min", type=int, default=1)
    ap.add_argument("--n-max", type=int, default=1000)
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    won, tried, bad = [], 0, 0
    for n in range(args.n_min, args.n_max + 1):
        grid = sc.grid_side(n)
        bestL, best = math.inf, None
        for _, a, b in candidates(n)[:4]:          # the four smallest sides
            xy, th, _ = build(a, b)
            xy, th = trim(xy, th, n)
            ok, info = sc.is_valid(xy, th)
            tried += 1
            if not ok:
                bad += 1
                continue
            if info["L"] < bestL:
                bestL, best = info["L"], (xy.copy(), th.copy())
        if best is None or bestL >= grid - 1e-9:
            continue
        won.append((n, grid, bestL))
        if not args.report:
            sc.store_best(n, best[0], best[1], OUT)

    # The two related families, stored at their full count; lift_packings'
    # delete rule carries each one down to smaller n.
    extra = [build_offcentre(a, b) for a in range(1, 26) for b in range(1, 45)
             if admits_offcentre(a, b)]
    extra += [build_strip(a) for a in range(2, 32)]
    stored = 0
    for xy, th, _ in extra:
        n = len(xy)
        if n > args.n_max or n < args.n_min:
            continue
        ok, info = sc.is_valid(xy, th)
        tried += 1
        if not ok:
            bad += 1
            print(f"  invalid family build n={n} pen={info['max_penetration']:.1e}")
            continue
        if info["L"] < sc.grid_side(n) - 1e-9 and not args.report:
            stored += sc.store_best(n, xy, th, OUT)
    print(f"off-centre and strip builds stored: {stored}")

    print(f"builds tried {tried}, invalid {bad}")
    print(f"n where the family beats the grid: {len(won)}")
    if won:
        saved = sum((g - L) / math.sqrt(n) for n, g, L in won)
        print(f"score saved: {saved:.4f}")
        print(f"  n <= 324: {sum(1 for n, _, _ in won if n <= 324)}")
        print(f"  n >  324: {sum(1 for n, _, _ in won if n > 324)}")
        for n, g, L in won[:6]:
            print(f"    n={n:4d} grid={g:2d} L={L:.6f} score={L/math.sqrt(n)-1:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
