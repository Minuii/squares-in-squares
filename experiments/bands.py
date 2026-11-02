"""bands.py -- grid plus two mirrored bands of tilted rows, the bent-band family.

EXPERIMENTAL. Seen on the Living Atlas and in best/ (n = 182 ... 273): one
band of tilted rows runs from the left wall down towards the middle, and its
mirror image in y = x runs from the middle to the right wall. The axis grid
fills the staircases on both sides. rows.py only puts thin axis-aligned strips
along two walls, which is why it falls 5-6 squares short of these records.

A band is a square lattice at angle t whose rows (along u) are stacked down
along -v and each shifted by p along u. Row j keeps the cells whose position q
along u lies in [s j, s j + m), so s sets how the band slants, plus every
cell must lie inside [0, L]^2. Band A starts at (ox, oy); band B is A mirrored
in y = x (angle -t), with B's squares that hit A dropped. rows.fill adds the
axis grid around them, so every candidate is feasible by construction and the
search only counts squares.

    python experiments/bands.py --n 240 --L 15.96969     # can it rebuild a record?
    python experiments/bands.py --n 274 --L 16.999        # beyond the frontier
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np
from scipy.spatial import cKDTree

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import contact_polish as cp
import squares_core as sc
from rows import EPS, fill, pen

# prm = (t, p, ox, oy, s, k, m); k rows of up to m cells
INTS = (5, 6)


def band(L, prm):
    t, p, ox, oy, s, k, m = prm
    u = np.array([math.cos(t), math.sin(t)])
    v = np.array([-math.sin(t), math.cos(t)])
    j = np.repeat(np.arange(int(k)), int(m) + 2 * int(L) + 4)
    q = np.tile(np.arange(-int(L) - 2, int(m) + int(L) + 2), int(k)) + j * p
    keep = (q >= s * j - EPS) & (q < s * j + m - EPS)
    j, q = j[keep], q[keep]
    c = np.array([ox, oy]) + q[:, None] * u - j[:, None] * v
    h = sc.half_extent(np.array(t))
    inside = ((c >= h - EPS) & (c <= L - h + EPS)).all(1)
    return c[inside]


def build(L, prm):
    A = band(L, prm)
    B = A[:, ::-1]
    t = prm[0]
    if len(A) and len(B):
        near = cKDTree(A).sparse_distance_matrix(cKDTree(B), 1.42, output_type="ndarray")
        bad = np.zeros(len(B), bool)
        if len(near):
            i, j = near["i"], near["j"]
            hit = pen(A[i], np.full(len(i), t), B[j], np.full(len(j), -t)) > EPS
            bad[j[hit]] = True
        B = B[~bad]
    txy = np.vstack([A, B])
    tth = np.r_[np.full(len(A), t), np.full(len(B), -t)]
    return fill(L, txy, tth)


def random_prm(L, rng):
    return np.array([rng.uniform(0.15, 0.6), rng.uniform(0, 1), rng.uniform(0, 1.5),
                     L - rng.uniform(0, 1.5), rng.uniform(-1.5, 1.5),
                     rng.integers(3, int(L / 2) + 1), rng.integers(3, int(L) + 1)], float)


STEP = np.array([0.01, 0.05, 0.05, 0.05, 0.05, 1, 1])


def climb(L, prm, steps, rng):
    c = len(build(L, prm)[0])
    for _ in range(steps):
        q = prm.copy()
        idx = rng.integers(len(q))
        if idx in INTS:
            q[idx] = max(1, q[idx] + rng.choice((-1, 1)))
        else:
            q[idx] += rng.normal(0, STEP[idx])
        cq = len(build(L, q)[0])
        if cq >= c:
            prm, c = q, cq
    return prm, c


def search(n, L, seconds, rng, steps=400):
    best, best_c = None, -1
    end = time.time() + seconds
    while time.time() < end and best_c < n:
        prm, c = climb(L, random_prm(L, rng), steps, rng)
        if c > best_c:
            best, best_c = prm, c
            print(f"  {best_c} squares  prm={np.round(best, 3).tolist()}", flush=True)
    return best, best_c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--L", type=float, help="side to fill (default: best/ record)")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    L = a.L or float(np.load(f"best/n{a.n:03d}.npz")["L"])
    prm, c = search(a.n, L, a.seconds, np.random.default_rng(a.seed))
    line = f"n={a.n} L={L:.5f} fits {c} (need {a.n})"
    if c >= a.n:
        xy, th = build(L, prm)
        xy, th = xy[: a.n], th[: a.n]
        p, _ = cp.polish(cp.to_packing(xy, th))
        xy, th = p[:, :2], p[:, 2]
        ok = sc.is_valid(xy, th)[0]
        line += f" -> polished L={sc.container_side(xy, th):.6f} valid={ok}"
        if ok and sc.store_best(a.n, xy, th):
            line += " STORED"
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
