"""
viz.py -- drawing utilities for packings of unit squares.

Deliberately dependency-light: NumPy + Pillow only, so it runs anywhere the
rest of this folder runs (no matplotlib needed).

Everything is drawn to the *same* scale inside a figure, because the whole
point of these pictures is comparing sizes: a packing at L = 2.707 must look
visibly smaller than one at L = 3.000.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# geometry (kept local so this file stands alone)
# --------------------------------------------------------------------------
SQ = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]  # not used, see below
_HALF = np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])


def corners(xy, th):
    """(n, 4, 2) corners of n unit squares centred at xy, rotated by th."""
    xy = np.asarray(xy, dtype=float)
    th = np.asarray(th, dtype=float)
    c, s = np.cos(th), np.sin(th)
    x = xy[:, 0:1] + c[:, None] * _HALF[:, 0] - s[:, None] * _HALF[:, 1]
    y = xy[:, 1:2] + s[:, None] * _HALF[:, 0] + c[:, None] * _HALF[:, 1]
    return np.stack([x, y], axis=-1)


def side(xy, th):
    """Side of the tightest axis-aligned square around the packing."""
    p = corners(xy, th).reshape(-1, 2)
    return float(max(np.ptp(p[:, 0]), np.ptp(p[:, 1])))


def score(L, n):
    return L / math.sqrt(n) - 1.0


# --------------------------------------------------------------------------
# specific packings worth looking at
# --------------------------------------------------------------------------
def grid(n):
    """The trivial packing: ceil(sqrt n) x ceil(sqrt n)."""
    k = int(math.ceil(math.sqrt(n) - 1e-12))
    idx = np.arange(n)
    xy = np.stack([idx % k + 0.5, idx // k + 0.5], axis=-1).astype(float)
    return xy, np.zeros(n)


def optimal5():
    """The proved-optimal packing of 5 unit squares, L = 2 + sqrt(2)/2.

    Four unit squares sit in the four corners of the container; the fifth is
    rotated by 45 degrees and fills the middle.  Each corner square touches the
    central diamond at exactly one point -- its inner corner lands on an edge
    of the diamond -- which is why the gap is sqrt(2)/2 and not more.
    """
    L = 2.0 + 0.5 ** 0.5
    xy = np.array(
        [[0.5, 0.5], [L - 0.5, 0.5], [0.5, L - 0.5], [L - 0.5, L - 0.5],
         [L / 2.0, L / 2.0]]
    )
    th = np.array([0.0, 0.0, 0.0, 0.0, math.pi / 4.0])
    return xy, th


def mutilated(k=3, holes=()):
    """The k x k grid with some cells removed: the n = k^2 - |holes| family.

    Removing a cell never increases the bounding box, so these pack into a
    k x k square -- and for |holes| <= 2 that is provably optimal.
    """
    cells = [(i, j) for i in range(k) for j in range(k) if (i, j) not in holes]
    xy = np.array([[i + 0.5, j + 0.5] for i, j in cells], dtype=float)
    return xy, np.zeros(len(cells))


def rotated_block(k=2, angle=0.0):
    """A k x k grid of unit squares, the whole block rotated by `angle`."""
    xy, th = grid(k * k)
    xy = xy - (k / 2.0)
    c, s = math.cos(angle), math.sin(angle)
    R = np.array([[c, -s], [s, c]])
    return xy @ R.T + (k / 2.0), np.full(k * k, angle)


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------
PALETTE = [
    (219, 68, 55), (66, 133, 244), (244, 180, 0), (15, 157, 88),
    (171, 71, 188), (0, 172, 193), (255, 112, 67), (124, 179, 66),
]
INK = (32, 33, 36)
GREY = (120, 122, 128)
LIGHT = (214, 216, 220)


def _font(size, bold=False):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                       # Pillow < 10
        return ImageFont.load_default()


def render(panels, path, cols=None, cell=(330, 372), margin=24,
           background=(255, 255, 255)):
    """Draw several packings side by side at a common scale.

    `panels` is a list of dicts: xy, th, label (str), note (str, optional),
    and optionally `waste` (bool) to shade the unused part of the container.
    """
    panels = list(panels)
    cols = cols or len(panels)
    rows = int(math.ceil(len(panels) / cols))
    maxL = max(side(p["xy"], p["th"]) for p in panels)

    # one scale for every panel: that is the whole point of the figure
    s = (cell[0] - 2 * margin) / maxL
    row_h = margin + 6 + maxL * s + 46 + margin

    W, H = cols * cell[0], int(rows * row_h)
    img = Image.new("RGB", (W, H), background)
    d = ImageDraw.Draw(img)
    f_lab, f_note = _font(15), _font(13)

    for idx, p in enumerate(panels):
        r, c = divmod(idx, cols)
        x0, y0 = c * cell[0], r * row_h
        xy, th = np.asarray(p["xy"], float), np.asarray(p["th"], float)
        n = len(xy)
        L = side(xy, th)

        # put the packing's bounding box at the panel origin
        pts = corners(xy, th).reshape(-1, 2)
        lo = pts.min(axis=0)
        xy = xy - lo

        ox = x0 + (cell[0] - L * s) / 2.0
        oy = y0 + margin + 6

        def P(px, py):
            return (ox + px * s, oy + (L - py) * s)

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)

        if p.get("waste"):
            dl.rectangle([P(0, L), P(L, 0)], fill=LIGHT + (255,))

        for i in range(n):
            poly = [P(px, py) for px, py in corners(xy[i:i + 1], th[i:i + 1])[0]]
            col = PALETTE[i % len(PALETTE)]
            dl.polygon(poly, fill=col + (150,), outline=col + (255,))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(img)

        # redraw crisp outlines on top of the alpha
        for i in range(n):
            poly = [P(px, py) for px, py in corners(xy[i:i + 1], th[i:i + 1])[0]]
            d.line(poly + [poly[0]], fill=INK, width=2, joint="curve")

        d.rectangle([P(0, L), P(L, 0)], outline=INK, width=2)

        ly = oy + maxL * s + 10
        d.text((x0 + margin, ly), p["label"], font=f_lab, fill=INK)
        if p.get("note"):
            d.text((x0 + margin, ly + 19), p["note"], font=f_note, fill=GREY)

    img.save(path)
    return path


def figure_n5(panels, path):
    return render(panels, path, cols=len(panels), cell=(380, 430))


def figure_gallery(items, path, cols=4):
    return render(items, path, cols=cols, cell=(250, 280), margin=18)


def plot_L_vs_n(ns, L_grid, L_bound, known, path, W=1120, H=560, PAD=78):
    """Container side L as a function of n: the bound, the grid, the records."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f, fs = _font(17), _font(14)
    ymax = max(L_grid) * 1.05

    def X(n):
        return PAD + (n - 1) / (ns[-1] - 1) * (W - 2 * PAD)

    def Y(v):
        return H - PAD - v / ymax * (H - 2 * PAD)

    for v in range(0, int(ymax) + 1, 2):
        d.line([(PAD, Y(v)), (W - PAD, Y(v))], fill=(232, 232, 236), width=1)
        d.text((PAD - 34, Y(v) - 8), str(v), font=fs, fill=GREY)

    # the area bound
    d.line([(X(n), Y(v)) for n, v in zip(ns, L_bound)], fill=(60, 60, 66), width=2)
    # the grid staircase
    d.line([(X(n), Y(v)) for n, v in zip(ns, L_grid)], fill=(30, 90, 200), width=2)
    # published records
    for n, v in known.items():
        if n <= ns[-1]:
            d.ellipse([X(n) - 4, Y(v) - 4, X(n) + 4, Y(v) + 4],
                      fill=(200, 40, 40), outline="white")

    d.text((PAD, 22), "Container side L(n): the area bound, the grid staircase, the records",
           font=f, fill=INK)
    d.text((PAD, 48), "black = sqrt(n) (area bound)   blue = trivial grid   red = best known packing",
           font=fs, fill=GREY)
    for n in [1, 25, 50, 75, 100]:
        if n <= ns[-1]:
            d.line([(X(n), Y(0)), (X(n), Y(0) + 5)], fill=(60, 60, 66), width=1)
            d.text((X(n) - 8, Y(0) + 9), str(n), font=fs, fill=GREY)
    img.save(path)
    return path


if __name__ == "__main__":
    from pathlib import Path

    out = Path("figures")
    out.mkdir(exist_ok=True)

    gxy, gth = grid(5)
    print(render([
        {"xy": gxy, "th": gth, "label": "n=5, grid",
         "note": "L = 3.0000  score 0.3416"},
    ], out / "_smoke.png"))
