"""probe_locked.py -- test the 'k^2 - j is locked for j <= k' hypothesis.

For block k, the grid side is k. Write j = k^2 - n. The claim to test:
the shrink-wrap optimiser can beat k only once j > k, i.e. only in the
*lower* half of each block. If that holds, the 349 "untouched" puzzles
(which all sit at j <= k) are not claimable and Phase 3b is a dead end.
"""
import time
import numpy as np
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import squares_core as sc

def probe(k, js, rounds=30, iters=250, seed=0):
    print(f"\nblock k={k}  (grid L={k})")
    print(f"{'n':>5} {'j':>4} {'grid':>5} {'found L':>10} {'beats grid?':>12} {'score':>9} {'secs':>6}")
    for j in js:
        n = k * k - j
        if n < 1:
            continue
        t0 = time.time()
        r = sc.shrink(n, rounds=rounds, iters=iters, seed=seed, eta=0.004)
        dt = time.time() - t0
        beat = r["L"] < k - 1e-9
        print(f"{n:>5} {j:>4} {k:>5} {r['L']:>10.6f} {str(beat):>12} "
              f"{r['score']:>9.6f} {dt:>6.1f}")
    return

if __name__ == "__main__":
    for k, js in ((5, [2, 4, 5, 6, 7]),
                  (8, [4, 7, 8, 9, 10, 12]),
                  (10, [5, 9, 10, 11, 13])):
        probe(k, js)
