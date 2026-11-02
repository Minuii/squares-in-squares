"""
make_figures.py -- regenerate the figures used by README.md.

    python notebooks/make_figures.py

Writes into figures/.  The visual notebook builds the same pictures itself
(it embeds viz.py), so the two never disagree.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import squares_core as sc
import viz

OUT = Path("figures")
OUT.mkdir(exist_ok=True)


def note(xy, th, tag=""):
    L = viz.side(xy, th)
    s = viz.score(L, len(xy))
    return f"L = {L:.4f}   score {s:.4f}{tag}"


def main() -> None:
    # ---------------------------------------------------------------- n = 5
    # the search result from the other notebook, recomputed here
    r = sc.shrink(5, rounds=45, iters=350, seed=7)
    xy_s, th_s = sc.polish(r["xy"], r["th"], np.random.default_rng(0))

    gxy, gth = viz.grid(5)
    oxy, oth = viz.optimal5()

    viz.figure_n5([
        {"xy": gxy, "th": gth, "label": "trivial grid",
         "note": note(gxy, gth), "waste": True},
        {"xy": xy_s, "th": th_s, "label": "shrink-wrap search",
         "note": note(xy_s, th_s), "waste": True},
        {"xy": oxy, "th": oth, "label": "optimal (proved, 1979)",
         "note": note(oxy, oth), "waste": True},
    ], OUT / "n5-three-ways.png")
    print("n5: grid %.4f  search %.4f  optimal %.4f"
          % (viz.side(gxy, gth), viz.side(xy_s, th_s), viz.side(oxy, oth)))

    # ------------------------------------------------------- gallery n=1..12
    items = []
    for n in range(1, 13):
        xy, th = viz.grid(n)
        items.append({"xy": xy, "th": th, "label": f"n = {n}",
                      "note": note(xy, th)})
    viz.figure_gallery(items, OUT / "gallery.png", cols=4)
    print("gallery: 12 panels")

    # --------------------------------------------------- perfect squares
    items = []
    for k in (2, 3, 4):
        xy, th = viz.grid(k * k)
        items.append({"xy": xy, "th": th, "label": f"n = {k*k} = {k}x{k}",
                      "note": note(xy, th)})
    viz.figure_n5(items, OUT / "perfect-squares.png")
    print("perfect squares: n = 4, 9, 16")

    # ------------------------------------------- n = k^2 - 1 and k^2 - 2
    xy7, th7 = viz.mutilated(3, holes=((0, 0), (2, 2)))
    xy8, th8 = viz.mutilated(3, holes=((2, 2),))
    viz.figure_n5([
        {"xy": xy7, "th": th7, "label": "n = 7 = 3^2 - 2",
         "note": note(xy7, th7) + "  (provably optimal)", "waste": True},
        {"xy": xy8, "th": th8, "label": "n = 8 = 3^2 - 1",
         "note": note(xy8, th8) + "  (provably optimal)", "waste": True},
    ], OUT / "k2-minus.png")
    print("k^2-2 / k^2-1: L = %.4f, %.4f" % (viz.side(xy7, th7), viz.side(xy8, th8)))

    # ------------------------------------------------------------ L vs n
    ns = list(range(1, 121))
    L_grid = [viz.side(*viz.grid(n)) for n in ns]
    L_bound = [math.sqrt(n) for n in ns]
    known = {1: 1.0, 2: 2.0, 3: 2.0, 4: 2.0, 5: 2 + 0.5 ** 0.5, 6: 3.0, 7: 3.0,
             8: 3.0, 9: 3.0, 10: 3 + 0.5 ** 0.5, 11: 3.87708359, 12: 4.0,
             13: 4.0, 14: 4.0, 15: 4.0, 16: 4.0, 17: 4.67553009,
             18: 4.822875655, 19: 4.885618083, 20: 5.0}
    viz.plot_L_vs_n(ns, L_grid, L_bound, known, OUT / "L-vs-n.png")
    print("L vs n: 1..120")


if __name__ == "__main__":
    main()
