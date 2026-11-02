"""
squares_core.py -- geometry, exact feasibility check, metric, and a
shrink-wrap optimizer for the "Squares in Squares" playground competition.

Everything here is plain NumPy so it runs on a Kaggle CPU kernel with no
extra installs. This file is the single source of truth: the notebook embeds
this text verbatim in one cell (see build_notebook.py).

Conventions
-----------
* A packing is (xy, th): xy is (n, 2) centres, th is (n,) angles in radians.
* A square is the closed set  c + R(th) . [-1/2, 1/2]^2  (side length 1).
* The container is *derived*, never chosen: it is the tightest axis-aligned
  square around the union, i.e.  L = max(x-extent, y-extent).
  So there are no boundary constraints at all -- only non-overlap matters.
"""

from __future__ import annotations

import numpy as np

# A pair is "overlapping" if its interiors share area. Touching is legal
# (the statement of the problem is about interiors), but floating point means
# we always finish with a small positive gap, see `polish`.
GAP = 1e-7
# Penetration below this is treated as numerical dust, not a violation.
TOL = 1e-9


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def pairs(n: int) -> tuple[np.ndarray, np.ndarray]:
    """All index pairs i < j."""
    return np.triu_indices(n, 1)


def half_extent(th: np.ndarray) -> np.ndarray:
    """Half-width of a unit square rotated by th, along the x axis.

    Same value along y: a unit square rotated by th has axis-aligned
    bounding box side (|cos th| + |sin th|)."""
    return 0.5 * (np.abs(np.cos(th)) + np.abs(np.sin(th)))


def corners(xy: np.ndarray, th: np.ndarray) -> np.ndarray:
    """(n, 4, 2) array of the four corners of every square."""
    c, s = np.cos(th), np.sin(th)
    lx = np.array([-0.5, 0.5, 0.5, -0.5])
    ly = np.array([-0.5, -0.5, 0.5, 0.5])
    x = xy[:, 0:1] + c[:, None] * lx - s[:, None] * ly
    y = xy[:, 1:2] + s[:, None] * lx + c[:, None] * ly
    return np.stack([x, y], axis=-1)


def container_side(xy: np.ndarray, th: np.ndarray) -> float:
    """L, the side of the tightest axis-aligned square around the union."""
    p = corners(xy, th)
    x, y = p[..., 0], p[..., 1]
    return float(max(x.max() - x.min(), y.max() - y.min()))


def score(L: float, n: int) -> float:
    """Competition metric for one puzzle."""
    return L / np.sqrt(n) - 1.0


def store_best(n: int, xy: np.ndarray, th: np.ndarray, best_dir=None) -> bool:
    """Save best/nNNN.npz only if it beats what is there. True if written."""
    from pathlib import Path

    path = Path(best_dir or "best") / f"n{n:03d}.npz"
    L = container_side(xy, th)
    if path.exists() and float(np.load(path)["L"]) <= L + 1e-12:
        return False
    path.parent.mkdir(exist_ok=True)
    np.savez(path, xy=xy, th=th, L=L)
    return True


def grid_side(n: int) -> int:
    """Side of the trivial grid packing: ceil(sqrt n)."""
    return int(np.ceil(np.sqrt(n) - 1e-12))


# --------------------------------------------------------------------------
# exact feasibility: separating-axis test for two rotated squares
# --------------------------------------------------------------------------
def sat_depths(xy: np.ndarray, th: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-pair penetration depth along the four SAT axes.

    Returns (depth, axes, delta) with shapes (P, 4), (P, 4, 2), (P, 2).
    depth[p, k] > 0  <=>  the projections overlap on axis k.
    For convex polygons, "interiors intersect" <=> every axis overlaps, so the
    penetration depth of the pair is depth.min(axis=1).
    """
    n = len(xy)
    iu, ju = pairs(n)
    c, s = np.cos(th), np.sin(th)
    U = np.stack([c, s], axis=-1)          # square edge directions
    V = np.stack([-s, c], axis=-1)
    axes = np.stack([U[iu], V[iu], U[ju], V[ju]], axis=1)   # (P, 4, 2), unit
    delta = xy[ju] - xy[iu]
    proj = np.abs(np.einsum("pkd,pd->pk", axes, delta))
    r = 0.5 * (
        np.abs(np.einsum("pkd,pd->pk", axes, U[iu]))
        + np.abs(np.einsum("pkd,pd->pk", axes, V[iu]))
        + np.abs(np.einsum("pkd,pd->pk", axes, U[ju]))
        + np.abs(np.einsum("pkd,pd->pk", axes, V[ju]))
    )
    return r - proj, axes, delta


def max_penetration(xy: np.ndarray, th: np.ndarray) -> float:
    """Largest pairwise penetration depth. <= 0 means pairwise disjoint."""
    n = len(xy)
    if n < 2:
        return 0.0
    depth, _, _ = sat_depths(xy, th)
    return float(depth.min(axis=1).max())


def is_valid(xy: np.ndarray, th: np.ndarray) -> tuple[bool, dict]:
    """Independent validation, mirroring what the grader must check."""
    n = len(xy)
    pen = max_penetration(xy, th)
    L = container_side(xy, th)
    finite = bool(np.isfinite(xy).all() and np.isfinite(th).all())
    ok = finite and pen <= TOL and L > 0
    return ok, {"max_penetration": pen, "L": L, "finite": finite, "n": n}


# --------------------------------------------------------------------------
# constructions
# --------------------------------------------------------------------------
def grid(n: int) -> tuple[np.ndarray, np.ndarray]:
    """The trivial baseline: n axis-aligned squares in a k x k grid."""
    k = grid_side(n)
    idx = np.arange(n)
    xy = np.stack([idx % k + 0.5, idx // k + 0.5], axis=-1).astype(float)
    return xy, np.zeros(n)


def centered(xy: np.ndarray, th: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Translate so the bounding box starts at the origin."""
    p = corners(xy, th)
    lo = p.reshape(-1, 2).min(axis=0)
    return xy - lo, th


# --------------------------------------------------------------------------
# the shrink-wrap optimizer
# --------------------------------------------------------------------------
def relax(
    xy: np.ndarray,
    th: np.ndarray,
    L: float,
    iters: int,
    rng: np.random.Generator,
    step: float = 0.55,
    sigma: float = 0.0,
    sigma_decay: float = 0.995,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Push the packing into the window [0, L]^2 and kill overlaps.

    Pure physics: each overlapping pair is separated along its minimum
    translation vector; squares are projected back into the container box.
    `sigma` adds rotational noise to squares that are still in conflict, which
    is what lets the search discover rotated configurations.
    Returns the configuration and the residual penetration.
    """
    xy = xy.copy()
    th = th.copy()
    n = len(xy)
    if n > 1:
        iu, ju = pairs(n)

    for _ in range(iters):
        h = half_extent(th)
        hi = np.maximum(L - h, h)
        xy[:, 0] = np.clip(xy[:, 0], h, hi)
        xy[:, 1] = np.clip(xy[:, 1], h, hi)
        if n < 2:
            return xy, th, 0.0

        depth, axes, delta = sat_depths(xy, th)
        pen = depth.min(axis=1)
        if pen.max() <= 0.0:
            return xy, th, 0.0

        act = pen > 0.0
        k = np.argmin(depth, axis=1)
        # unit MTV axis and the sign that pushes j away from i
        a = axes[np.arange(len(k)), k]
        sgn = np.sign(np.einsum("pd,pd->p", a, delta))
        sgn[sgn == 0.0] = 1.0
        vec = (a * sgn[:, None]) * (0.5 * step * pen)[:, None] * act[:, None]

        dx = np.zeros((n, 2))
        cnt = np.zeros((n, 1))
        np.add.at(dx, iu, -vec)
        np.add.at(dx, ju, +vec)
        np.add.at(cnt, iu, act[:, None])
        np.add.at(cnt, ju, act[:, None])
        xy += dx / np.maximum(cnt, 1.0)

        if sigma > 0.0:
            hot = np.zeros(n, dtype=bool)
            hot[iu[act]] = True
            hot[ju[act]] = True
            th[hot] += rng.normal(0.0, sigma, size=int(hot.sum()))
            sigma *= sigma_decay

    if n < 2:
        return xy, th, 0.0
    depth, _, _ = sat_depths(xy, th)
    return xy, th, float(depth.min(axis=1).max())


def _fit_into(xy, th, window, rng, iters, sigma, step=0.9):
    """Re-centre and squash a packing into a smaller window, then repair it.

    Returns candidate (xy, th, L, penetration)."""
    xy, th = centered(xy, th)
    cur = container_side(xy, th)
    scale = min(window / max(cur, 1e-12), 1.0)
    xy = xy * scale
    xy, th, pen = relax(xy, th, window, iters, rng, step=step, sigma=sigma)
    xy, th = centered(xy, th)
    return xy, th, container_side(xy, th), pen


def shrink(
    n: int,
    start: tuple[np.ndarray, np.ndarray] | None = None,
    goal: float | None = None,
    rounds: int = 70,
    iters: int = 400,
    eta: float = 0.004,
    sigma: float = 0.08,
    step: float = 0.9,
    kicks: int = 0,
    seed: int = 0,
    log=None,
) -> dict:
    """Shrink-wrap by bisection on the container side.

    Maintains a feasible side `hi` and an infeasible side `lo`; each round
    tries the midpoint (or at least an `eta` improvement), repairs overlaps
    inside that window, and moves whichever bracket end the result lands on.
    `goal` is a hard floor on L (default: the area bound sqrt(n)).
    """
    rng = np.random.default_rng(seed)
    if start is None:
        xy, th = centered(*grid(n))
    else:
        xy, th = centered(start[0].copy(), start[1].copy())
    if goal is None:
        goal = float(np.sqrt(n))
    goal = max(goal, float(np.sqrt(n)))

    hi = container_side(xy, th)
    best = {"L": hi, "xy": xy.copy(), "th": th.copy()}
    step_frac = eta
    fails = 0

    for r in range(rounds):
        window = max(hi * (1.0 - step_frac), goal)
        if window >= hi * (1.0 - 1e-12):
            break
        xy1, th1, L1, pen = _fit_into(
            best["xy"], best["th"], window, rng, iters,
            sigma * (1.0 - 0.6 * r / max(rounds, 1)), step)
        if pen <= TOL and L1 <= window * (1.0 + 1e-12):
            hi = min(L1, window)
            best = {"L": hi, "xy": xy1.copy(), "th": th1.copy()}
            fails = 0
            step_frac = min(eta, step_frac * 1.5)
            if log:
                log(f"  n={n:4d} r{r:3d}  L={hi:.10f}  score={score(hi, n):.6f}")
        else:
            fails += 1
            step_frac *= 0.5
            if fails >= 4 and kicks > 0:
                # basin hop: shake the best configuration and retry the window
                th0 = best["th"] + rng.normal(0.0, 0.3, size=n)
                xy0, th0_, L0, pen0 = _fit_into(best["xy"], th0, window, rng, iters,
                                               sigma * 2.5, step)
                if pen0 <= TOL and L0 < hi:
                    hi, best = L0, {"L": L0, "xy": xy0.copy(), "th": th0_.copy()}
                    if log:
                        log(f"  n={n:4d} kick  L={hi:.10f}  score={score(hi, n):.6f}")
                fails = 0
                step_frac = eta
            if step_frac < 1e-7:
                step_frac = eta  # restart the fine step after a kick

    return {"n": n, "L": best["L"], "xy": best["xy"], "th": best["th"],
            "score": score(best["L"], n)}


def polish(xy: np.ndarray, th: np.ndarray, rng, iters: int = 300) -> tuple[np.ndarray, np.ndarray]:
    """Finish with a strictly positive gap so the grader sees no overlap.

    Inflates the squares by GAP and re-separates; the container grows by about
    2*GAP, which is far below the submission's rounding error.
    """
    n = len(xy)
    if n < 2:
        return xy, th
    iu, ju = pairs(n)
    xy = xy.copy()
    th = th.copy()
    for _ in range(iters):
        depth, axes, delta = sat_depths(xy, th)
        pen = depth.min(axis=1)
        bad = pen > -GAP
        if not bad.any():
            break
        k = np.argmin(depth, axis=1)
        a = axes[np.arange(len(k)), k]
        sgn = np.sign(np.einsum("pd,pd->p", a, delta))
        sgn[sgn == 0.0] = 1.0
        push = (pen + GAP).clip(min=0.0)
        vec = (a * sgn[:, None]) * (0.55 * push)[:, None] * bad[:, None]
        dx = np.zeros((n, 2))
        cnt = np.zeros((n, 1))
        np.add.at(dx, iu, -vec)
        np.add.at(dx, ju, +vec)
        np.add.at(cnt, iu, bad[:, None])
        np.add.at(cnt, ju, bad[:, None])
        xy += dx / np.maximum(cnt, 1.0)
    return xy, th


# --------------------------------------------------------------------------
# simulated annealing on a fixed window: "is L feasible?"
# --------------------------------------------------------------------------
def _pen_vs_all(xy, th, i):
    """Penetration depth of square i against every other square (n,)."""
    n = len(xy)
    c, s = np.cos(th), np.sin(th)
    U = np.stack([c, s], axis=-1)
    V = np.stack([-s, c], axis=-1)
    j = np.arange(n)
    A = np.stack([np.broadcast_to(U[i], (n, 2)), np.broadcast_to(V[i], (n, 2)),
                  U, V], axis=1)                     # (n, 4, 2)
    delta = xy - xy[i]
    proj = np.abs(np.einsum("pkd,pd->pk", A, delta))
    r = 0.5 * (np.abs(A @ U[i]) + np.abs(A @ V[i])
               + np.abs(np.einsum("pkd,pd->pk", A, U))
               + np.abs(np.einsum("pkd,pd->pk", A, V)))
    depth = (r - proj).min(axis=1)
    depth[i] = -np.inf
    return depth


def energy(xy, th, L, wall=4.0):
    """Penalty: squared penetration of every overlapping pair plus squared
    excursion of any square outside the window [0, L]^2. Zero <=> feasible."""
    n = len(xy)
    e = 0.0
    if n > 1:
        depth, _, _ = sat_depths(xy, th)
        pen = np.maximum(depth.min(axis=1), 0.0)
        e += float(np.sum(pen * pen))
    h = half_extent(th)
    vx = np.maximum(h - xy[:, 0], 0.0) + np.maximum(xy[:, 0] + h - L, 0.0)
    vy = np.maximum(h - xy[:, 1], 0.0) + np.maximum(xy[:, 1] + h - L, 0.0)
    e += wall * float(np.sum(vx * vx + vy * vy))
    return e


def sa_feasible(
    n: int,
    L: float,
    iters: int = 40000,
    T0: float = 4e-3,
    T1: float = 2e-6,
    move: float = 0.10,
    rot: float = 0.30,
    wall: float = 4.0,
    rng: np.random.Generator | None = None,
    init: tuple[np.ndarray, np.ndarray] | None = None,
):
    """Metropolis search for a zero-energy (overlap-free, inside) packing.

    Incremental energy: a move touches one square, so only that square's row of
    pairwise penalties and its wall term are recomputed.
    """
    rng = rng or np.random.default_rng(0)
    if init is None:
        xy = rng.random((n, 2)) * L
        th = rng.random(n) * np.pi
    else:
        xy, th = init[0].copy(), init[1].copy()
    xy = np.clip(xy, 0.0, L)

    cur = energy(xy, th, L, wall)
    best = (cur, xy.copy(), th.copy())
    logT = np.log(T0)
    dlog = (np.log(T1) - logT) / max(iters - 1, 1)

    for it in range(iters):
        T = np.exp(logT + dlog * it)
        i = int(rng.integers(n))
        ox, oy, oth = xy[i, 0], xy[i, 1], th[i]
        old_row = 0.0
        if n > 1:
            d_old = np.maximum(_pen_vs_all(xy, th, i), 0.0)
            old_row = float(np.sum(d_old * d_old))
        h_old = half_extent(th[i])
        vx = max(h_old - xy[i, 0], 0.0) + max(xy[i, 0] + h_old - L, 0.0)
        vy = max(h_old - xy[i, 1], 0.0) + max(xy[i, 1] + h_old - L, 0.0)
        old_wall = wall * (vx * vx + vy * vy)

        scale = move * L * (0.35 + 0.65 * T / T0)
        xy[i, 0] = ox + rng.normal(0.0, scale)
        xy[i, 1] = oy + rng.normal(0.0, scale)
        if rng.random() < 0.5:
            th[i] = oth + rng.normal(0.0, rot * (0.35 + 0.65 * T / T0))

        new_row = 0.0
        if n > 1:
            d_new = np.maximum(_pen_vs_all(xy, th, i), 0.0)
            new_row = float(np.sum(d_new * d_new))
        h_new = half_extent(th[i])
        vx = max(h_new - xy[i, 0], 0.0) + max(xy[i, 0] + h_new - L, 0.0)
        vy = max(h_new - xy[i, 1], 0.0) + max(xy[i, 1] + h_new - L, 0.0)
        new_wall = wall * (vx * vx + vy * vy)

        delta = (new_row + new_wall) - (old_row + old_wall)
        if delta <= 0.0 or rng.random() < np.exp(-delta / max(T, 1e-12)):
            cur += delta
            if cur < best[0] - 1e-15:
                best = (cur, xy.copy(), th.copy())
                if cur <= 1e-18:
                    break
        else:
            xy[i, 0], xy[i, 1], th[i] = ox, oy, oth

    return best[0], best[1], best[2]


def sa_descent(
    n: int,
    start: tuple[np.ndarray, np.ndarray] | None = None,
    goal: float | None = None,
    rounds: int = 40,
    iters: int = 30000,
    eta: float = 0.01,
    seed: int = 0,
    log=None,
) -> dict:
    """Descend the container side, asking SA each round whether it is feasible."""
    rng = np.random.default_rng(seed)
    if goal is None:
        goal = float(np.sqrt(n))
    goal = max(goal, float(np.sqrt(n)))

    if start is None:
        xy, th = centered(*grid(n))
        # start already inside its own window
        L = container_side(xy, th)
    else:
        xy, th = start[0].copy(), start[1].copy()
        L = container_side(xy, th)
        xy, th = centered(xy, th)
    best = {"L": L, "xy": xy.copy(), "th": th.copy()}

    for r in range(rounds):
        target = max(L * (1.0 - eta), goal)
        if target >= L * (1.0 - 1e-12):
            break
        # squash the incumbent into the candidate window, then anneal
        x0 = xy.copy() * min(target / max(container_side(xy, th), 1e-12), 1.0)
        e, x1, t1 = sa_feasible(n, target, iters=iters, rng=rng, init=(x0, th))
        x1, t1 = centered(x1, t1)
        if e <= 1e-14 and max_penetration(x1, t1) <= TOL:
            L = min(container_side(x1, t1), target)
            best = {"L": L, "xy": x1.copy(), "th": t1.copy()}
            xy, th = x1, t1
            if log:
                log(f"  n={n:4d} r{r:3d}  L={L:.10f}  score={score(L, n):.6f}")
        else:
            # infeasible: try once more from the incumbent with fresh noise
            e, x2, t2 = sa_feasible(n, target, iters=iters, rng=rng, init=(x0, th))
            x2, t2 = centered(x2, t2)
            if e <= 1e-14 and max_penetration(x2, t2) <= TOL:
                L = min(container_side(x2, t2), target)
                best = {"L": L, "xy": x2.copy(), "th": t2.copy()}
                xy, th = x2, t2
            else:
                eta *= 0.6
                if eta < 1e-5:
                    break

    return {"n": n, "L": best["L"], "xy": best["xy"], "th": best["th"],
            "score": score(best["L"], n)}


# --------------------------------------------------------------------------
# submission I/O
# --------------------------------------------------------------------------
def submission_rows(solutions: dict[int, tuple[np.ndarray, np.ndarray]]) -> list[tuple]:
    """(id, n, square_id, x, y, angle) rows in the required format."""
    rows = []
    sid = 0
    for n in sorted(solutions):
        xy, th = solutions[n]
        xy, th = centered(xy, th)
        for i in range(n):
            rows.append(
                (sid, n, i, float(xy[i, 0]), float(xy[i, 1]), float(th[i]))
            )
            sid += 1
    return rows


def write_submission(path: str, solutions: dict[int, tuple[np.ndarray, np.ndarray]]) -> None:
    """Write the CSV with plain decimal literals (repr is exact round-trip)."""
    rows = submission_rows(solutions)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("id,n,square_id,x,y,angle\n")
        for sid, n, i, x, y, t in rows:
            f.write(f"{sid},{n},{i},{x!r},{y!r},{t!r}\n")


def evaluate_submission(path: str, n_max: int = 1000) -> dict:
    """Re-read our own CSV and recompute the leaderboard sum exactly.

    Same scoring as the grader: group by n, rebuild the packing, check
    non-overlap, compute L, charge the grid ceiling for any puzzle that is
    missing or invalid. The overlap test here is a fast double-precision one
    with tolerance TOL; the grader's is stricter, see grader_check.py.
    """
    import csv

    by_n: dict[int, list[tuple]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = int(row["n"])
            by_n.setdefault(n, []).append(
                (float(row["x"]), float(row["y"]), float(row["angle"]))
            )

    total = 0.0
    detail = []
    for n in range(1, n_max + 1):
        if n not in by_n or len(by_n[n]) != n:
            total += grid_side(n) / np.sqrt(n) - 1.0
            detail.append((n, grid_side(n), "grid (missing/partial)"))
            continue
        xy = np.array([(r[0], r[1]) for r in by_n[n]])
        th = np.array([r[2] for r in by_n[n]])
        ok, info = is_valid(xy, th)
        if ok:
            L = info["L"]
            total += L / np.sqrt(n) - 1.0
            detail.append((n, L, "packed"))
        else:
            total += grid_side(n) / np.sqrt(n) - 1.0
            detail.append((n, grid_side(n), f"invalid ({info['max_penetration']:.2e})"))
    return {"total": total, "detail": detail}
