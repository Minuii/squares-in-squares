# Squares in Squares: what we did and why

A start-to-finish account of this repository's work on the Kaggle competition
[Squares in Squares](https://www.kaggle.com/competitions/squares-in-squares),
from the all-grid baseline at **28.94** to the current file at **22.2570**.
The executed companion is [`walkthrough.ipynb`](notebooks/walkthrough.ipynb), which
rebuilds every number and picture below from `best/` and the scripts.

---

## 1. The problem in one paragraph

For each `n = 1 … 1000`, place `n` unit squares (any rotation) so that their
interiors do not overlap, and make the tightest axis-aligned square around them
as small as possible. You submit centres and angles; the grader derives the
side `L`. Each puzzle scores `L/√n − 1`, the leaderboard is the sum over all
1000, and lower is better.

Two facts shape everything:

- **The floor is 0, and only perfect squares reach it.** Unit squares tile a
  square only when `n = m²`, so 31 puzzles are free and the other 969 have a
  strictly positive, mostly unknown optimum.
- **The container is derived, not chosen.** There are no wall constraints,
  only pairwise non-overlap, and `L = max(width, height)`.

The trivial packing, a `⌈√n⌉ × ⌈√n⌉` grid, scores **28.9377**.

## 2. Score history

| step | script | gain | running score |
|---|---|---:|---:|
| all-grid baseline | `squares_core.grid` | | 28.94 |
| published best-known packings, `n ≤ 324` | `src/fetch_witnesses.py`, `src/witness_to_packing.py` | 3.0346 | |
| Göbel's centred diagonal block, `n > 324` | `src/gobel_packings.py` | 1.2027 | |
| L-lift and delete closure | `src/lift_packings.py` | 1.4141 | 23.15 |
| Friedman's off-centre family, Göbel's diagonal strip, lifted | `src/gobel_packings.py` | 0.1640 | **22.9888** (own work, confirmed on Kaggle) |
| public packings from the Living Atlas output, 614 puzzles | `src/merge_public.py` | 0.7318 | **22.2570079** (confirmed on Kaggle) |
| contact-LP polish of `best/` | `src/polish_best.py` | 1.8e-8 | 22.2570078917 |
| `--refresh`: 36 newer public packings | `make_submission.py --refresh` | 2.2e-5 | **22.2569857** (current, local) |

For scale on 2026-11-02: #1 on the leaderboard was 22.0544, and the aggregate
of every known per-puzzle record was 22.0562.

## 3. The grader, and why it mattered most

Kaggle's [metric notebook](https://www.kaggle.com/code/metric/squares-in-squares)
is public, and reading it changed the project. A rejected puzzle does not fail
the file; it is quietly charged the grid value. Our first files lost 0.21 this
way without any error.

What the metric actually does:

1. A fast double-precision test throws out pairs that are clearly apart or
   clearly overlapping.
2. Pairs within about 1e-8 of contact are certified with `mpmath` interval
   arithmetic at 50, 100, 200 and 500 digits, using the submitted literals.
3. **Any true overlap is rejected, even 1e-16.** A double-precision
   separating-axis test cannot see this.
4. **Exact contact at non-dyadic coordinates is rejected as undecidable.**
   `0.5` against `1.5` passes; `3.35` against `4.35` does not, because the
   interval never shrinks to a definite sign.
5. Kaggle parses the CSV into doubles first, so you must certify the doubles,
   not the text. A public merge certified on its text scored 22.26 locally and
   25.36 on Kaggle.

Our response:

- `src/merge_best.py` expands every packing by a factor of `1 + 1e-12` about its
  centroid. Centre distances only grow, so every contact opens. Cost: about
  1e-9 of total score.
- `src/grader_check.py` re-implements the metric's rules and runs on the
  coordinates exactly as written. It predicted Kaggle's score to 1e-10 and is
  the gate for every submission.

## 4. The packings

### 4.1 Published records for `n ≤ 324`

[The Squares Project](https://github.com/jlevy/squares) (CC BY 4.0) publishes
best-known packings as "witnesses" in three formats: `corners` (175 files),
`center-basis` (75) and `center-angle` (74), including 10 in algebraic number
fields and 4 with angles in radians. `src/witness_to_packing.py` converts them all,
normalises the side to unit squares, and stores them in `best/`. Gain: 3.03.

### 4.2 Göbel's centred diagonal block for `n > 324`

Above 324 nothing was imported, so we built Göbel's family directly: an `a`-deep
frame of axis-aligned squares around a `b × b` block tilted 45°. It holds
`2a² + 2a + b²` squares in side `a + 1 + b/√2`, valid when
`a − 1 < b/√2 < a + 1`. For an `n` below the family size, `trim` keeps the `n`
squares nearest the centre. 2,704 builds, 0 invalid, 176 puzzles improved.
Gain: 1.20.

### 4.3 The L-lift

Given a packing of side `L`, add an L-shaped strip of `2⌊L⌋ + 1` axis-aligned
squares along the top and right:

```
s(n + 2⌊s(n)⌋ + 1) ≤ s(n) + 1
```

With the companion rule "delete a square from `n + 1`", `src/lift_packings.py`
closes `best/` under both until nothing changes. One good seed improves a whole
chain: `842 → 901 → 962` are lifts of each other, which is why `n = k² + 1`
shares digits across `k = 29, 30, 31`. 230 puzzles improved. Gain: 1.41.

### 4.4 Friedman's off-centre family and Göbel's diagonal strip

- **Off-centre:** `2a² + 4a + b² + 1` squares in side `a + 3/2 + b/√2`, valid
  for `a − 1/2 < b/√2 < a + 1/2`. The block is squeezed into a rectangle and a
  column of `2a + 1` squares stands beside it.
- **Diagonal strip:** a 45° strip from corner to corner with staircases either
  side, `a² + a + 2 + (⌊(a − 1)√2⌋ + 1)` squares in side `a + 1 + √2/2`.

Only 18 builds above 324 beat what we had, but lifting carried them to 97
puzzles. Gain: 0.16, bringing our own-work score to **22.9888**, which Kaggle
confirmed at 22.9888002452.

A lesson here: an early estimate of 0.76 used the parent family's wider
validity condition, which admits impossible packings such as `n = 21` at
4.914. The narrower condition is the right one.

### 4.5 Public packings

About 1,000 of the 1,398 teams on the leaderboard sat between 22.18 and 22.72,
because public notebooks merge everyone's published packings. `src/merge_public.py`
imports a public `submission.csv`, re-certifies each puzzle with the grader
rules, and keeps only improvements, recording the source of each in
`best/provenance.json`. From malyshevdanil's
[Living Atlas](https://www.kaggle.com/code/malyshevdanil/squares-in-squares-living-atlas-of-tight-packings)
output this took 578 puzzles, plus 36 from a later `--refresh`: 614 in all.
Gain: 0.73.

Whether rule C.14(a), "your own original work", permits submitting public
packings has no official answer yet. Deleting the files listed in
`best/provenance.json` reverts to the own-work set.

## 5. What did not work

| attempt | result | why |
|---|---|---|
| `shrink`, `sa_feasible` in `src/squares_core.py` | no records | `shrink` never leaves the grid; `sa_feasible` only polishes |
| contact-LP polisher (`src/contact_polish.py`) on our packings | gain 0 | our packings are jammed: the LP's best step is `dL ≈ +7e-10` |
| same LP after a random kick | worse | a kick large enough to unjam costs 1–2% of `L`; 300 LP steps recover 15–25% of it |
| same LP over the 547 public packings (`src/polish_best.py`) | 1.8e-8 total | they are already polished; 95% of the gain was at `n = 916` |
| batched penalty search (`experiments/gpu_search.py`) | fails below the record | angle errors add up along rows of 16–20 squares, and the penalty settles in tangled minima with `E ≈ 1e-4` |
| a private GPU search kernel on Kaggle | did not run | the account received no GPU or internet; staged for later |

The contact LP is sound; it needs unjammed starting packings, which is what the
public GPU searches provide and what ours do not.

## 6. Where the remaining gap is

- 387 records above `n = 324` cannot be derived from any other record by
  lifting or deleting. They need genuinely new packings, and the ~0.2 gap to #1
  lives there.
- 453 puzzles are still at the grid, worth 7.29 of the score. 91 of them
  (`k²`, `k² − 1`, `k² − 2`) are provably locked; the other 362 are open but
  low value per puzzle.
- The grid tail is a frontier, not a wall: `n = 877` already beats side 30,
  while `878 … 900` are merely unbeaten.

## 7. Next steps

1. New unjammed starting packings (global search with rigid row and block
   moves, or new constructions), finished by the contact LP.
2. Rank seeds by chain value: an improvement at `n` counts once for every lift
   it propagates to.
3. Attack the frontier at `k² − (j_min − 1)`.
4. Relaunch the Kaggle GPU kernel once the account has GPU access.

## 8. Reproducing it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python src/fetch_witnesses.py
.venv/Scripts/python make_submission.py             # rebuild from best/
.venv/Scripts/python make_submission.py --refresh   # pull newer public packings first
.venv/Scripts/python notebooks/build_walkthrough_notebook.py # rebuild notebooks/walkthrough.ipynb
```

`make_submission.py` takes about 15 minutes on 8 cores, writes
`submission_final.csv`, and never makes `best/` worse.

Credits and licences are in [`README.md`](README.md).
