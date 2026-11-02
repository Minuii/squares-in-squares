"""contact_polish.py -- shrink a packing with a trust-region sequential LP.

Adapted from lightningv08, "CUDA Packing Search" (Apache-2.0), as carried in
malyshevdanil's "Squares in Squares Living Atlas of Tight Packings" notebook,
which credits the coupled sparse LP idea to prvsiyan's "A Square Deal".

Each round linearises the problem around the current packing:

    variables   a small move (dx, dy, dtheta) for every square, and dL
    contacts    for every pair within 1.75, keep the separating axis that is
                widest now, and require the linearised gap on it to stay >= 0
    walls       every square stays inside [0, L + dL] on both axes
    objective   minimise dL, plus a tiny L1 penalty on the moves

HiGHS solves it, and the move is line-searched. A trial is accepted only after
`repair` rescales the centres until every near pair is provably apart, and only
if the side really shrank. The trust region grows on success and shrinks on
failure.

A packing here is an (n, 3) array of (x, y, theta).

    python src/contact_polish.py --n 376        # try one puzzle
"""
from __future__ import annotations

import argparse
import math
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

CLEARANCE = 4e-11


def side(p: np.ndarray) -> float:
    h = (np.abs(np.cos(p[:, 2])) + np.abs(np.sin(p[:, 2]))) / 2
    lo = (p[:, :2] - h[:, None]).min(axis=0)
    hi = (p[:, :2] + h[:, None]).max(axis=0)
    return float(np.max(hi - lo))


def normalize(p: np.ndarray, margin: float = 0.0) -> np.ndarray:
    """Scale centres by 1 + margin, then translate the box to the origin."""
    p = np.asarray(p, dtype=float).copy()
    p[:, :2] *= 1 + margin
    h = (np.abs(np.cos(p[:, 2])) + np.abs(np.sin(p[:, 2]))) / 2
    p[:, :2] -= (p[:, :2] - h[:, None]).min(axis=0)
    return p


def repair(p: np.ndarray, clearance: float = CLEARANCE) -> np.ndarray | None:
    """Rescale centres so every near pair clears by `clearance`, or None.

    Two unit squares are apart if, along one of their four edge directions,
    the centre distance is at least 0.5 plus the other square's half-width
    there, 0.5 * (1 + |cos(a - b)| + |sin(a - b)|). That is a sufficient test,
    so a repaired packing is valid. Pairs further than sqrt(2) apart are always
    disjoint. A rescale outside (0.9999, 1.003) means the move was bad.
    """
    p = normalize(p)
    pairs = cKDTree(p[:, :2]).query_pairs(1.42, output_type="ndarray")
    if not len(pairs):
        return p
    i, j = pairs.T
    d = p[j, :2] - p[i, :2]
    a, b = p[i, 2], p[j, 2]
    proj = np.maximum.reduce([
        abs(d[:, 0] * np.cos(a) + d[:, 1] * np.sin(a)),
        abs(-d[:, 0] * np.sin(a) + d[:, 1] * np.cos(a)),
        abs(d[:, 0] * np.cos(b) + d[:, 1] * np.sin(b)),
        abs(-d[:, 0] * np.sin(b) + d[:, 1] * np.cos(b)),
    ])
    rad = 0.5 * (1 + abs(np.cos(a - b)) + abs(np.sin(a - b)))
    f = max(1.0, float(np.max((rad + clearance) / np.maximum(proj, 1e-30))))
    if not 0.9999 < f < 1.003:
        return None
    p[:, :2] *= f
    return normalize(p)


def polish(p: np.ndarray, rounds: int = 80, seed: int = 0,
           max_seconds: float = 15.0) -> tuple[np.ndarray, int]:
    """Return (polished packing, accepted steps). Never returns a larger side."""
    p = normalize(p)
    n = len(p)
    rng = np.random.default_rng(seed)
    start = time.perf_counter()
    step = 0.025
    accepted = 0
    for _ in range(rounds):
        if time.perf_counter() - start > max_seconds:
            break
        L = side(p)
        theta = p[:, 2]
        c, s = np.cos(theta), np.sin(theta)
        h = (abs(c) + abs(s)) / 2

        edges = cKDTree(p[:, :2]).query_pairs(1.75, output_type="ndarray")
        if not len(edges):
            break
        i, j = edges.T
        d = p[j, :2] - p[i, :2]
        # the four candidate axes: both edge directions of i, then of j
        ux = np.column_stack((c[i], -s[i], c[j], -s[j]))
        uy = np.column_stack((s[i], c[i], s[j], c[j]))
        proj = d[:, 0, None] * ux + d[:, 1, None] * uy
        jitter = rng.uniform(-2e-12, 2e-12, proj.shape)
        chosen = (abs(proj) + jitter).argmax(axis=1)
        rr = np.arange(len(i))
        sign = np.sign(proj[rr, chosen])
        vx, vy = sign * ux[rr, chosen], sign * uy[rr, chosen]
        rotation = -d[:, 0] * vy + d[:, 1] * vx
        delta = theta[j] - theta[i]
        cd, sd = np.cos(delta), np.sin(delta)
        rad = (1 + abs(cd) + abs(sd)) / 2
        drad = (-sd * np.sign(cd) + cd * np.sign(sd)) / 2
        dist = abs(proj[rr, chosen])
        own = chosen < 2                       # axis belongs to square i

        rows, cols, vals, bounds = [], [], [], []
        count = [0]

        def add(cc, vv, bb):
            bb = np.asarray(bb)
            k = len(bb)
            rows.append(np.repeat(np.arange(count[0], count[0] + k), cc.shape[1]))
            cols.append(cc.ravel())
            vals.append(vv.ravel())
            bounds.append(bb)
            count[0] += k

        columns = np.column_stack((3 * i, 3 * i + 1, 3 * j, 3 * j + 1, 3 * i + 2, 3 * j + 2))
        values = np.column_stack((vx, vy, -vx, -vy,
                                  -drad - np.where(own, rotation, 0),
                                  drad - np.where(own, 0, rotation)))
        add(columns, values, dist - rad - CLEARANCE)
        # At relative right angles the radius has a kink: constrain both slopes.
        kink = np.flatnonzero(np.minimum(abs(cd), abs(sd)) < 1e-8)
        for slope in (-0.5, 0.5):
            vv = values[kink].copy()
            vv[:, 4] = -slope - np.where(own[kink], rotation[kink], 0)
            vv[:, 5] = slope - np.where(own[kink], 0, rotation[kink])
            add(columns[kink], vv, dist[kink] - rad[kink] - CLEARANCE)

        # walls, with the same kink treatment for axis-aligned squares
        k = np.arange(n)
        dh = (-s * np.sign(c) + c * np.sign(s)) / 2
        aligned = k[np.minimum(abs(c), abs(s)) < 1e-8]
        for dim in (0, 1):
            for upper in (False, True):
                for ids, deriv in ((k, dh),
                                   (aligned, np.full(len(aligned), -0.5)),
                                   (aligned, np.full(len(aligned), 0.5))):
                    cc = np.column_stack((3 * ids + dim, 3 * ids + 2, np.full(len(ids), 3 * n)))
                    vv = np.column_stack((np.full(len(ids), 1.0 if upper else -1.0), deriv,
                                          np.full(len(ids), -1.0 if upper else 0.0)))
                    bb = L - p[ids, dim] - h[ids] if upper else p[ids, dim] - h[ids]
                    add(cc, vv, bb)

        # |move| <= u, for the L1 penalty
        k3 = np.arange(3 * n)
        for sgn in (-1.0, 1.0):
            add(np.column_stack((k3, 3 * n + 1 + k3)), np.tile([sgn, -1.0], (3 * n, 1)),
                np.zeros(3 * n))

        A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(count[0], 6 * n + 1)).tocsr()
        objective = np.zeros(6 * n + 1)
        objective[3 * n] = 1.0
        objective[3 * n + 1:] = 2e-6
        trust = np.tile([step, step, step * 0.4], n)
        limits = list(zip(-trust, trust)) + [(-step, step)] + [(0, None)] * (3 * n)
        fit = linprog(objective, A_ub=A, b_ub=np.concatenate(bounds), bounds=limits,
                      method="highs",
                      options={"primal_feasibility_tolerance": 1e-10,
                               "dual_feasibility_tolerance": 1e-9, "time_limit": 2})
        if not fit.success:
            step *= 0.4
            if step < 2e-7:
                break
            continue

        move = fit.x[:3 * n].reshape(n, 3)
        winner = None
        for alpha in (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125):
            trial = repair(p + alpha * move)
            if trial is not None and side(trial) < L - 2e-10 and (
                    winner is None or side(trial) < side(winner)):
                winner = trial
        if winner is None:
            step *= 0.4
            if step < 2e-7:
                break
        else:
            p = winner
            accepted += 1
            step = min(0.06, step * 1.3)
    return p, accepted


def to_packing(xy: np.ndarray, th: np.ndarray) -> np.ndarray:
    return np.column_stack((xy, th))


def main() -> int:
    import squares_core as sc

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seconds", type=float, default=30.0)
    args = ap.parse_args()
    d = np.load(f"best/n{args.n:03d}.npz")
    p = to_packing(d["xy"], d["th"])
    q, steps = polish(p, seed=args.n, max_seconds=args.seconds)
    ok, info = sc.is_valid(q[:, :2], q[:, 2])
    print(f"n={args.n}  {side(p):.9f} -> {side(q):.9f}  steps={steps}  "
          f"valid={ok} pen={info['max_penetration']:.1e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
