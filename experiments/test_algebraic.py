"""test_algebraic.py -- sanity-check the quadratic-field decode on the 10 cases."""
import pathlib
import sys

sys.path.insert(0, "_vendor")
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import witness_to_packing as W

SRC = pathlib.Path("literature/witnesses/known-best")
ALG = [51, 70, 102, 123, 153, 207, 258, 259, 295, 302]

for n in ALG:
    w = yaml.safe_load((SRC / f"n-{n:03d}.yaml").read_text(encoding="utf-8"))["witness"]
    a = W.field_generator(w["scalar"])
    side = W.field_element(w["side"], a)
    print(f"n={n:4d}  alpha={a:.12f}  poly={w['scalar']['minimal_polynomial']}  "
          f"declared side={side:.10f}")
