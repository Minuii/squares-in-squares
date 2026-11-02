"""
frontier.py -- read a per-puzzle best-L table and say where the contest is.

The leaderboard export looks like

    n<TAB>Best Side Length L (50 decimals)<TAB>TeamName<TAB>DateSubmitted

Tab- or comma-separated; the header is ignored. Any n missing from the file is
assumed to be at the grid value.

    python experiments/frontier.py leaderboard.tsv      # from a file
    python experiments/frontier.py --clipboard          # read the table from the clipboard
    python experiments/frontier.py -                    # read it from stdin
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import subprocess
import sys


def clipboard_text() -> str:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        raise SystemExit("powershell not found; save the table to a file instead")
    if out.returncode != 0 or not out.stdout.strip():
        raise SystemExit("clipboard is empty -- copy the leaderboard table, then rerun")
    return out.stdout


def file_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    except FileNotFoundError:
        raise SystemExit(
            f"no such file: {path}\n"
            "  copy the leaderboard table, then run:  python experiments/frontier.py --clipboard\n"
            "  or save it as leaderboard.tsv and run: python experiments/frontier.py leaderboard.tsv"
        )


def parse(text: str) -> dict[int, tuple[float, str]]:
    """n -> (L, team). Robust to tab or comma, and to a header row."""
    delim = "\t" if text.count("\t") > text.count(",") else ","
    out: dict[int, tuple[float, str]] = {}
    for row in csv.reader(io.StringIO(text), delimiter=delim):
        if len(row) < 2:
            continue
        try:
            n = int(row[0].strip())
            L = float(row[1].strip())
        except ValueError:
            continue                          # header or junk
        team = row[2].strip() if len(row) > 2 else "-"
        out[n] = (L, team)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=None,
                    help="leaderboard file, or '-' to read stdin")
    ap.add_argument("-c", "--clipboard", action="store_true",
                    help="read the table from the Windows clipboard")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    if args.clipboard or args.path is None:
        text = clipboard_text()
    elif args.path == "-":
        text = sys.stdin.read()
    else:
        text = file_text(args.path)

    tab = parse(text)
    if not tab:
        snippet = text.strip()[:300].replace("\t", "<TAB>").replace("\n", "\\n")
        print("no rows parsed -- expected lines like:  5<TAB>2.70710678118654<TAB>-<TAB>-",
              file=sys.stderr)
        print(f"what I actually got: {snippet}", file=sys.stderr)
        return 1

    def grid_L(n):
        return math.ceil(math.sqrt(n) - 1e-12)

    rows = []
    for n in range(1, 1001):
        g = grid_L(n)
        L, team = tab.get(n, (float(g), "-"))
        rows.append((n, L, L / math.sqrt(n) - 1.0, team, g))

    total = sum(r[2] for r in rows)
    grid_total = sum(grid_L(n) / math.sqrt(n) - 1.0 for n in range(1, 1001))

    print(f"rows parsed  : {len(tab)}")
    print(f"total score  : {total:.10f}")
    print(f"grid baseline: {grid_total:.10f}   (frontier is {grid_total - total:+.4f} better)")
    print(f"floor        : 0.0000000000   "
          f"({100 * total / grid_total:.1f}% of the baseline is still on the table)")
    print()

    untouched = [r for r in rows if r[3] in ("-", "") and abs(r[1] - r[4]) < 1e-9]

    def locked(n):
        """n = k^2, k^2-1 or k^2-2: the grid is PROVED optimal, nothing to win."""
        k = grid_L(n)
        return n in (k * k, k * k - 1, k * k - 2)

    lock = [r for r in untouched if locked(r[0])]
    open_ = [r for r in untouched if not locked(r[0])]
    print(f"puzzles still at the plain grid (no submitter): {len(untouched)}")
    print(f"  they contribute {sum(r[2] for r in untouched):.4f} of the {total:.4f} total")
    print(f"    proved optimal anyway (k^2, k^2-1, k^2-2): {len(lock):>4} "
          f"-> {sum(r[2] for r in lock):.4f}  LOCKED")
    print(f"    open, nobody has tried:                    {len(open_):>4} "
          f"-> {sum(r[2] for r in open_):.4f}  claimable")
    print()

    print("per block (block k = n from (k-1)^2+1 to k^2)")
    print(f"{'k':>3} {'n range':>12} {'touched':>8} {'untouched':>10} "
          f"{'block':>9} {'as grid':>9}")
    for k in range(2, 32):
        lo, hi = (k - 1) ** 2 + 1, k * k
        sub = [r for r in rows if lo <= r[0] <= hi]
        t = sum(1 for r in sub if r[3] not in ("-", ""))
        block = sum(r[2] for r in sub)
        gblock = sum(grid_L(r[0]) / math.sqrt(r[0]) - 1.0 for r in sub)
        print(f"{k:>3} {lo:>5}-{hi:<6} {t:>8} {len(sub) - t:>10} "
              f"{block:>9.4f} {gblock:>9.4f}")
    print()

    print(f"biggest single scores still on the table -- top {args.top}")
    print(f"{'n':>5} {'L':>12} {'score':>9} {'sqrt n':>9} {'slack':>8}  team")
    for n, L, s, team, g in sorted(rows, key=lambda r: -r[2])[: args.top]:
        print(f"{n:>5} {L:>12.6f} {s:>9.4f} {math.sqrt(n):>9.4f} "
              f"{L - math.sqrt(n):>8.4f}  {team or '-'}")
    print()

    print("open untouched puzzles with the most room (any improvement is a record)")
    print(f"{'n':>5} {'grid L':>7} {'score now':>10} {'sqrt n':>8} {'room':>8}")
    cand = [r for r in open_ if r[2] > 0]
    for n, L, s, team, g in sorted(cand, key=lambda r: -r[2])[: args.top]:
        print(f"{n:>5} {g:>7} {s:>10.4f} {math.sqrt(n):>8.4f} {L - math.sqrt(n):>8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
