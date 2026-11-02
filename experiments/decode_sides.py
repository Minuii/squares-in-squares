"""decode_sides.py -- can the record sides alone tell us the record layouts?

EXPERIMENTAL: as of 2026-11-02 they cannot. See plan.md, "Record sides carry
no layout".

public/lb_table.json gives every per-puzzle record side to 50 digits, but no
coordinates. Three tests on the puzzles where a record beats best/:

    families    group all records by the fractional part of L; records that
                share one are the same gadget in a bigger grid, and a family
                that also holds one of our packings would rebuild the rest
    algebra     exact constructions have algebraic sides (integer + 1/sqrt 2
                and so on); mpmath.findpoly looks for a low-degree polynomial,
                with our own packings above n = 324 as the control
    digits      whether the digits past 1e-16 are anything but the expansion
                of a double

    python experiments/decode_sides.py
"""
from __future__ import annotations

import json
import math
import pathlib
from collections import Counter
from decimal import Decimal, getcontext

import mpmath as mp
import numpy as np

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import squares_core as sc

mp.mp.dps = 30
getcontext().prec = 60


def ours() -> dict[int, float]:
    out = {}
    for n in range(1, 1001):
        p = pathlib.Path("best") / f"n{n:03d}.npz"
        out[n] = float(np.load(p)["L"]) if p.exists() else float(sc.grid_side(n))
    return out


def algebraic(x, tol: float = 1e-9):
    """Lowest-degree small-coefficient polynomial of frac(x), or None."""
    f = mp.mpf(x) % 1
    for deg, coeff in ((2, 60), (3, 60), (4, 20)):
        p = mp.findpoly(f, deg, maxcoeff=coeff, tol=tol)
        if p:
            return p
    return None


def main() -> int:
    table = json.load(open("public/lb_table.json", encoding="utf-8"))
    text = {r["n"]: r["L"] for r in table}
    rec = {n: float(s) for n, s in text.items()}
    own = ours()
    gap = sorted(n for n in rec if rec[n] < own[n] - 1e-9)
    print(f"{len(gap)} records beat best/, worth "
          f"{sum((own[n] - rec[n]) / math.sqrt(n) for n in gap):.4f}")

    # families: records with the same fractional part, to 1e-9
    items = sorted((rec[n] % 1, n) for n in rec if rec[n] % 1 > 1e-6)
    fams, cur = [], [items[0]]
    for a, b in zip(items, items[1:]):
        if b[0] - a[0] < 1e-9:
            cur.append(b)
        else:
            fams.append([n for _, n in cur])
            cur = [b]
    fams.append([n for _, n in cur])
    shared = [f for f in fams if sum(n in gap for n in f) >= 2]
    held = [f for f in fams if any(n in gap for n in f) and any(n not in gap for n in f)]
    print(f"families with 2+ gap records: {len(shared)}, covering "
          f"{sum(sum(n in gap for n in f) for f in shared)} of {len(gap)}")
    print(f"families that also hold one of ours: {len(held)}, worth "
          f"{sum((own[n] - rec[n]) / math.sqrt(n) for f in held for n in f if n in gap):.5f}")

    # algebra, with our own packings as the control
    hits = [n for n in gap if algebraic(text[n])]
    control = [n for n in range(325, 1001) if n not in gap and own[n] % 1 > 1e-6]
    print(f"algebraic: records {len(hits)} of {len(gap)}, "
          f"ours {sum(bool(algebraic(own[n])) for n in control)} of {len(control)}")

    # digits past the double
    exact = sum(Decimal(float(s)) == Decimal(s) for s in text.values())
    tails = Counter(s[s.index(".") + 19: s.index(".") + 32] for s in text.values())
    print(f"sides that are exactly a double: {exact} of {len(text)}; "
          f"commonest tails {tails.most_common(3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
