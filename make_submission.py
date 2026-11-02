"""make_submission.py -- rebuild submission_final.csv from the sources, in order.

Every step only ever improves best/, so this is safe to rerun.

    python make_submission.py
    python make_submission.py --refresh   # first pull the newest public packings

--refresh needs a Kaggle API token in ~/.kaggle/access_token.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

PY = [sys.executable]
KAGGLE = [str(pathlib.Path(sys.executable).with_name("kaggle"))]
PUBLIC = "malyshevdanil/squares-in-squares-living-atlas-of-tight-packings"

REFRESH = [
    KAGGLE + ["kernels", "output", PUBLIC, "-p", "public", "-o",
              "--file-pattern", r"^submission\.csv$"],
    PY + ["merge_public.py", "public/submission.csv"],
]
STEPS = [
    PY + ["witness_to_packing.py", "--skip-poly"],
    PY + ["gobel_packings.py", "--n-min", "325"],  # families only above the witnesses
    PY + ["lift_packings.py"],
    PY + ["merge_best.py", "--out", "submission_final.csv"],
    PY + ["diagnose_submission.py", "submission_final.csv", "--top", "5"],
]


def main() -> int:
    for step in (REFRESH if "--refresh" in sys.argv else []) + STEPS:
        print(f"\n=== {' '.join(step[1:])}", flush=True)
        code = subprocess.run(step).returncode
        if code:
            print(f"failed with exit code {code}")
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
