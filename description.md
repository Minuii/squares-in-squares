# Squares in Squares — the problem, the metric, and what we know

A working folder for the Kaggle competition
[**Squares in Squares**](https://www.kaggle.com/competitions/squares-in-squares)
($50,000 prize pool).

Dependencies are in `requirements.txt`. Only `fetch_witnesses.py` needs the
network. The two notebooks are already executed, so their outputs are real.

---

## 1. The problem

For each `n = 1 … 1000`, place `n` non-overlapping **unit squares** (side 1,
free to rotate) inside one axis-aligned square container, and make that
container as small as possible.

A packing is a list of `n` triples `(x, y, θ)` — centre and rotation in radians.
Square `i` occupies `c_i + R(θ_i)·[−½,½]²`.

Two rules define the game:

- **Interiors must be disjoint.** Touching is legal in principle, but the grader
  must be able to certify it: see `plan.md`, "The grader".
- **The container is derived, not chosen.** You never submit `L`. The grader
  wraps the tightest axis-aligned square around your squares:

  ```
  L = max( max_i x − min_i x ,  max_i y − min_i y ) = max(w, h)
  ```

  So there are **no boundary constraints at all** — only pairwise non-overlap —
  and `L` is minimax, which is why a good optimum always has `w ≈ h`.

## 2. The metric

```
score(n) = L / √n − 1
```

The leaderboard is `Σ score(n)` over all puzzles; **lower is better**. Missing
or unparseable puzzles are charged the grid value, so an incomplete submission
is never free but never catastrophic.

Absolute floor: `0`. Trivial grid: `28.9376699166`.

## 3. The floor is reached only at perfect squares

Area gives `n ≤ L²`, so `L ≥ √n` and `score ≥ 0`. Equality needs the squares to
**tile** the container exactly, and that happens if and only if `n` is a perfect
square.

*Proof.* If unit squares tile a square of side `L`, every tile's edges lie in
one of two perpendicular directions, and congruent tiles share that pair. The
bottom edge of the container is covered by tile edges, so one of them is
horizontal — hence every tile is axis-aligned. An axis-aligned unit-square
tiling has integer side `m`, and `n = m²`. ∎

Consequence: **exactly 31 of the 1000 puzzles can score 0** (`n = 1,4,…,961`),
and those are the `1.000000000000000` rows on the leaderboard. Every other
puzzle has a strictly positive optimum that is, in general, unknown.

## 4. What is known

Status for `n ≤ 20`. `proved` means the score is settled — no submission can
improve it.

| n | best known `s(n)` | status | score | grid score |
|---:|---:|:---|---:|---:|
| 1–4 | 1, 2, 2, 2 | proved | 0, .4142, .1547, 0 | same |
| 5 | `2 + √2/2` = 2.7071 | proved | 0.2107 | 0.3416 |
| 6–9 | 3 | proved | .2247, .1339, .0607, 0 | same |
| 10 | `3 + √2/2` = 3.7071 | proved | 0.1723 | 0.2649 |
| 11 | 3.87708359… | proved (2026) | 0.1690 | 0.2060 |
| 12 | 4 | **open** (LB 3.9715) | 0.1547 | same |
| 13–16 | 4 | proved | .1094, .0690, .0328, 0 | same |
| 17 | 4.67553009… | open (LB 4.6604) | 0.1340 | 0.2127 |
| 18 | 4.82287565… | open | 0.1368 | 0.1785 |
| 19 | 4.88561808… | open | 0.1208 | 0.1471 |
| 20 | 5 | open | 0.1180 | same |

Structural facts worth memorising:

- **Solved families:** `s(k²) = s(k²−1) = s(k²−2) = k`. For `n ≤ 1000` that is
  `31 + 30 + 30 = 91` puzzles that are **provably optimal at the plain grid**,
  worth 1.1567 of score.
- Of `n ≤ 324`, only **78** are proved and **246** open (Squares Project
  frontier survey).
- Smallest open case: `n = 12` — best packing 4, proven lower bound 3.9715.
- Asymptotically, waste can be `O(a^{0.6})` (Erdős–Graham, Chung–Graham) but
  must be `Ω(√(a·|a−round a|))` (Roth–Vaughan). True exponent: open.

## 5. What the leaderboard table told us

We parsed the per-puzzle best-`L` table (`frontier.py`). Results:

```
total (aggregate of all records)   22.0562319827
best single team                   22.0565351648
grid baseline                      28.9376699166
```

**#1 was within 0.0003 of the aggregate** and held 372 of the 493 records with a
named team. #2 was 0.043 behind, and the top ten spanned 0.12.

**440 puzzles are still at the plain grid**, worth 7.0961 of the 22.0562:

| | count | score |
|---|---:|---:|
| proved optimal anyway (`k²`, `k²−1`, `k²−2`) | 91 | 1.1567 **locked** |
| open, nobody has tried | 349 | 5.9394 **claimable** |

**Block structure.** Block `k` = `n` from `(k−1)²+1` to `k²`.

| k | block score | at grid | captured |
|---:|---:|---:|---:|
| 10 | 0.7379 | 0.9446 | 22% |
| 20 | 0.7285 | 0.9737 | 25% |
| 31 | 0.6986 | 0.9833 | 29% |

Nearly identical capture rate in every block, because the L-lift carries each
block's improvements into the next, and 387 records above `n = 324` are
per-puzzle results that lifting does not explain.

**The `k²+1` fingerprint.** The digits repeat because these are lifts:
`k + 0.5021527079…` for `k = 29, 30, 31`, `+0.5111108001` for 26, 27.

## 6. Files

| file | what it is |
|---|---|
| `description.md` | this document |
| `plan.md` | the operational plan, phases and acceptance tests |
| `packing_unit_squares.ipynb` | mathematics: floor, proof, known table, validator, optimiser, submission writer |
| `visual_tour.ipynb` | pictures: gallery, perfect squares, the `n=5` construction, `k²−1`/`k²−2`, `L(n)` chart |
| `squares_core.py` | geometry, exact SAT non-overlap test, grid, shrink-wrap, submission I/O |
| `verify_poly.py` | independent overlap test (polygon clipping + shoelace) |
| `viz.py` | drawing code (Pillow) |
| `frontier.py` | reads the leaderboard table and reports where the openings are |
| `diagnose_submission.py` | re-validates a submission CSV and scores it |
| `grader_check.py` | rejects what the Kaggle metric rejects; the submission gate |
| `fetch_witnesses.py`, `witness_to_packing.py` | import the published packings for `n ≤ 324` |
| `gobel_packings.py` | Goebel's centred-diagonal-block family |
| `lift_packings.py` | L-lift and delete closure over `best/` |
| `merge_best.py` | merges `best/` into a gated submission |
| `make_submission.py` | runs the whole pipeline in order |
| `best/` | best packing found for each `n` |
| `build_notebook.py` | regenerates + executes the maths notebook |
| `build_visual_notebook.py` | regenerates + executes the visual notebook |
| `make_figures.py` | regenerates `figures/` |
| `submission_final.csv` | the current submission, 23.1527917816 |
| `figures/` | all images, regenerable |

## 7. Running it

```bash
python make_submission.py              # rebuild the submission, about 30 minutes
python grader_check.py submission_final.csv
python make_figures.py                 # refresh pictures
python build_notebook.py               # rebuild + execute the maths notebook
python build_visual_notebook.py        # rebuild + execute the visual notebook
python frontier.py --clipboard         # analyse the leaderboard table
python diagnose_submission.py submission_final.csv
```

`frontier.py` accepts a file, `-` for stdin, or `--clipboard` (default). It
wants tab-separated rows `n <TAB> L <TAB> team <TAB> date`; the header is
ignored.

## 8. References

1. E. Friedman, *Packing Unit Squares in Squares*, EJC Dynamic Survey DS7 (2009).
2. [The Squares Project](https://squaremath.org/) and
   [jlevy/squares](https://github.com/jlevy/squares) — full research record,
   witnesses with coordinates for `n ≤ 324`, per-case evidence tiers.
3. Kaggle: [Squares in Squares](https://www.kaggle.com/competitions/squares-in-squares).
4. Erdős–Graham (1975); Roth–Vaughan (1978); Chung–Graham (2009);
   Stromquist (2003); Bentz (2010); Nagamochi (2005).
