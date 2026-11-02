"""atlas_families.py -- label every record in best/ by layout, and flag weak ones.

EXPERIMENTAL. The Living Atlas makes the records look like several families
(diamonds, straight strips, bent bands). This puts numbers on that view.

    tilt        each square's angle folded into (-45, 45] degrees; |tilt| > 0.5
                counts as tilted
    blocks      tilted squares joined when their centres are within 1.6, kept
                if a component has 4 or more squares
    family      grid       no tilted squares
                diamond    most tilted squares near 45 degrees (Goebel)
                strip      one block
                pinwheel   two blocks of opposite tilt
                multi      anything else
    weak        excess e(n) = L - sqrt(n), compared with the median excess of
                the non-grid records among n-2 .. n+2 in the same band
                k^2 < n <= (k+1)^2; a large positive residual is a record that
                sits above its neighbours

    python experiments/atlas_families.py                # summary + 25 weakest
    python experiments/atlas_families.py --top 50 --csv scratch/families.csv
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys
from collections import Counter

import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from lift_packings import load_all

N_MAX = 1000


def classify(xy: np.ndarray, th: np.ndarray) -> dict:
    tilt = np.degrees((th + math.pi / 4) % (math.pi / 2) - math.pi / 4)
    m = np.abs(tilt) > 0.5
    out = {"tilted": int(m.sum()), "blocks": 0, "angles": ""}
    if not m.any():
        return {**out, "family": "grid"}
    t, p = tilt[m], xy[m]
    if np.mean(np.abs(np.abs(t) - 45) < 3) > 0.5:
        return {**out, "family": "diamond", "angles": "45"}
    pairs = cKDTree(p).query_pairs(1.6, output_type="ndarray")
    g = np.zeros((len(p), len(p)), bool)
    if len(pairs):
        g[pairs[:, 0], pairs[:, 1]] = True
    _, lab = connected_components(g, directed=False)
    sizes = Counter(lab)
    big = [c for c, s in sizes.items() if s >= 4]
    med = [float(np.median(t[lab == c])) for c in big]
    out.update(blocks=len(big), angles=" ".join(f"{a:+.1f}" for a in sorted(med)))
    if len(big) == 1:
        fam = "strip"
    elif len(big) == 2 and med[0] * med[1] < 0:
        fam = "pinwheel"
    else:
        fam = "multi"
    return {**out, "family": fam}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--csv")
    a = ap.parse_args()

    pack = load_all()
    rows = {n: {"n": n, "L": L, **classify(xy, th)} for n, (xy, th, L) in pack.items()}
    e = {n: r["L"] - math.sqrt(n) for n, r in rows.items()}
    band = {n: math.isqrt(n - 1) for n in rows}  # k with k^2 < n <= (k+1)^2
    for n, r in rows.items():
        nb = [e[m] for m in range(n - 2, n + 3)
              if m != n and m in e and band[m] == band[n] and rows[m]["family"] != "grid"]
        r["resid"] = e[n] - float(np.median(nb)) if len(nb) >= 2 else 0.0

    print("family counts by n range")
    for lo in range(1, N_MAX, 100):
        c = Counter(rows[n]["family"] for n in range(lo, min(lo + 100, N_MAX + 1)))
        print(f"  {lo:4d}-{lo + 99:4d}  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))

    print(f"\n{a.top} records furthest above their neighbours (not grid)")
    print("    n         L   resid  family    blocks  angles          neighbours")
    weak = sorted((r for r in rows.values() if r["family"] != "grid"), key=lambda r: -r["resid"])
    for r in weak[: a.top]:
        n = r["n"]
        nb = " ".join(rows[m]["family"][:4] for m in (n - 1, n + 1) if m in rows)
        print(f"  {n:3d}  {r['L']:9.5f}  {r['resid']:+.4f}  {r['family']:<8}  {r['blocks']:6d}"
              f"  {r['angles']:<14}  {nb}")

    if a.csv:
        keys = ["n", "L", "resid", "family", "tilted", "blocks", "angles"]
        with open(a.csv, "w") as f:
            f.write(",".join(keys) + "\n")
            for n in sorted(rows):
                f.write(",".join(str(rows[n][k]) for k in keys) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
