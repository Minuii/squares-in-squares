"""rowband.py -- bent bands built from rigid rows, each with its own angle.

EXPERIMENTAL. In the records for n = 182 ... 273 a band is a stack of rows of
3-6 squares, and every row has its own angle (17.8 to 22.9 degrees on
n = 240). bands.py gives the whole band one lattice angle and falls 7-11
squares short, so here each row is a free rigid bar:

    row j       m_j squares in a line at angle a_j, first square o_j from the
                left wall; row 0's top sits y0 below the top wall
    stacking    every later row is pushed up from below until it touches the
                rows above it (exactly, via the Minkowski sum of two squares)
    band B      band A mirrored in y = x; B's squares that hit A are dropped
    fill        axis squares around the bands, so a build is feasible by
                construction and the search only counts squares: the search
                uses rows.fill (greedy, 20 ms), the finish uses fill_mis, an
                exact set over the corner grids plus squares slid along a grid
                line until they touch a band (0.5 s). fill_mis rebuilds the
                records for n = 182, 210 and 240 from their tilted squares
                alone, and 272 of 273

    python experiments/rowband.py --n 240 --fit                     # rebuild a record from its rows
    python experiments/rowband.py --n 274 --L 16.999 --fit 273      # one past the frontier
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import contact_polish as cp
import squares_core as sc
from rows import EPS, fill, pen

GAP = 1e-9


def minkowski(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(P, 9, 2) closed boundary of S(a) + S(b) for unit squares at angles a, b."""
    ang = np.concatenate([a[:, None] + np.arange(4) * math.pi / 2,
                          b[:, None] + np.arange(4) * math.pi / 2], 1) % (2 * math.pi)
    ang = np.sort(ang, 1)
    edges = np.stack([np.cos(ang), np.sin(ang)], -1)
    # walk counter-clockwise from the lowest (then leftmost) vertex
    start = np.zeros((len(a), 2))
    for t in (a, b):
        c = sc.corners(np.zeros((len(t), 2)), t)
        low = np.argmin(c[..., 1] + 1e-12 * c[..., 0], 1)
        start += c[np.arange(len(t)), low]
    return np.concatenate([start[:, None], start[:, None] + np.cumsum(edges, 1)], 1)


def lower_edge(poly: np.ndarray, dx: np.ndarray) -> np.ndarray:
    """Lowest y of each polygon on the line x = dx (+inf if the line misses it)."""
    x0, y0 = poly[:, :-1, 0], poly[:, :-1, 1]
    x1, y1 = poly[:, 1:, 0], poly[:, 1:, 1]
    d = dx[:, None]
    span = (np.minimum(x0, x1) <= d) & (d <= np.maximum(x0, x1)) & (np.abs(x1 - x0) > 1e-12)
    y = y0 + (d - x0) * (y1 - y0) / np.where(np.abs(x1 - x0) > 1e-12, x1 - x0, 1)
    return np.where(span, y, np.inf).min(1)


def upper_edge(poly: np.ndarray, dx: np.ndarray) -> np.ndarray:
    """Highest y of each polygon on x = dx; the sums are centrally symmetric."""
    return -lower_edge(poly, -dx)


def fill_mis(L, txy, tth):
    """Most axis squares around (txy, tth), solved exactly with HiGHS.

    Candidates are the four corner grids, plus squares on one grid line slid
    along it until they touch a tilted square (and chains of up to 3 more
    behind them): the records hold a few of those."""
    m = int(math.floor(L + EPS))
    s = np.arange(m) + 0.5
    lines = np.unique(np.round(np.r_[s, L - s], 12))
    cand = [np.stack(np.meshgrid(lines, lines), -1).reshape(-1, 2)]
    if len(txy):
        for ax in (0, 1):  # ax = the coordinate that stays on a grid line
            g, k = np.meshgrid(lines, np.arange(len(txy)), indexing="ij")
            g, k = g.ravel(), k.ravel()
            d = g - txy[k, ax]
            near = np.abs(d) < 1.42
            g, k, d = g[near], k[near], d[near]
            # in the frame where the grid coordinate is x, the tilted square's angle flips sign
            poly = minkowski(np.zeros(len(k)), tth[k] if ax == 0 else -tth[k])
            lo, hi = lower_edge(poly, d), upper_edge(poly, d)
            ok = np.isfinite(lo)
            free = np.r_[txy[k[ok], 1 - ax] + lo[ok] - GAP, txy[k[ok], 1 - ax] + hi[ok] + GAP]
            gg = np.r_[g[ok], g[ok]]
            sgn = np.r_[-np.ones(ok.sum()), np.ones(ok.sum())]
            for c in range(4):
                f = free + sgn * c
                pts = np.stack([gg, f], 1) if ax == 0 else np.stack([f, gg], 1)
                cand.append(pts)
    cand = np.vstack(cand)
    cand = cand[((cand >= 0.5 - EPS) & (cand <= L - 0.5 + EPS)).all(1)]
    cand = np.unique(np.round(cand, 10), axis=0)
    if len(txy):
        near = cKDTree(txy).sparse_distance_matrix(cKDTree(cand), 1.42, output_type="ndarray")
        bad = np.zeros(len(cand), bool)
        if len(near):
            i, j = near["i"], near["j"]
            bad[j[pen(txy[i], tth[i], cand[j], np.zeros(len(j))) > EPS]] = True
        cand = cand[~bad]
    pr = cKDTree(cand).query_pairs(1.42, output_type="ndarray")
    if len(pr):
        pr = pr[(np.abs(cand[pr[:, 0]] - cand[pr[:, 1]]) < 1 - EPS).all(1)]
    A = coo_matrix((np.ones(2 * len(pr)), (np.repeat(np.arange(len(pr)), 2), pr.ravel())),
                   shape=(len(pr), len(cand)))
    r = milp(-np.ones(len(cand)), constraints=LinearConstraint(A, 0, 1),
             integrality=np.ones(len(cand)), bounds=Bounds(0, 1), options={"time_limit": 5})
    out = cand[r.x > 0.5] if r.x is not None else np.zeros((0, 2))
    return np.vstack([txy, out]), np.r_[tth, np.zeros(len(out))]


def band(L, y0, rows):
    """rows = [(a, m, o), ...] -> (xy, th) of band A."""
    xy, th = np.zeros((0, 2)), np.zeros(0)
    for j, (a, m, o) in enumerate(rows):
        u = np.array([math.cos(a), math.sin(a)])
        h = float(sc.half_extent(np.array(a)))
        rel = np.arange(int(m))[:, None] * u
        rel[:, 0] += h + o
        rel = rel[rel[:, 0] <= L - h + EPS]
        if not len(rel):
            break
        top = L - h - rel[:, 1].max() - (y0 if j == 0 else 0)
        if len(xy):
            # the row's squares against every placed square they can reach
            i, k = np.meshgrid(np.arange(len(rel)), np.arange(len(xy)), indexing="ij")
            i, k = i.ravel(), k.ravel()
            dx = rel[i, 0] - xy[k, 0]
            near = np.abs(dx) < 1.42
            i, k, dx = i[near], k[near], dx[near]
            low = lower_edge(minkowski(np.full(len(i), a), th[k]), dx)
            hit = np.isfinite(low)
            if hit.any():
                top = min(top, float(np.min(xy[k[hit], 1] + low[hit] - rel[i[hit], 1])))
        c = rel + [0, top - GAP]
        c = c[c[:, 1] >= h - EPS]
        if not len(c):
            break
        xy = np.vstack([xy, c])
        th = np.r_[th, np.full(len(c), a)]
    return xy, th


def build(L, y0, rows, exact=False):
    A, ta = band(L, y0, rows)
    B, tb = A[:, ::-1], -ta
    if len(A):
        near = cKDTree(A).sparse_distance_matrix(cKDTree(B), 1.42, output_type="ndarray")
        bad = np.zeros(len(B), bool)
        if len(near):
            i, j = near["i"], near["j"]
            bad[j[pen(A[i], ta[i], B[j], tb[j]) > EPS]] = True
        B, tb = B[~bad], tb[~bad]
    txy, tth = np.vstack([A, B]), np.r_[ta, tb]
    return fill_mis(L, txy, tth) if exact else fill(L, txy, tth)


def count(L, state):
    return len(build(L, *state)[0])


def fit(n):
    """Rows of band A (positive tilt) read off the record in best/."""
    d = np.load(f"best/n{n:03d}.npz")
    xy, th = sc.centered(d["xy"], d["th"])
    xy = xy - sc.corners(xy, th).reshape(-1, 2).min(0)
    L = float(d["L"])
    a = (th + math.pi / 4) % (math.pi / 2) - math.pi / 4
    red = a > 0.05
    c, t = xy[red], a[red]
    tm = float(np.median(t))
    r = np.round(-(c @ [-math.sin(tm), math.cos(tm)]))
    rows = []
    for j in np.unique(r):
        m = r == j
        cj, tj = c[m], t[m]
        aj = float(np.median(tj))
        first = cj[np.argmin(cj[:, 0])]
        o = first[0] - float(sc.half_extent(np.array(aj)))
        rows.append((aj, int(m.sum()), max(0.0, o)))
    top = c[r == r.min()]
    y0 = L - float(sc.half_extent(np.array(rows[0][0]))) - top[:, 1].max()
    return L, max(0.0, y0), rows


def mutate(state, L, rng):
    y0, rows = state
    rows = [list(r) for r in rows]
    move = rng.integers(6)
    j = rng.integers(len(rows))
    if move == 0:
        rows[j][0] = float(np.clip(rows[j][0] + rng.normal(0, 0.01), 0.05, 0.75))
    elif move == 1:
        rows[j][1] = max(1, rows[j][1] + rng.choice((-1, 1)))
    elif move == 2:
        rows[j][2] = max(0.0, rows[j][2] + rng.normal(0, 0.05))
    elif move == 3:
        y0 = max(0.0, y0 + rng.normal(0, 0.05))
    elif move == 4 and len(rows) > 1:
        rows.pop(j)
    else:
        rows.insert(j, list(rows[j]))
    return y0, [tuple(r) for r in rows]


def random_state(L, rng):
    a = rng.uniform(0.2, 0.5)
    R = rng.integers(4, int(L * 0.7))
    return rng.uniform(0, 2), [(a + rng.normal(0, 0.02), int(rng.integers(2, 8)),
                                rng.uniform(0, 1)) for _ in range(R)]


def climb(L, state, steps, rng):
    c = count(L, state)
    for _ in range(steps):
        s = mutate(state, L, rng)
        cs = count(L, s)
        if cs >= c:
            state, c = s, cs
    return state, c


def finish(n, L, state):
    xy, th = build(L, *state, exact=True)
    if len(xy) < n:
        return f"exact fill {len(xy)}, short"
    ok0 = sc.is_valid(xy, th)[0]
    xy, th = xy[:n], th[:n]
    p, _ = cp.polish(cp.to_packing(xy, th))
    xy, th = p[:, :2], p[:, 2]
    ok = sc.is_valid(xy, th)[0]
    line = f"build valid={ok0} -> polished L={sc.container_side(xy, th):.6f} valid={ok}"
    if ok and sc.store_best(n, xy, th):
        line += " STORED"
    return line


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--L", type=float, help="side to fill (default: best/ record)")
    ap.add_argument("--fit", type=int, nargs="?", const=-1, metavar="N",
                    help="start from the rows of the record for N (default: --n)")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    L = a.L or float(np.load(f"best/n{a.n:03d}.npz")["L"])

    best, best_c = None, -1
    if a.fit:
        _, y0, rows = fit(a.n if a.fit < 0 else a.fit)
        best = (y0, rows)
        best_c = count(L, best)
        print(f"fitted rows: {len(rows)}, a = {[round(math.degrees(r[0]), 1) for r in rows]}, "
              f"m = {[r[1] for r in rows]}  -> {best_c} squares", flush=True)
    end = time.time() + a.seconds
    while time.time() < end and best_c < a.n:
        start = best if a.fit else random_state(L, rng)
        s, c = climb(L, start, a.steps, rng)
        if c > best_c:
            best, best_c = s, c
            print(f"  {c} squares, {len(s[1])} rows", flush=True)
    line = f"n={a.n} L={L:.5f} fits {best_c} (need {a.n})"
    if best_c >= a.n - 8:  # the exact fill adds slid squares the greedy one misses
        line += " " + finish(a.n, L, best)
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
