"""
build_visual_notebook.py -- generate `visual_tour.ipynb`.

A picture-first companion to `packing_unit_squares.ipynb`: it draws the
packings, overlays the numbers, and walks through the four things worth seeing
(gallery, perfect squares, n = 5, the k^2-1 / k^2-2 family) plus the L(n) chart.

The drawing code lives in viz.py and is embedded verbatim, so the notebook is
self-contained.  Every cell is executed here and its real output is embedded.

Usage:  python build_visual_notebook.py
"""

from __future__ import annotations

import base64
import io
import json
import re
import sys
import traceback
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
VIZ = (ROOT / "viz.py").read_text(encoding="utf-8")
OUT = ROOT / "visual_tour.ipynb"

BANNER = re.compile(r"# -{20,}\n# (.+?)\n# -{20,}\n")


def split_sections(text: str) -> list[tuple[str, str]]:
    text = re.sub(r'\A\s*""".*?"""\s*', "", text, flags=re.S)
    text = text.replace("from __future__ import annotations\n", "")
    # drop the demo block at the bottom of viz.py
    text = text.split('if __name__ == "__main__":')[0]

    hits = list(BANNER.finditer(text))
    out = [("setup", text[: hits[0].start()])]
    for k, m in enumerate(hits):
        end = hits[k + 1].start() if k + 1 < len(hits) else len(text)
        out.append((m.group(1), text[m.end(): end]))
    return out


CELLS: list[tuple[str, str]] = []


def md(src: str) -> None:
    CELLS.append(("markdown", src.strip("\n")))


def code(src: str) -> None:
    CELLS.append(("code", src.strip("\n")))


# ==========================================================================
md(
    r"""
# A visual tour of square packing

### What the pictures say that the formulas don't

The companion notebook (`packing_unit_squares.ipynb`) does the mathematics.
This one is about **seeing** it. Every figure below is drawn from real
coordinates and recomputed as you run the cells — nothing is a stock image, and
the numbers printed under each panel are measured from the drawing itself.

Four things are worth looking at:

1. **The grid staircase** — why the container grows in sudden steps of one.
2. **Perfect squares** — the only packings that fill their box exactly.
3. **n = 5** — the smallest case where tilting wins, and by how much.
4. **n = k² − 1 and k² − 2** — the "mutilated chessboard": knock one or two
   cells out of a grid and you never need a bigger box.

Colours are only there to separate squares from each other. Grey is empty
container — the waste you are paying for.
"""
)

md(
    r"""
## 0. The drawing code

Pillow only, no matplotlib (so it runs on a bare Kaggle kernel). `render()`
draws a list of packings **at one common scale** — that is the whole point:
a packing with $L = 2.707$ must look visibly smaller than one with $L = 3.000$,
otherwise the picture is decorative rather than informative.

You can skip these cells; the tour starts below.
"""
)

for title, body in split_sections(VIZ):
    label = {
        "setup": "Imports",
        "geometry (kept local so this file stands alone)":
            "Geometry: corners, container side, score",
        "specific packings worth looking at":
            "Packings worth looking at (grid, the n=5 optimum, mutilated grids)",
        "drawing": "Drawing",
    }.get(title, title)
    md(f"#### {label}")
    code(body)

code(
    r'''
# Display a PNG inline (rather than as a separate file to open).
def show_png(path):
    from IPython.display import Image, display
    display(Image(filename=path))
'''
)

md(
    r"""
## 1. A gallery, n = 1 … 12

Every packing here is the **trivial grid**: lay the squares out in a
$\lceil\sqrt n\rceil \times \lceil\sqrt n\rceil$ block and shrink-wrap.

Watch the container instead of the squares. It stays at 2 for $n=2,3,4$, jumps
to 3 for $n=5\ldots9$, jumps to 4 at $n=10$. The jump happens one puzzle *after*
the grid fills up, and that jump is the expensive part of this competition.

Also note the grey: at $n=5$ you are paying for nine cells and using five.
"""
)

code(
    r"""
from pathlib import Path
Path("figures").mkdir(exist_ok=True)

items = []
for n in range(1, 13):
    xy, th = grid(n)
    L = side(xy, th)
    items.append({"xy": xy, "th": th, "label": f"n = {n}",
                  "note": f"L = {L:.4f}   score {score(L, n):.4f}"})
show_png(render(items, "figures/gallery.png", cols=4, cell=(250, 280), margin=18))
"""
)

md(
    r"""
## 2. Perfect squares: the only packings that fill the box

$n = 4, 9, 16$: the grid *is* the optimum, the container is exactly
$\sqrt n \times \sqrt n$, and the score is **exactly 0**.

There is no grey in these panels, and there cannot be: $n$ unit squares have
area $n$, a square of side $\sqrt n$ has area $n$, so a packing with
$L=\sqrt n$ uses every bit of the box. Any packing with a visible gap has
$L > \sqrt n$ and a positive score.

Since only 31 of the first 1000 values of $n$ are perfect squares, only 31
puzzles can ever score exactly 0 — those are the `1.000000000000000` entries
people post.
"""
)

code(
    r"""
items = []
for k in (2, 3, 4):
    xy, th = grid(k * k)
    L = side(xy, th)
    items.append({"xy": xy, "th": th, "label": f"n = {k*k} = {k} x {k}",
                  "note": f"L = {L:.4f}   score {score(L, k*k):.4f}"})
show_png(render(items, "figures/perfect-squares.png", cols=3, cell=(380, 430)))
"""
)

md(
    r"""
## 3. n = 5: the smallest puzzle where tilting wins

This is the first genuinely interesting case, and the one where human intuition
beats every naive search.

### The optimal packing

Four unit squares sit in the four corners of the container. The fifth is
rotated by $45^\circ$ and dropped in the middle. Each corner square touches the
central diamond at **exactly one point** — its inner corner lands on an edge of
the diamond — and that tangency is what fixes the container size:

$$L = 2 + \frac{\sqrt 2}{2} = 2.7071\ldots$$

Read the construction off the picture: if the four corner squares are unit
squares in the corners of an $L \times L$ box, the middle gap has width
$L - 2$ on each side. A unit square rotated by $45^\circ$ has axis-aligned
extent $\sqrt 2$, and its diamond shape lets its four vertices poke into the
four gaps.
The gap closes when $L - 2 = \sqrt2/2$, i.e. $L = 2 + \sqrt2/2$. Göbel proved in
1979 that nothing does better.

### Why the search stops short

The middle panel is what the shrink-wrap optimiser in the companion notebook
actually produces. It finds the *right idea* — it rotates a square and buries it
in the middle — but it cannot land on the exact tangency, so it pays about 3%
extra in $L$ and loses $0.035$ of score.
"""
)

code(
    # the search result is baked in at build time so the notebook needs nothing
    # but viz.py
    r"""
# Four corner squares + one diamond. L = 2 + sqrt(2)/2.
GRID5, GRID5_TH = grid(5)
OPT5, OPT5_TH = optimal5()

# a few % worse than optimal, but the right topology -- found by the
# shrink-wrap search in packing_unit_squares.ipynb
SEARCH5 = np.array(SEARCH5_XY)
SEARCH5_TH = np.array(SEARCH5_TH)

print(f"grid      L = {side(GRID5, GRID5_TH):.6f}   score {score(side(GRID5, GRID5_TH), 5):.6f}")
print(f"search    L = {side(SEARCH5, SEARCH5_TH):.6f}   score {score(side(SEARCH5, SEARCH5_TH), 5):.6f}")
print(f"optimal   L = {side(OPT5, OPT5_TH):.6f}   score {score(side(OPT5, OPT5_TH), 5):.6f}")
print(f"area bound  sqrt(5) = {np.sqrt(5):.6f}   (unreachable: 5 is not a perfect square)")

panels = [
    {"xy": GRID5, "th": GRID5_TH, "label": "trivial grid",
     "note": f"L = 3.0000   score {score(3.0, 5):.4f}", "waste": True},
    {"xy": SEARCH5, "th": SEARCH5_TH, "label": "shrink-wrap search",
     "note": f"L = {side(SEARCH5, SEARCH5_TH):.4f}   score {score(side(SEARCH5, SEARCH5_TH), 5):.4f}",
     "waste": True},
    {"xy": OPT5, "th": OPT5_TH, "label": "optimal (Gobel, 1979)",
     "note": f"L = {side(OPT5, OPT5_TH):.4f}   score {score(side(OPT5, OPT5_TH), 5):.4f}",
     "waste": True},
]
show_png(render(panels, "figures/n5-three-ways.png", cols=3, cell=(380, 430)))
"""
)

md(
    r"""
### Check the tangency yourself

The claim "each corner square touches the diamond at exactly one point" is easy
to verify analytically. The inner corner of the bottom-left square is at
$(1,1)$; the diamond's lower-left edge runs along $x + y = 2$. That line passes
through $(1,1)$ exactly, and the square sits in $x + y \le 2$ — so the only
contact is the single point $(1,1)$. Repeat for the other three corners and the
packing is proved legal.

The cell below measures it instead. Note the subtlety it has to get right: the
closest approach between two squares is a **point-to-edge** distance, not
vertex-to-vertex — the tangency point here lies in the *interior* of the
diamond's edge, so a naive corner-to-corner computation reports $0.5$ and misses
the contact entirely.
"""
)

code(
    r"""
def _pt_seg(p, a, b):
    # distance from point p to the segment a-b
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0.0, 1.0)
    return np.linalg.norm(p - (a + t * ab))


def poly_distance(A, B):
    # For convex polygons the closest pair is always vertex-to-edge, so
    # minimising the 8 vertices against the 4 edges of the other body is exact.
    best = np.inf
    for i in range(4):
        for j in range(4):
            best = min(best, _pt_seg(A[i], B[j], B[(j + 1) % 4]))
            best = min(best, _pt_seg(B[i], A[j], A[(j + 1) % 4]))
    return best


def gaps(xy, th):
    # Distance from each square to its nearest neighbour: 0 = touching.
    # A legal packing never goes negative.
    p = corners(xy, th)
    n = len(xy)
    out = []
    for i in range(n):
        best = np.inf
        for j in range(n):
            if i != j:
                best = min(best, poly_distance(p[i], p[j]))
        out.append(best)
    return np.array(out)


print("distance from each square to its nearest neighbour (0 = in contact)")
g_opt = gaps(OPT5, OPT5_TH)
g_grid = gaps(GRID5, GRID5_TH)
g_search = gaps(SEARCH5, SEARCH5_TH)
for name, g in [("optimal n=5", g_opt), ("grid    n=5", g_grid),
                ("search  n=5", g_search)]:
    print(f"  {name} : {np.round(np.maximum(g, 0), 6)}")

print()
print(f"optimal: largest slack {g_opt.max():.2e}  -> every square is in contact.")
print(f"search : largest slack {g_search.max():.2e}  -> {np.sum(g_search > 1e-4)} of 5 "
      "squares still float free.")
print()
print("That slack is the 2.8% of L the search pays. A rigid packing has no slack")
print("to spend: every degree of freedom is pinned by a contact, so the contacts")
print("themselves determine L. Finding *which* contacts to force is the hard part.")
"""
)

md(
    r"""
## 4. The $n = k^2-1$ and $k^2-2$ families

Take a $3\times3$ grid and knock out one or two cells. The bounding box does not
grow — it is still $3 \times 3$ — so $n=8$ and $n=7$ pack into a container of
side 3, exactly like $n=9$ does.

This is not a curiosity, it is a theorem: $s(k^2) = s(k^2-1) = s(k^2-2) = k$.
For $n \le 1000$ that settles $31 + 30 + 30 = 91$ puzzles — they are already at
their optimum, and no amount of search can improve them.

The grey holes in these pictures are *allowed*: you are not required to fill the
container, only to fit inside it.
"""
)

code(
    r"""
xy7, th7 = mutilated(3, holes=((0, 0), (2, 2)))
xy8, th8 = mutilated(3, holes=((2, 2),))
xy9, th9 = grid(9)

panels = []
for xy, th, lab in [(xy7, th7, "n = 7 = 3^2 - 2"),
                    (xy8, th8, "n = 8 = 3^2 - 1"),
                    (xy9, th9, "n = 9 = 3^2")]:
    L = side(xy, th)
    panels.append({"xy": xy, "th": th, "label": lab,
                   "note": f"L = {L:.4f}   score {score(L, len(xy)):.4f}",
                   "waste": True})
show_png(render(panels, "figures/k2-minus.png", cols=3, cell=(380, 430)))
"""
)

md(
    r"""
## 5. The container side as a function of $n$

Same information as the gallery, all at once.

* **Black** is $\sqrt n$ — the area bound, unattainable except at perfect
  squares.
* **Blue** is the trivial grid: a staircase that touches the black curve at
  $n = 1,4,9,16,\ldots$ and jumps one level right after each of them.
* **Red** is the best packing anybody has published, for $n \le 20$. It ducks
  under the staircase but stays above the bound.

The vertical gap between blue and black is the score you are paying. For $n$
just above a perfect square that gap is $\approx 1$, i.e. a full unit of
container; for $n$ just below one it is almost nothing. That asymmetry is why
"$n = k^2+1$" puzzles are where the leaderboard is won.
"""
)

code(
    r"""
ns = list(range(1, 121))
L_grid = [side(*grid(n)) for n in ns]
L_bound = [np.sqrt(n) for n in ns]

KNOWN = {1: 1.0, 2: 2.0, 3: 2.0, 4: 2.0, 5: 2 + 0.5 ** 0.5, 6: 3.0, 7: 3.0,
         8: 3.0, 9: 3.0, 10: 3 + 0.5 ** 0.5, 11: 3.87708359, 12: 4.0,
         13: 4.0, 14: 4.0, 15: 4.0, 16: 4.0, 17: 4.67553009,
         18: 4.822875655, 19: 4.885618083, 20: 5.0}

show_png(plot_L_vs_n(ns, L_grid, L_bound, KNOWN, "figures/L-vs-n.png"))
"""
)

md(
    r"""
## 6. Draw your own

Drop in any list of centres and angles. This is the quickest way to sanity-check
a submission visually before you upload it — an overlap that is invisible in a
CSV is obvious in a picture.

```python
panels = [{"xy": my_xy, "th": my_th, "label": "n = 37, mine",
           "note": f"L = {side(my_xy, my_th):.4f}"}]
show_png(render(panels, "figures/mine.png"))
```
"""
)

code(
    r"""
# a deliberately silly example: the same 3x3 grid rotated by 20 degrees.
# It no longer fits in 3x3 -- the corners stick out -- so L grows.
a = np.deg2rad(20)
c, s = np.cos(a), np.sin(a)
R = np.array([[c, -s], [s, c]])
base, _ = grid(9)
spun = (base - 1.5) @ R.T + 1.5

panels = [
    {"xy": base, "th": np.zeros(9), "label": "n = 9, axis-aligned",
     "note": f"L = {side(base, np.zeros(9)):.4f}", "waste": True},
    {"xy": spun, "th": np.full(9, a), "label": "n = 9, rotated 20 deg",
     "note": f"L = {side(spun, np.full(9, a)):.4f}  <- same squares, bigger box",
     "waste": True},
]
show_png(render(panels, "figures/rotated.png", cols=2, cell=(380, 430)))
print("rotating a block that already fills its box only makes the box bigger:")
print(f"  axis-aligned L = {side(base, np.zeros(9)):.6f}")
print(f"  rotated 20d  L = {side(spun, np.full(9, a)):.6f}")
"""
)

md(
    r"""
That last pair is a useful warning. Rotation is not free: it lets a square reach
into a gap, but it also sweeps out a bigger bounding box ($\sqrt2$ instead of
$1$ at $45^\circ$). Every tilted packing in the record tables is a *negotiated*
improvement — the tilt buys space in one direction and pays for it in another.
That is what makes the optimisation non-obvious, and it is why the search in the
companion notebook stalls where it does.
"""
)

md(
    r"""
## Where to go next

* **The mathematics** — `packing_unit_squares.ipynb` proves that score $=0$ if and
  only if $n$ is a perfect square, tabulates what is known for $n\le20$, and
  builds the validator, the optimiser and the submission writer.
* **The frontier** — [squaremath.org](https://squaremath.org/frontier.html)
  publishes the best known packing and best lower bound for every $n$, with
  attribution.
* **The written version** — `README.md` in this folder is the same story in
  prose, with these figures embedded.
"""
)


# --------------------------------------------------------------------------
def install_shim(captured: list[str]) -> None:
    ip = types.ModuleType("IPython")
    disp = types.ModuleType("IPython.display")

    class _Image:
        def __init__(self, filename=None, data=None, **kw):
            self.filename = filename

    def _display(obj):
        if isinstance(obj, _Image) and obj.filename:
            captured.append(obj.filename)

    disp.Image = _Image
    disp.display = _display
    ip.display = disp
    sys.modules["IPython"] = ip
    sys.modules["IPython.display"] = disp


def main() -> int:
    # compute the search result once, so the cell can carry it as data
    import squares_core as sc

    r = sc.shrink(5, rounds=45, iters=350, seed=7)
    xy_s, th_s = sc.polish(r["xy"], r["th"], np.random.default_rng(0))
    xy_s = xy_s - sc.corners(xy_s, th_s).reshape(-1, 2).min(axis=0)

    # inject the literal before the cell that uses it
    for i, (kind, src) in enumerate(CELLS):
        if kind == "code" and "SEARCH5 = np.array(SEARCH5_XY)" in src:
            lit = (
                "SEARCH5_XY = %r\n"
                "SEARCH5_TH = %r\n"
                % (np.round(xy_s, 12).tolist(), np.round(th_s, 12).tolist())
            )
            CELLS[i] = ("code", lit + "\n" + src)
            break
    else:
        raise SystemExit("could not find the SEARCH5 cell")

    captured: list[str] = []
    install_shim(captured)
    G: dict = {"__name__": "__main__"}
    cells, count, failures = [], 0, 0

    for idx, (kind, src) in enumerate(CELLS):
        if kind == "markdown":
            cells.append({"cell_type": "markdown", "id": f"cell-{idx:03d}",
                          "metadata": {}, "source": src.splitlines(keepends=True)})
            continue

        buf = io.StringIO()
        count += 1
        captured.clear()
        err = None
        try:
            with redirect_stdout(buf):
                exec(compile(src, f"<cell {idx}>", "exec"), G)
        except Exception:
            err = traceback.format_exc()
            failures += 1
            print(f"!! cell {idx} failed\n{err}", file=sys.stderr)

        outs = []
        if buf.getvalue():
            outs.append({"output_type": "stream", "name": "stdout",
                         "text": buf.getvalue().splitlines(keepends=True)})
        for fig in captured:
            p = ROOT / fig
            if p.exists():
                outs.append({"output_type": "display_data",
                             "data": {"image/png":
                                      base64.b64encode(p.read_bytes()).decode("ascii"),
                                      "text/plain": [f"<Figure {fig}>"]},
                             "metadata": {}})
        if err:
            outs.append({"output_type": "stream", "name": "stderr",
                         "text": err.splitlines(keepends=True)})
        cells.append({"cell_type": "code", "id": f"cell-{idx:03d}",
                      "metadata": {}, "execution_count": count,
                      "outputs": outs, "source": src.splitlines(keepends=True)})

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.12",
                              "mimetype": "text/x-python",
                              "file_extension": ".py"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }
    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({len(cells)} cells, {count} code)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
