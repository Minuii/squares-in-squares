"""fetch_witnesses.py -- pull the known-best Witness/v2 files (n = 1..324).

The Squares Project publishes exact best-known packings for n <= 324 as
Witness/v2 YAML (coordinates in rational / algebraic / decimal form).
This downloads them from raw.githubusercontent.com into
literature/witnesses/known-best/ so the parser can work offline.

    python fetch_witnesses.py
"""
from __future__ import annotations

import concurrent.futures as cf
import pathlib
import urllib.request

BASE = ("https://raw.githubusercontent.com/jlevy/squares/main/"
        "packing/witnesses/known-best/n-{n:03d}.yaml")
OUT = pathlib.Path("literature/witnesses/known-best")


def grab(n: int) -> tuple[int, str]:
    dest = OUT / f"n-{n:03d}.yaml"
    if dest.exists() and dest.stat().st_size > 0:
        return n, "cached"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(BASE.format(n=n), timeout=30) as r:
                dest.write_bytes(r.read())
            return n, "ok"
        except Exception as e:                      # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
    return n, err


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    todo = list(range(1, 325))
    ok = bad = 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for n, status in ex.map(grab, todo):
            if status in ("ok", "cached"):
                ok += 1
            else:
                bad += 1
                print(f"n={n}: {status}")
    size = sum(p.stat().st_size for p in OUT.glob("*.yaml"))
    print(f"downloaded {ok} / {len(todo)}  ({bad} failed)  {size/1024:.1f} KiB in {OUT}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
