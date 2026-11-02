"""inspect_alg.py -- how many coefficients does an algebraic coordinate carry?"""
import pathlib
import sys

sys.path.insert(0, "_vendor")
import yaml

SRC = pathlib.Path("literature/witnesses/known-best")
for n in (102, 258, 70, 123):
    w = yaml.safe_load((SRC / f"n-{n:03d}.yaml").read_text(encoding="utf-8"))["witness"]
    deg = len(w["scalar"]["minimal_polynomial"]) - 1
    c = w["squares"][0]["center"]
    depth = lambda v: 0 if not isinstance(v, list) else 1 + max(depth(x) for x in v)
    widths = [len(v) if isinstance(v, list) else None for v in c]
    print(f"n={n} degree={deg} center_depth={depth(c)} widths={widths}")
    print(f"   center[0] = {str(c[0])[:90]}")
