"""probe_sa.py -- can sa_feasible reach a target L that is known to be feasible?

n=19 has a published packing at L=4.88561808 (it is in best/n019.npz), and
n=30 sits just above the locked band. If the annealer cannot find a packing we
know exists -- and can warm-start from -- then no amount of parameter tuning
will carry the search into blocks 19-31, and the next phase has to be
constructive rather than stochastic.
"""
import time

import numpy as np

import squares_core as sc


def attempt(n: int, target: float, iters: int, seed: int):
    d = np.load(f"best/n{n:03d}.npz")
    xy, th = d["xy"], d["th"]
    L0 = sc.container_side(xy, th)
    # squash the known-good packing into the smaller window, then anneal
    s = min(target / L0, 1.0)
    c = xy.mean(axis=0)
    xy0 = c + (xy - c) * s
    t0 = time.time()
    e, x1, t1 = sc.sa_feasible(n, target, iters=iters,
                               rng=np.random.default_rng(seed),
                               init=(xy0, th))
    dt = time.time() - t0
    pen = sc.max_penetration(x1, t1)
    ok = e <= 1e-14 and pen <= sc.TOL
    print(f"  n={n:3d} target={target:.6f}  energy={e:.3e}  pen={pen:+.2e}  "
          f"{'FEASIBLE' if ok else 'failed':>9}  ({dt:.1f}s)")
    return ok


def main() -> int:
    print("warm-start from the published packing, squash into the target window")
    for seed in (0, 1):
        for target in (4.90, 4.886, 4.878):
            attempt(19, target, 60000, seed)
    print()
    print("n=30 at the grid boundary (k=6, j=6)")
    for target in (5.99, 5.97):
        attempt(30, target, 60000, 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
