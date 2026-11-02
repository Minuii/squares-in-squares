"""round_to_square.py -- grow circles into squares, optionally under gravity.

EXPERIMENTAL: as of 2026-11-02 this finds nothing. See plan.md, "Rounding the
squares helps a little, not enough". Asks whether starting from round pieces, which slide and turn
freely, reaches packings that a penalty search on hard squares does not.

The piece is a rounded square: a core square of side 1 - 2r grown by a disc of
radius r. r = 0.5 is a unit circle, r = 0 is the unit square, and every piece
has width 1 along its own axes, so the area bound stays the same throughout.

    starts      B random layouts, random angles, in a box 15% above the target
    continuation  r falls from 0.5 to 0 while the box shrinks to the target T;
                Adam minimises the summed squared overlap plus wall overlap
    gravity     optional: a pull toward the corner (0, 0) of strength g that
                fades to zero with r, so the pieces settle like falling sand
                instead of only being pushed in by the walls
    finish      L-BFGS on hard squares in float64, then contact_polish.repair
                and polish; a start counts if it is valid with side <= T

Two rounded squares overlap by 2r minus the distance between their cores. When
the cores are apart, that distance is the smallest vertex-to-square distance
over both squares' corners. When the cores overlap, it is minus their
separating-axis depth.

    python experiments/round_to_square.py --n 10 11 17 18 19 --compare
    python experiments/round_to_square.py --n 52 --delta 0.002 --gravity 0.05
    python experiments/round_to_square.py --n 260 --warm --r0 0.05 --delta 2e-4
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

import numpy as np
import torch

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import contact_polish as cp
import gpu_search as gs
import squares_core as sc

SIGNS = torch.tensor([[-1, -1], [1, -1], [1, 1], [-1, 1]], dtype=torch.float64)


def core_gap(P: torch.Tensor, pairs: torch.Tensor, a: float) -> torch.Tensor:
    """(B, K) signed distance between the core squares (half-side a) of each pair."""
    x, y, t = P[..., 0], P[..., 1], P[..., 2]
    c, s = torch.cos(t), torch.sin(t)
    i, j = pairs[:, 0], pairs[:, 1]
    dx, dy = x[:, j] - x[:, i], y[:, j] - y[:, i]
    ci, si, cj, sj = c[:, i], s[:, i], c[:, j], s[:, j]
    proj = torch.stack([
        (dx * ci + dy * si).abs(), (-dx * si + dy * ci).abs(),
        (dx * cj + dy * sj).abs(), (-dx * sj + dy * cj).abs(),
    ]).amax(dim=0)
    dt = t[:, j] - t[:, i]
    sep = proj - a * (1 + torch.cos(dt).abs() + torch.sin(dt).abs())
    if a <= 0:
        return sep

    def vertex_dist(cx, cy, ca, sa, ox, oy, cb, sb):
        # corners of square A, measured in square B's frame
        k = SIGNS.to(P)
        vx = cx[..., None] + a * (k[:, 0] * ca[..., None] - k[:, 1] * sa[..., None])
        vy = cy[..., None] + a * (k[:, 0] * sa[..., None] + k[:, 1] * ca[..., None])
        rx, ry = vx - ox[..., None], vy - oy[..., None]
        u = torch.relu((rx * cb[..., None] + ry * sb[..., None]).abs() - a)
        v = torch.relu((-rx * sb[..., None] + ry * cb[..., None]).abs() - a)
        return torch.sqrt(u * u + v * v + 1e-30).amin(dim=-1)

    xi, yi, xj, yj = x[:, i], y[:, i], x[:, j], y[:, j]
    dist = torch.minimum(vertex_dist(xi, yi, ci, si, xj, yj, cj, sj),
                         vertex_dist(xj, yj, cj, sj, xi, yi, ci, si))
    return torch.where(sep < 0, sep, dist)


def energy(P: torch.Tensor, pairs: torch.Tensor, T: float, r: float,
           g: float) -> torch.Tensor:
    """(B,) overlap penalty for rounded squares of corner radius r in [0, T]^2."""
    a = 0.5 - r
    e = torch.relu(2 * r - core_gap(P, pairs, a)).pow(2).sum(dim=1)
    x, y, t = P[..., 0], P[..., 1], P[..., 2]
    h = a * (torch.cos(t).abs() + torch.sin(t).abs()) + r
    for v in (x, y):
        e = e + (torch.relu(h - v).pow(2) + torch.relu(v + h - T).pow(2)).sum(dim=1)
    if g > 0:
        e = e + g * ((x - h) + (y - h)).sum(dim=1) / P.shape[1]
    return e


def search(n: int, T: float, batch: int, steps: int, gravity: float, rounded: bool,
           rng, dtype=torch.float32, warm: np.ndarray | None = None,
           r0: float = 0.5, jitter: float = 0.0) -> list[np.ndarray]:
    if warm is None:
        L0 = 1.15 * T
        P0 = np.empty((batch, n, 3))
        P0[..., :2] = rng.uniform(0.5, L0 - 0.5, (batch, n, 2))
        P0[..., 2] = rng.uniform(0, math.pi / 2, (batch, n))
        lr0 = 0.02
    else:
        # the record, jittered; rounding r0 frees its corners while the box
        # shrinks from its side to T
        L0 = cp.side(warm)
        P0 = np.repeat(cp.normalize(warm)[None], batch, axis=0)
        P0 += rng.normal(0, jitter, P0.shape) * (np.arange(batch) % 4 + 1)[:, None, None]
        lr0 = max(jitter, 1e-4)
    P = torch.tensor(P0, dtype=dtype, requires_grad=True)
    opt = torch.optim.Adam([P], lr=lr0)
    pairs = gs.near_pairs(P.detach(), 2.0)
    for k in range(steps):
        f = k / steps
        shape = max(0.0, 1 - f / 0.7)            # 1 while round, 0 once square
        r = r0 * shape if rounded else 0.0
        box = T + (L0 - T) * max(0.0, 1 - f / 0.6)
        for grp in opt.param_groups:
            grp["lr"] = lr0 * (1 - f) + lr0 / 100
        if k % 20 == 0:
            pairs = gs.near_pairs(P.detach(), 2.0)
        opt.zero_grad()
        energy(P, pairs, box, r, gravity * shape).sum().backward()
        opt.step()

    # finish on hard squares, as gpu_search does
    P = P.detach().to(torch.float64).requires_grad_(True)
    lbfgs = torch.optim.LBFGS([P], lr=1.0, max_iter=50, history_size=20,
                              line_search_fn="strong_wolfe")
    for _ in range(gs.args_lbfgs_rounds):
        pairs = gs.near_pairs(P.detach(), 1.7)

        def closure():
            lbfgs.zero_grad()
            e = gs.energy(P, pairs, T, 1.0 + gs.INFLATE).sum()
            e.backward()
            return e

        lbfgs.step(closure)
    with torch.no_grad():
        e = gs.energy(P, gs.near_pairs(P, 1.6), T, 1.0)
    return [P[b].detach().numpy() for b in (e < 1e-14).nonzero().flatten().tolist()]


def hits(cands: list[np.ndarray], T: float) -> list[np.ndarray]:
    """Candidates that repair to a valid packing of side <= T (plus rounding)."""
    out = []
    for p in cands:
        q = cp.repair(p)
        if q is None:
            continue
        ok, info = sc.is_valid(q[:, :2], q[:, 2])
        if ok and info["L"] <= T + 1e-6:
            out.append(q)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="+", required=True)
    ap.add_argument("--delta", type=float, default=0.0,
                    help="target is best L minus delta; 0 asks only to match the record")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--gravity", type=float, default=0.0)
    ap.add_argument("--hard", action="store_true", help="squares from the start, no rounding")
    ap.add_argument("--compare", action="store_true",
                    help="run hard, round, and round + gravity on the same seeds")
    ap.add_argument("--warm", action="store_true",
                    help="start from the record in best/ instead of random layouts")
    ap.add_argument("--r0", type=float, default=0.5,
                    help="starting corner radius; small for warm starts")
    ap.add_argument("--jitter", type=float, default=0.002, help="warm-start noise")
    ap.add_argument("--polish-seconds", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="found")
    args = ap.parse_args()

    if args.compare:
        g = args.gravity or 0.05
        variants = [("hard", False, 0.0), ("round", True, 0.0), ("round+gravity", True, g)]
    else:
        variants = [("hard" if args.hard else "round", not args.hard, args.gravity)]
    L = gs.best_sides()
    out = pathlib.Path(args.out)
    for n in args.n:
        T = L[n] - args.delta
        for name, rounded, g in variants:
            t0 = time.time()
            rng = np.random.default_rng(args.seed + n)
            warm = gs.load_packing(n) if args.warm else None
            cands = search(n, T, args.batch, args.steps, g, rounded, rng, warm=warm,
                           r0=args.r0, jitter=args.jitter)
            if args.warm:
                q = gs.finish(n, cands, L[n], args.polish_seconds) if cands else None
                got = [] if q is None else [q]
            else:
                got = hits(cands, T)
            best = min((cp.side(q) for q in got), default=None)
            if got and best < L[n] - 1e-9:
                out.mkdir(parents=True, exist_ok=True)
                q = min(got, key=cp.side)
                np.savez(out / f"n{n:03d}.npz", xy=q[:, :2], th=q[:, 2], L=cp.side(q))
            print(json.dumps(dict(n=n, variant=name, target=round(T, 8),
                                  record=round(L[n], 8), hits=len(got), of=args.batch,
                                  best=best and round(best, 8),
                                  seconds=round(time.time() - t0, 1))), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
