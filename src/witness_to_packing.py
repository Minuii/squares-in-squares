"""witness_to_packing.py -- turn Squares Project Witness/v2 files into packings.

Reads literature/witnesses/known-best/n-NNN.yaml, extracts one (x, y, theta)
triple per square, normalises so every square has side exactly 1, checks the
result with *both* overlap tests, and stores it in best/nNNN.npz unless a
better packing is already there.

Three representations occur:

    corners       four corner points, read as strings (rationals or decimals)
    center-angle  centre + angle (degrees, or radians where the file says so)
    center-basis  centre + one edge vector

A fourth scalar kind, algebraic-number-field (10 cases: 51, 70, 102, 123, 153,
207, 258, 259, 295, 302), encodes coordinates as polynomials in a generator.
`flatten` rewrites those as plain floats first.

    python src/witness_to_packing.py            # parse + validate + store
    python src/witness_to_packing.py --report   # summary only
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from fractions import Fraction

sys.path.insert(0, "_vendor")
import numpy as np
import yaml

import squares_core as sc
import verify_poly

SRC = pathlib.Path("literature/witnesses/known-best")
OUT = pathlib.Path("best")


def num(v) -> float:
    """Exact rational ('29/6', '0.5') or plain number -> float."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        return float(s)


def geometry(sq, angle_unit: str = "degrees") -> tuple[tuple[float, float], float, float]:
    """(centre, angle_radians, side_length) for one witness square."""
    if "corners" in sq:
        p = [(num(a), num(b)) for a, b in sq["corners"]]
        cx = sum(q[0] for q in p) / 4.0
        cy = sum(q[1] for q in p) / 4.0
        ux, uy = p[1][0] - p[0][0], p[1][1] - p[0][1]
        return (cx, cy), math.atan2(uy, ux), math.hypot(ux, uy)

    c = (num(sq["center"][0]), num(sq["center"][1]))
    if "angle" in sq:
        # angle_unit is stated per file and is not always degrees: four cases
        # (106, 152, 177, 301) are in radians and were rejected as overlaps
        # when every angle was read as degrees.
        a = num(sq["angle"])
        return c, (a if angle_unit == "radians" else math.radians(a)), 1.0

    b = sq["basis"]
    vec = (num(b[0][0]), num(b[0][1])) if isinstance(b[0], list) else (num(b[0]), num(b[1]))
    return c, math.atan2(vec[1], vec[0]), math.hypot(*vec)


def field_element(v, alpha: float) -> float:
    """A number in Q(alpha): either a scalar or a coefficient list.

    The list holds the coefficients of 1, alpha, alpha^2, ... in that order,
    so it has one entry per degree of the minimal polynomial -- two for the
    quadratic fields (n = 51, 295), eight for n = 258. Reading only the first
    two coefficients is what made the higher-degree cases come out as overlaps.
    """
    if isinstance(v, list):
        total, power = 0.0, 1.0
        for c in v:
            total += num(c) * power
            power *= alpha
        return total
    return num(v)


def field_generator(scalar: dict) -> float:
    """Recover alpha from minimal_polynomial + isolating_interval.

    Coefficients are highest-degree first, so [1, 0, -2] is x^2 - 2 and the
    isolating interval [1, 2] selects +sqrt(2). [1, 2, -1] is x^2 + 2x - 1 and
    the interval selects sqrt(2) - 1.
    """
    coeffs = [num(c) for c in scalar["minimal_polynomial"]][::-1]   # low..high
    lo, hi = (num(scalar["isolating_interval"][0]), num(scalar["isolating_interval"][1]))
    roots = np.roots(coeffs[::-1])
    real = roots[np.abs(roots.imag) < 1e-12].real
    inside = real[(real >= lo - 1e-9) & (real <= hi + 1e-9)]
    if not len(inside):
        inside = real[np.argmin(np.abs(real - 0.5 * (lo + hi))):][:1]
    return float(inside[0])


def flatten(w) -> None:
    """Rewrite every coordinate in an algebraic witness as a plain float."""
    alpha = field_generator(w["scalar"])
    w["side"] = field_element(w["side"], alpha)
    for sq in w["squares"]:
        if "corners" in sq:
            sq["corners"] = [[field_element(x, alpha), field_element(y, alpha)]
                             for x, y in sq["corners"]]
            continue
        sq["center"] = [field_element(sq["center"][0], alpha),
                        field_element(sq["center"][1], alpha)]
        if "basis" in sq:
            # basis is a 2-list of coordinates, each a scalar or a [p, q] pair
            b = sq["basis"]
            sq["basis"] = [field_element(b[0], alpha), field_element(b[1], alpha)]
    w["scalar"]["kind"] = "decimal"


def parse(path: pathlib.Path):
    w = yaml.safe_load(path.read_text(encoding="utf-8"))["witness"]
    if w["scalar"]["kind"] == "algebraic-number-field":
        try:
            flatten(w)
        except Exception as e:                           # noqa: BLE001
            return None, w, f"algebraic decode failed: {type(e).__name__}: {e}"

    n = int(w["n"])
    rows = w["squares"]
    if len(rows) != n:
        return None, w, f"expected {n} squares, found {len(rows)}"

    unit = (w.get("coordinates") or {}).get("angle_unit") or "degrees"
    ctr, ang, side = [], [], []
    for sq in rows:
        c, a, s = geometry(sq, unit)
        ctr.append(c)
        ang.append(a)
        side.append(s)

    side = np.asarray(side)
    scale = float(np.median(side))
    if not np.isfinite(scale) or scale <= 0:
        return None, w, "degenerate side length"

    xy = np.asarray(ctr) / scale
    th = np.asarray(ang)
    # normalise angles into (-pi/2, pi/2]: a square is invariant under pi/2
    th = np.mod(th, np.pi / 2)
    th = np.where(th > np.pi / 4, th - np.pi / 2, th)
    return (xy, th), w, None


def check(xy, th, w):
    """Validate, and compare our L against the witness's declared side."""
    n = len(xy)
    ok_sat, info = sc.is_valid(xy, th)
    L = sc.container_side(xy, th)
    declared = None
    try:
        sd = w["side"]
        declared = num(sd[0]) if isinstance(sd, list) else num(sd)
    except Exception:                                    # noqa: BLE001
        pass
    rel = None if declared is None else abs(L - declared) / max(declared, 1e-12)
    return {"n": n, "L": L, "declared": declared, "rel_err": rel,
            "sat_ok": ok_sat, "pen": info["max_penetration"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--skip-poly", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    files = sorted(SRC.glob("n-*.yaml"))
    good, bad, skipped = [], [], []

    for f in files:
        packing, w, why = parse(f)
        if packing is None:
            skipped.append((int(w["n"]), why))
            continue
        xy, th = packing
        c = check(xy, th, w)
        if not c["sat_ok"]:
            bad.append((c["n"], f"SAT overlap {c['pen']:.2e}"))
            continue
        if not args.skip_poly:
            area, where = verify_poly.max_overlap_area(xy, th)
            if area > 1e-12:
                bad.append((c["n"], f"poly overlap {area:.2e} at {where}"))
                continue
        if c["rel_err"] is not None and c["rel_err"] > 1e-9:
            bad.append((c["n"], f"L mismatch {c['L']:.12f} vs {c['declared']:.12f}"))
            continue
        good.append(c)
        if not args.report:
            sc.store_best(c["n"], xy, th, OUT)

    good.sort(key=lambda r: r["n"])
    print(f"parsed      {len(good)}")
    print(f"rejected    {len(bad)}")
    print(f"skipped     {len(skipped)}")
    for n, why in bad[:10]:
        print(f"   reject n={n}: {why}")
    for n, why in skipped[:12]:
        print(f"   skip   n={n}: {why}")

    if good:
        tot = sum(r["L"] / math.sqrt(r["n"]) - 1.0 for r in good)
        grid = sum(sc.grid_side(r["n"]) / math.sqrt(r["n"]) - 1.0 for r in good)
        print(f"\nscore of parsed set : {tot:.10f}")
        print(f"grid for same set   : {grid:.10f}   (saved {grid - tot:+.4f})")
        worst = max((r for r in good if r["declared"]), key=lambda r: abs(r["rel_err"] or 0))
        print(f"largest L deviation : n={worst['n']} rel={worst['rel_err']:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
