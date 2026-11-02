"""polish_best.py -- try to shrink every non-grid packing in best/ with the
contact LP polisher, keeping only strict improvements.

    python src/polish_best.py --seconds 20

Grid packings are skipped: the polisher cannot beat them this way. Workers
only compute; the parent validates and is the only process that writes files.
"""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import pathlib

import numpy as np

import contact_polish
import squares_core as sc


def work(job: tuple[int, float]):
    """Polish one puzzle: return (n, xy, th), or (n, None, error)."""
    n, seconds = job
    try:
        d = np.load(f"best/n{n:03d}.npz")
        p = contact_polish.to_packing(d["xy"], d["th"])
        q, _ = contact_polish.polish(p, seed=n, max_seconds=seconds)
        return n, q[:, :2], q[:, 2]
    except Exception as exc:                    # one puzzle must not stop the run
        return n, None, repr(exc)


def candidates() -> dict[int, float]:
    """n -> stored L, for the packings that already beat the grid side."""
    out = {}
    for f in sorted(pathlib.Path("best").glob("n*.npz")):
        n = int(f.stem[1:])
        if 2 <= n <= 1000:
            side = float(np.load(f)["L"])
            if side < sc.grid_side(n) - 1e-12:
                out[n] = side
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0)
    args = ap.parse_args()

    old = candidates()
    jobs = [(n, args.seconds) for n in sorted(old)]
    print(f"{len(jobs)} puzzles below the grid", flush=True)

    improved, gain = [], 0.0
    with mp.Pool(7) as pool:
        for n, xy, th in pool.imap_unordered(work, jobs, chunksize=1):
            if xy is None:
                print(f"n={n:4d}  failed: {th}", flush=True)
                continue
            ok, info = sc.is_valid(xy, th)
            if not ok:
                print(f"n={n:4d}  invalid {info['max_penetration']:.1e}", flush=True)
                continue
            if sc.store_best(n, xy, th):
                improved.append(n)
                gain += (old[n] - info["L"]) / math.sqrt(n)
                print(f"n={n:4d}  {old[n]:.10f} -> {info['L']:.10f}", flush=True)

    improved.sort()
    print(f"\nimproved {len(improved)} puzzles   gain {gain:+.10f}")
    print(f"n = {improved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
