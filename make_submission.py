"""make_submission.py -- rebuild submission_final.csv from the sources, in order.

Every step only ever improves best/, so this is safe to rerun.

    python make_submission.py
"""
from __future__ import annotations

import subprocess
import sys

STEPS = [
    ["witness_to_packing.py", "--skip-poly"],
    ["gobel_packings.py", "--n-min", "325"],  # families only above the witnesses
    ["lift_packings.py"],
    ["merge_best.py", "--out", "submission_final.csv"],
    ["grader_check.py", "submission_final.csv"],
    ["diagnose_submission.py", "submission_final.csv", "--top", "5"],
]


def main() -> int:
    for step in STEPS:
        print(f"\n=== {' '.join(step)}", flush=True)
        code = subprocess.run([sys.executable, *step]).returncode
        if code:
            print(f"failed with exit code {code}")
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
