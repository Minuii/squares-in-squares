"""import_found.py -- bring packings found by gpu_search.py into best/.

Each nNNN.npz is checked for size and overlap and stored only if it beats
best/. Afterwards run make_submission.py, which lifts the new seeds, gates
everything with grader_check and writes the submission.

    python experiments/import_found.py found/
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import squares_core as sc


def main() -> int:
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "found")
    stored = rejected = 0
    for path in sorted(src.glob("n*.npz")):
        n = int(path.stem[1:])
        d = np.load(path)
        xy, th = d["xy"], d["th"]
        ok, info = sc.is_valid(xy, th)
        if len(xy) != n or not ok:
            rejected += 1
            print(f"  rejected {path.name}: n={len(xy)} pen={info['max_penetration']:.1e}")
            continue
        if sc.store_best(n, xy, th):
            stored += 1
            print(f"  n={n}: stored L={info['L']:.9f}")
    print(f"stored {stored}, rejected {rejected}; now run make_submission.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
