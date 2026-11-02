"""rows.py -- random restarts in a structured family: grid + tilted lattice blocks.

The 900+ packings are an axis grid with one or two rectangular blocks of a
rotated square lattice (angle ~14 deg) in opposite corners. Here a packing is
~10 numbers instead of 3n coordinates:

    block A in the top-left corner,     W x H, angle, lattice phase (2)
    block B in the bottom-right corner, W x H, angle, lattice phase (2)

Lattice squares are kept if they lie inside their block; axis cells from the
four corner-anchored grids are then added greedily wherever they fit, so the
grid interlocks with the blocks' ragged edges. Every candidate is feasible by
construction, so the search only has to count.

Result (n=920, 930, 984, 994, 998): 3-6 squares short of the current best
at its L. Fillers do not close the gap: there is no free hole (only 2 points
sit 1 from every centre on n=994), and dropping 3 squares into the largest
holes then relaxing at fixed L stalls at penetration 0.04 (0.3 with rotation
noise). Sheared rows are locked: a row cannot slide without entering the next.

    python rows.py 930 994          # search, store_best on success
    python rows.py --check          # self-check
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np
from scipy.optimize import brentq
from scipy.spatial import cKDTree

import contact_polish as cp
import squares_core as sc

EPS = 1e-9


def pen(xa, ta, xb, tb):
    """Penetration depth of square pairs (a[k], b[k]); <= 0 means apart."""
    ca, sa, cb, sb = np.cos(ta), np.sin(ta), np.cos(tb), np.sin(tb)
    axes = np.stack([np.stack([ca, sa], -1), np.stack([-sa, ca], -1),
                     np.stack([cb, sb], -1), np.stack([-sb, cb], -1)], 1)
    d = xb - xa
    proj = np.abs(np.einsum("pkd,pd->pk", axes, d))
    r = 0.5 * sum(np.abs(np.einsum("pkd,pd->pk", axes, np.stack(e, -1)))
                  for e in ((ca, sa), (-sa, ca), (cb, sb), (-sb, cb)))
    return (r - proj).min(axis=1)


def block(L, corner, W, H, th, ox, oy):
    """Sheared-row squares inside a W x H rectangle at a corner of [0, L]^2.

    Top-left blocks use horizontal rows: pitch 1/cos(th) along x, rows cos(th)
    apart with a sin(th) shift (basis u - tan(th) v, v). Bottom-right blocks
    use the same thing turned into vertical columns (basis v + tan(th) u, u).
    """
    x0, y0 = (0.0, L - H) if corner == "tl" else (L - W, 0.0)
    h = sc.half_extent(np.array(th))
    u, v = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
    u, v = (u - math.tan(th) * v, v) if corner == "tl" else (v + math.tan(th) * u, u)
    k = int(W + H) + 2
    i, j = np.meshgrid(np.arange(-k, k + 1), np.arange(-k, k + 1))
    c = np.array([x0 + W / 2 + ox, y0 + H / 2 + oy]) + i.reshape(-1, 1) * u + j.reshape(-1, 1) * v
    ok = ((c[:, 0] >= x0 + h - EPS) & (c[:, 0] <= x0 + W - h + EPS)
          & (c[:, 1] >= y0 + h - EPS) & (c[:, 1] <= y0 + H - h + EPS))
    return c[ok]


def build(L, prm):
    """prm = (WA, HA, tA, oxA, oyA, WB, HB, tB, oxB, oyB) -> (xy, th)."""
    A = block(L, "tl", *prm[:5])
    B = block(L, "br", *prm[5:])
    txy = np.vstack([A, B])
    tth = np.concatenate([np.full(len(A), prm[2]), np.full(len(B), prm[7])])
    # A and B may collide where they meet: drop B's offenders
    if len(A) and len(B):
        near = cKDTree(A).sparse_distance_matrix(cKDTree(B), 1.42, output_type="ndarray")
        bad = np.zeros(len(B), bool)
        if len(near):
            i, j = near["i"], near["j"]
            hit = pen(A[i], np.full(len(i), prm[2]), B[j], np.full(len(j), prm[7])) > EPS
            bad[j[hit]] = True
        keep = np.r_[np.ones(len(A), bool), ~bad]
        txy, tth = txy[keep], tth[keep]

    # axis cells from the four corner-anchored grids, then greedy fill
    m = int(math.floor(L + EPS))
    s = np.arange(m) + 0.5
    cand = np.vstack([np.stack(np.meshgrid(xs, ys), -1).reshape(-1, 2)
                      for xs in (s, L - s) for ys in (s, L - s)])
    cand = np.unique(np.round(cand, 12), axis=0)
    blocked = np.zeros(len(cand), bool)
    if len(txy):
        near = cKDTree(txy).sparse_distance_matrix(cKDTree(cand), 1.42, output_type="ndarray")
        if len(near):
            i, j = near["i"], near["j"]
            hit = pen(txy[i], tth[i], cand[j], np.zeros(len(j))) > EPS
            blocked[j[hit]] = True
    # ponytail: greedy in a fixed order (left/bottom first); a max independent set could fit more
    order = np.lexsort((cand[:, 0], cand[:, 1]))
    taken = {}
    out = []
    for q in order:
        if blocked[q]:
            continue
        x, y = cand[q]
        gx, gy = int(math.floor(x)), int(math.floor(y))
        if any(abs(x - a) < 1 - EPS and abs(y - b) < 1 - EPS
               for dx in (-1, 0, 1) for dy in (-1, 0, 1)
               for a, b in taken.get((gx + dx, gy + dy), ())):
            continue
        taken.setdefault((gx, gy), []).append((x, y))
        out.append((x, y))
    xy = np.vstack([txy, np.array(out).reshape(-1, 2)])
    th = np.concatenate([tth, np.zeros(len(out))])
    return xy, th


def search(n, L, seconds, rng):
    """Pinwheel scan: strip thickness k, block edges, then lattice phases.

    A strip of height H = L - (whole grid cells) holds k = floor(H) + 1
    sheared rows when k cos(t) + sin(t) = H, so the angle is not free. Block A
    is [0, W] x [L-H, L], block B is its quarter-turn [L-H, L] x [0, HB].
    """
    best, best_c = None, -1
    end = time.time() + seconds
    ph = np.linspace(0, 0.8, 5)
    for k in range(3, int(L / 2)):
        H = L - math.floor(L) + k - 1
        if (k + 1) / math.sqrt(2) > H:  # strip too thin for k rows at any angle
            continue
        t = brentq(lambda t: k * math.cos(t) + math.sin(t) - H, math.atan(1 / k), math.pi / 4)
        for dW in (0, -0.5, -1):
            for dB in (0, -0.5, -1):
                p = np.array([L - H + dW, H, -t, 0, 0, H, L - H + dB, t, 0, 0])
                c = len(build(L, p)[0])
                for _ in range(2):  # coordinate descent: A's phase, then B's
                    for idx in ((3, 4), (8, 9)):
                        for a in ph:
                            for b in ph:
                                q = p.copy()
                                q[list(idx)] = a, b
                                cq = len(build(L, q)[0])
                                if cq > c:
                                    p, c = q, cq
                if c > best_c:
                    best, best_c = p, c
                if best_c >= n or time.time() > end:
                    return best, best_c
    return best, best_c


def check():
    # no blocks: the four grids give floor(L)^2 cells
    xy, th = build(5.3, np.array([0, 0, 0.2, 0, 0, 0, 0, 0.2, 0, 0]))
    assert len(xy) == 25 and sc.is_valid(xy, th)[0]
    # a block of 45 deg squares stays feasible
    xy, th = build(12.4, np.array([7, 5, math.pi / 4, 0.1, 0.3, 4, 8, 0.25, 0.2, 0.1]))
    assert sc.is_valid(xy, th)[0] and sc.container_side(xy, th) <= 12.4 + 1e-9
    print("ok", len(xy))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ns", nargs="*", type=int)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check()
        return 0
    rng = np.random.default_rng(0)
    for n in a.ns:
        L = float(np.load(f"best/n{n:03d}.npz")["L"])
        prm, c = search(n, L, a.seconds, rng)
        line = f"n={n} L={L:.5f} fits {c} (need {n})"
        if c >= n:
            xy, th = build(L, prm)
            xy, th = xy[:n], th[:n]
            p, _ = cp.polish(cp.to_packing(xy, th))
            xy, th = p[:, :2], p[:, 2]
            ok = sc.is_valid(xy, th)[0]
            line += f" -> polished L={sc.container_side(xy, th):.6f} valid={ok}"
            if ok and sc.store_best(n, xy, th):
                line += " STORED"
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
