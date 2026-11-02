"""merge_public.py -- bring packings from public submission files into best/.

For every puzzle in each CSV, the packing is read as the doubles Kaggle would
score, checked for overlap, and stored in best/ only if it beats what is
there. best/provenance.json records which puzzles came from which file, so
they can be credited, or removed if the rules turn out to forbid them.

make_submission.py then lifts, expands every contact by 1e-12 and gates each
puzzle with grader_check, exactly as for our own packings.

    python src/merge_public.py public/living_atlas.csv [more.csv ...]
    python make_submission.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

import numpy as np

import squares_core as sc

PROVENANCE = pathlib.Path("best/provenance.json")


def read(path: pathlib.Path) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    rows: dict[int, list[tuple[int, float, float, float]]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rows.setdefault(int(r["n"]), []).append(
                    (int(r["square_id"]), float(r["x"]), float(r["y"]), float(r["angle"])))
            except (KeyError, TypeError, ValueError):
                continue
    out = {}
    for n, rs in rows.items():
        if not 1 <= n <= 1000 or len(rs) != n:
            continue
        rs.sort()
        a = np.array([r[1:] for r in rs], dtype=float)
        if np.isfinite(a).all():
            out[n] = (a[:, :2], a[:, 2])
    return out


def main() -> int:
    paths = [pathlib.Path(p) for p in sys.argv[1:]]
    if not paths:
        print(__doc__)
        return 2
    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() else {}
    total = 0.0
    for path in paths:
        stored = invalid = 0
        for n, (xy, th) in sorted(read(path).items()):
            ok, info = sc.is_valid(xy, th)
            if not ok:
                invalid += 1
                continue
            old = np.load(f"best/n{n:03d}.npz")["L"] if pathlib.Path(f"best/n{n:03d}.npz").exists() \
                else sc.grid_side(n)
            if sc.store_best(n, xy, th):
                stored += 1
                total += (float(old) - info["L"]) / np.sqrt(n)
                prov[str(n)] = path.name
        print(f"{path}: stored {stored} improvements, {invalid} invalid packings skipped")
    PROVENANCE.write_text(json.dumps(dict(sorted(prov.items(), key=lambda kv: int(kv[0]))),
                                     indent=1))
    print(f"score gain before lifting and gating: {total:.6f}")
    print("now run: python make_submission.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
