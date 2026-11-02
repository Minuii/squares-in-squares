"""gobel_scan.py -- does Goebel's centred-diagonal-block family beat the grid?

Friedman DS7's statement of the family: for integers a, b with
a - 1 < b/sqrt(2) < a + 1, exactly 2a^2 + 2a + b^2 unit squares pack into a
square of side a + 1 + b/sqrt(2). Because deleting squares can only shrink the
bounding box, the family also delivers a packing for every n <= count(a, b) at
side at most that value.

So the question for blocks 19-31 is simply: is
    min over admissible (a,b) with count >= n of (a + 1 + b/sqrt(2))
below the grid side ceil(sqrt(n))? If it is not, the family is asymptotically
dense but useless exactly where we need it.
"""
import math


def admits(a: int, b: int) -> bool:
    return a >= 1 and b >= 1 and a - 1 < b / math.sqrt(2) < a + 1


def count(a: int, b: int) -> int:
    return 2 * a * a + 2 * a + b * b


def best_side(n: int) -> float:
    best = math.inf
    for a in range(1, 40):
        for b in range(1, 70):
            if admits(a, b) and count(a, b) >= n:
                best = min(best, a + 1 + b / math.sqrt(2))
    return best


def main() -> int:
    beats = []
    for n in range(1, 1001):
        g = math.ceil(math.sqrt(n) - 1e-12)
        L = best_side(n)
        if L < g - 1e-9:
            beats.append((n, L, g))
    print(f"n where the family beats the grid: {len(beats)}")
    print(f"  of those with n <= 324 : {sum(1 for n, _, _ in beats if n <= 324)}")
    print(f"  of those with n >  324 : {sum(1 for n, _, _ in beats if n > 324)}")
    for n, L, g in beats[:12]:
        print(f"    n={n:4d}  family L={L:.6f}  grid={g}  score={L/math.sqrt(n)-1:.6f}")
    print()
    for n in (900, 869, 841, 729, 700, 625, 400, 330):
        g = math.ceil(math.sqrt(n) - 1e-12)
        print(f"n={n:4d}  grid={g:2d}  family best={best_side(n):.4f}  "
              f"{'better' if best_side(n) < g - 1e-9 else 'no help'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
