"""gpu_search.py -- look for smaller packings with a batched penalty search.

EXPERIMENTAL: as of 2026-11-02 this finds nothing. See plan.md, "Penalty
search fails on these packings", for the measurements.

For one puzzle n with best side L, try a target side T < L:

    starts      B copies of the best packing, jittered, plus copies of the
                n + 1 packing with one square deleted
    penalty     sum over near pairs of relu(overlap)^2, plus squares outside
                [0, T]^2 squared; zero means a valid packing in side T
    search      Adam on all B starts at once, on the GPU if there is one
    continuation  the box shrinks from slightly above L down to T while the
                squares grow from 97% to full size, so they can slide past
                each other before they become rigid; the last phase inflates
                them a hair so contacts come out positive
    finish      every near-feasible start goes through contact_polish.repair
                and polish in float64, and is kept only if it is valid and
                smaller than L

For two unit squares the separating-axis radius is the same on all four of
their edge directions, 0.5 * (1 + |cos(dtheta)| + |sin(dtheta)|), so a pair's
overlap is that radius minus the largest projection of the centre gap.

Found packings go to --out as nNNN.npz; bring them home with import_found.py,
which only keeps strict improvements, then run make_submission.py.

    python experiments/gpu_search.py --n 376 --minutes 10
    python experiments/gpu_search.py --auto 20 --minutes 120 --out found
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
import contact_polish as cp
import squares_core as sc

BEST = pathlib.Path("best")
N_MAX = 1000
args_lbfgs_rounds = 8          # outer L-BFGS rounds, each up to 50 iterations
INFLATE = 2e-9                 # final-phase oversize, so contacts end open


# --------------------------------------------------------------------------
# which puzzles to search
# --------------------------------------------------------------------------
def best_sides() -> dict[int, float]:
    out = {}
    for n in range(1, N_MAX + 1):
        path = BEST / f"n{n:03d}.npz"
        g = float(sc.grid_side(n))
        out[n] = min(g, float(np.load(path)["L"])) if path.exists() else g
    return out


def seed_weights(L: dict[int, float]) -> dict[int, float]:
    """For each seed (a packing not derived from another by lift or delete),
    the sum of 1/sqrt(m) over every puzzle m its improvement would reach."""
    parent = {}
    for n in range(1, N_MAX + 1):
        m = n + 2 * math.floor(L[n]) + 1
        if m <= N_MAX and abs(L[m] - (L[n] + 1)) < 1e-9:
            parent.setdefault(m, n)
        if n > 1 and abs(L[n - 1] - L[n]) < 1e-12:
            parent.setdefault(n - 1, n)
    children: dict[int, list[int]] = {}
    for m, p in parent.items():
        children.setdefault(p, []).append(m)

    def reach(n: int) -> float:
        total, stack, seen = 0.0, [n], set()
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            total += 1 / math.sqrt(k)
            stack.extend(children.get(k, []))
        return total

    return {n: reach(n) for n in range(2, N_MAX + 1)
            if n not in parent and L[n] < sc.grid_side(n) - 1e-9}


def load_packing(n: int) -> np.ndarray:
    path = BEST / f"n{n:03d}.npz"
    if path.exists():
        d = np.load(path)
        if float(d["L"]) < sc.grid_side(n) - 1e-9:
            return cp.normalize(cp.to_packing(d["xy"], d["th"]))
    xy, th = sc.grid(n)
    return cp.normalize(cp.to_packing(xy, th))


# --------------------------------------------------------------------------
# the batched penalty
# --------------------------------------------------------------------------
def near_pairs(P: torch.Tensor, cut: float) -> torch.Tensor:
    """(K, 2) index pairs i < j that are within `cut` in any start."""
    B, n, _ = P.shape
    mask = torch.zeros(n, n, dtype=torch.bool, device=P.device)
    for b in range(B):
        xy = P[b, :, :2]
        mask |= torch.cdist(xy, xy) < cut
    mask = torch.triu(mask, diagonal=1)
    return mask.nonzero()


def energy(P: torch.Tensor, pairs: torch.Tensor, T: float, size: float) -> torch.Tensor:
    """(B,) penalty for squares of side `size` in the box [0, T]^2."""
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
    rad = 0.5 * size * (1 + torch.cos(dt).abs() + torch.sin(dt).abs())
    e = torch.relu(rad - proj).pow(2).sum(dim=1)
    h = 0.5 * size * (c.abs() + s.abs())
    for v in (x, y):
        e = e + (torch.relu(h - v).pow(2) + torch.relu(v + h - T).pow(2)).sum(dim=1)
    return e


def starts(n: int, base: np.ndarray, batch: int, L0: float, rng,
           jitter: float = 0.02) -> np.ndarray:
    """Jittered copies of the best packing, and n + 1 minus one square."""
    out = []
    bigger = load_packing(n + 1) if n < N_MAX else None
    for b in range(batch):
        if bigger is not None and b % 2 == 1:
            p = np.delete(bigger, rng.integers(n + 1), axis=0)
        else:
            p = base.copy()
        p = cp.normalize(p)
        p[:, :2] *= L0 / max(cp.side(p), 1e-9)
        sigma = jitter * (1 + b % 4)
        p[:, :2] += rng.normal(0, sigma, (n, 2))
        p[:, 2] += rng.normal(0, sigma, n)
        out.append(p)
    return np.stack(out)


def search(n: int, base: np.ndarray, T: float, batch: int, steps: int,
           device: str, dtype, rng, jitter: float = 0.02) -> list[np.ndarray]:
    """Run the continuation once; return near-feasible packings as numpy."""
    L = cp.side(base)
    L0 = max(L, T) * (1 + jitter / 2)
    P = torch.tensor(starts(n, base, batch, L0, rng, jitter), device=device, dtype=dtype,
                     requires_grad=True)
    lr0 = jitter / 2              # move no further per step than the noise
    opt = torch.optim.Adam([P], lr=lr0)
    pairs = near_pairs(P.detach(), 1.9)
    for k in range(steps):
        f = k / steps
        box = L0 + (T - L0) * min(1.0, f / 0.6)
        size = 0.97 + 0.03 * min(1.0, f / 0.7)
        for g in opt.param_groups:
            g["lr"] = lr0 * (1 - f) + lr0 / 100
        if k % 25 == 0:
            pairs = near_pairs(P.detach(), 1.9)
        opt.zero_grad()
        e = energy(P, pairs, box, size).sum()
        e.backward()
        opt.step()

    # Adam stalls near zero; L-BFGS converges the last stretch. It runs in
    # float64, because the squares are inflated by INFLATE so that contacts
    # come out open, and float32 cannot see a gap that small at coordinates
    # near 30. The starts are independent, so minimising their summed penalty
    # minimises each of them.
    P = P.detach().to(torch.float64).requires_grad_(True)
    lbfgs = torch.optim.LBFGS([P], lr=1.0, max_iter=50, history_size=20,
                              line_search_fn="strong_wolfe")
    for _ in range(args_lbfgs_rounds):
        pairs = near_pairs(P.detach(), 1.7)

        def closure():
            lbfgs.zero_grad()
            e = energy(P, pairs, T, 1.0 + INFLATE).sum()
            e.backward()
            return e

        lbfgs.step(closure)
    with torch.no_grad():
        e = energy(P, near_pairs(P, 1.6), T, 1.0)
    keep = (e < 1e-14).nonzero().flatten().tolist()
    return [P[b].detach().cpu().numpy() for b in keep]


def finish(n: int, cands: list[np.ndarray], L: float, seconds: float):
    """Repair and polish each candidate in float64; return the best valid one."""
    best = None
    for p in cands:
        q = cp.repair(p)
        if q is None:
            continue
        q, _ = cp.polish(q, seed=n, max_seconds=seconds)
        ok, info = sc.is_valid(q[:, :2], q[:, 2])
        if ok and info["L"] < L - 1e-9 and (best is None or info["L"] < cp.side(best)):
            best = q
    return best


def run_puzzle(n: int, args, device: str, dtype, out: pathlib.Path) -> dict:
    rng = np.random.default_rng(args.seed + n)
    base = load_packing(n)
    L_start = cp.side(base)
    start = time.time()
    delta = args.delta
    rounds = found = 0
    while time.time() - start < args.minutes * 60 / max(len(args.n_list), 1) and delta > 1e-5:
        L = cp.side(base)
        cands = search(n, base, L - delta, args.batch, args.steps, device, dtype, rng,
                       args.jitter)
        better = finish(n, cands, L, args.polish_seconds) if cands else None
        rounds += 1
        if better is None:
            delta *= 0.5
            continue
        base = better
        found += 1
        np.savez(out / f"n{n:03d}.npz", xy=better[:, :2], th=better[:, 2],
                 L=cp.side(better))
    row = dict(n=n, before=L_start, after=cp.side(base), rounds=rounds, found=found,
               gain=(L_start - cp.side(base)) / math.sqrt(n),
               seconds=round(time.time() - start, 1))
    print(json.dumps(row), flush=True)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, nargs="*", help="puzzles to search")
    ap.add_argument("--auto", type=int, default=0,
                    help="search the top K seeds by how far an improvement lifts")
    ap.add_argument("--auto-min-n", type=int, default=101,
                    help="auto skips smaller n, which decades of work have settled")
    ap.add_argument("--minutes", type=float, default=10.0, help="total budget")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--delta", type=float, default=0.01,
                    help="first target is L - delta; halves on each failure")
    ap.add_argument("--jitter", type=float, default=0.02,
                    help="start noise; small to refine a layout, large to escape it")
    ap.add_argument("--polish-seconds", type=float, default=10.0)
    ap.add_argument("--float64", action="store_true", help="slower, for A100")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="found")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float64 if args.float64 else torch.float32
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    ns = list(args.n or [])
    if args.auto:
        w = {n: v for n, v in seed_weights(best_sides()).items() if n >= args.auto_min_n}
        ns += [n for n, _ in sorted(w.items(), key=lambda kv: -kv[1])[: args.auto]]
    args.n_list = ns
    print(f"device {device}, {dtype}, puzzles {ns}", flush=True)
    rows = [run_puzzle(n, args, device, dtype, out) for n in ns]
    gain = sum(r["gain"] for r in rows)
    print(f"total gain before lifting {gain:.6f} over {sum(r['found'] > 0 for r in rows)} puzzles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
