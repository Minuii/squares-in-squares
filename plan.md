# Plan

**Objective:** get `Σ (L/√n − 1)` as low as possible on the
[Squares in Squares](https://www.kaggle.com/competitions/squares-in-squares)
leaderboard.

**Timeline:** started 2026-10-21. Milestones 2027-01-17 and 2027-04-18.
Final submission 2027-07-18.

---

## 0. State of play

Figures as of 2026-11-02.

| thing | value | source |
|---|---|---|
| all-grid baseline | 28.9376699166 | computed |
| **our file (`submission_final.csv`)** | **22.9888002453** | Kaggle scored it 22.9888002452 on 2026-11-02 |
| best merge of public packings | 22.2591301174 | public notebook |
| aggregate of every record (2026-11-01) | 22.0562319827 | per-puzzle table |
| #1 team | 22.0544214515 | leaderboard, 2026-11-02 |
| puzzles still at grid | 564 → 9.3996 | `attack_surface.py` |
| …of which provably locked | 91 → 1.1567 | `k²`, `k²−1`, `k²−2` |
| …of which open | 473 → 8.2430 | |

Progress: **28.8042 → 22.9888**.

| move | gain |
|---|---:|
| published witnesses for `n ≤ 324` | 3.0346 |
| Goebel's centred block, `n > 324` | 1.2027 |
| L-lift closure | 1.4141 |
| Friedman's off-centre family and Göbel's diagonal strip, then lifted | 0.1640 |

About 1,000 of 1,398 teams on the 2026-11-01 board sat between 22.18 and 22.72,
because public notebooks merge everyone's published packings. Our gap to rank
200 is about 0.9, and it is mostly not new mathematics.

---

## Done

- [x] Grids for `n = 1…1000` merged with the 91 solved families.
- [x] 324 witnesses imported (`fetch_witnesses.py`, `witness_to_packing.py`):
      `corners` (175), `center-basis` (75), `center-angle` (74), including 10
      algebraic-field files and 4 files with `angle_unit: radians`.
- [x] Goebel's centred-diagonal-block family (`gobel_packings.py`): 2704 builds,
      0 invalid, 176 puzzles improved.
- [x] L-lift closure (`lift_packings.py`): 230 puzzles improved.
- [x] Friedman's off-centre family (`2a² + 4a + b² + 1` in `a + 3/2 + b/√2`,
      `a − 1/2 < b/√2 < a + 1/2`) and Göbel's diagonal strip, in
      `gobel_packings.py`. 18 builds above 324 were stored, and lifting
      carried them to 97 puzzles. An estimate made with the parent family's
      wider condition `a − 1 < b/√2 < a + 1` gave 0.76, but that condition
      admits impossible entries such as `n = 21` at 4.914.
- [x] Grader gate (`grader_check.py`): every puzzle is checked by the metric's
      rules on the coordinates as written.
- [x] `make_submission.py` rebuilds everything in order. About 30 minutes on 8
      cores.
- [ ] Upload once and confirm the local score.

---

## What we learned

### The grader

The [metric notebook](https://www.kaggle.com/code/metric/squares-in-squares) is
public and settles what used to be open here:

- Pairs within 1e-8 of contact go to interval arithmetic at 50, 100, 200 and
  500 digits. A true overlap of any size is rejected, including 1e-16.
- Two squares touching exactly at non-dyadic coordinates can never be certified
  and are rejected as undecidable. `0.5` and `1.5` pass; `3.35` and `4.35` do
  not.
- A rejected puzzle is charged the grid ceiling. The rest of the file still
  scores, so a bad file does not fail loudly.
- Kaggle reads the CSV as correctly rounded doubles. Digits past a double are
  dropped before the metric runs, so certify the double, not the text. A public
  merge certified on its text scored 22.26 locally and 25.36 on Kaggle.

Our old file passed a double-precision test yet had real overlaps of about
1e-16 at `n = 5` and `n = 17`, costing 0.21. The fix is to expand every packing
from `best/` by 1e-12 about its centroid, for about 1e-9 of total score.

### The L-lift

A packing of `n` squares in side `L` gains an L-shaped strip of
`2⌊L⌋ + 1` unit squares: `s(n + 2⌊s(n)⌋ + 1) ≤ s(n) + 1`.

The per-puzzle table is already closed under this rule: applying it improves 0
records. It is why `n = k² + 1` shares digits across `k = 29, 30, 31`:
`842 → 901 → 962` are lifts. A better seed therefore improves its whole chain.

### What the remaining gap is

387 records above `n = 324` cannot be derived from another record by lifting or
deleting. Those need new packings, and the gap to the public merge lives there.
After lifting we sit 1.10 above the record aggregate, and Göbel's diagonal strip
would add only about 0.05 of that.

Our `sa_feasible` and `shrink` do not find them: `shrink` never leaves the grid,
and `sa_feasible` only polishes. That is a limit of these tools, not of search.
The field's records rise smoothly with `n` and arrive daily, which points to
numeric search.

### The grid tail is a frontier, not a wall

Only `k²`, `k²−1` and `k²−2` are proved. The smallest `j` with a record below
`k` is 23 at `k = 30` and 24 at `k = 31`, so `n = 877` is already below 30 while
`n = 878…900` are merely unbeaten. These puzzles are low value, but any
improvement there is a fresh record.

---

### The contact-LP polisher finds nothing on our packings

`contact_polish.py` is a port of the trust-region sequential LP from public
Kaggle code (credits in `README.md`). It is correct, and every output passes
`repair`, but on our packings it gains nothing, measured 2026-11-02:

| mode | puzzles tried | gain |
|---|---|---:|
| polish as is | 376, 457, 19, 338 | 0 |
| delete a square from `n + 1`, then polish | 376, 417, 457, 338 | 0 |
| kick by σ = 0.003 or 0.01, expand, polish 60 s | 376, 457, 156, 297 | worse |

The LP's best step is `dL ≈ +7e-10`, so these packings are jammed. Göbel's
construction is a rigid wall–frame–diamond–frame–wall chain, and the
witnesses are already optimal locally. A kick big enough to unjam them costs
1–2% of `L`, and 300 LP steps recover only 15–25% of that.

In the public notebook the same LP gains 0.0002–0.0015 per puzzle, because it
is applied to public and GPU-searched packings that are not jammed. The
polisher needs a better start, not more time.

### Penalty search fails on these packings

`gpu_search.py` is a batched penalty search: jittered starts, Adam with a
shrinking box and growing squares, then L-BFGS in float64. It runs on CPU or
GPU, and `import_found.py` brings results home. Measured on CPU, 2026-11-02:

| test | result |
|---|---|
| no noise, target `L + 0.001`, `n = 260` | succeeds, a plumbing check |
| noise 1e-4, target `L + 0.001` | fails |
| noise 0.002, target `L − 1e-4`, `n = 206, 260` (records exist 2.6e-5 and 2.7e-4 below) | fails |
| target `L − 0.005`, `n = 376` | fails |
| starts from `n + 1` minus one square | always fail |

Tiny angle errors add up along rows of 16–20 squares, so a jittered start no
longer fits, and the overlap penalty settles in tangled local minima with
`E ≈ 1e-4` that L-BFGS cannot leave. A Colab notebook was not built, since
this would only spend GPU time.

What would be needed instead: moves that keep rows rigid (shift or rotate
whole rows or blocks), or a combinatorial search over layouts, with the
contact LP as the finisher.

---

## Next

1. ~~Upload and confirm~~ Done: Kaggle 22.9888002452, local 22.9888002453.
2. **Decide on public packings.** Merging them is worth about 0.9, and
   `contact_polish.py` can then be run on them. See the compliance note below.
3. **New starting packings.** Make unjammed candidates for the polisher with a
   global search (L-BFGS on a penalty, on GPU as the public code does), or with
   new constructions.
4. **Search seeds, ranked by chain value.** An improvement at `n` counts once
   for every lift it propagates to.
5. **Attack the frontier** at `k² − (j_min − 1)`.

---

## Compliance

- Section B.6 permits External Data that is public, free and equally available.
- Whether C.14(a) "your own original work" allows submitting public packings
  directly has no official answer as of 2026-11-02
  ([thread](https://www.kaggle.com/competitions/squares-in-squares/discussion/752580)).
  This matters for prize eligibility.
- The witnesses are CC BY 4.0, so they need attribution. See `README.md`.
- Winners must supply code that regenerates the submission;
  `make_submission.py` is that path.

---

## Rules of engagement

1. **Never regress.** `squares_core.store_best` writes only improvements.
2. **`grader_check.py` is the gate.** A double-precision pass proves nothing.
3. **Rescale before submitting.** `L` is translation-invariant, not
   scale-invariant, so witnesses are normalised to unit side on import.
4. **Measure against the table, not the leaderboard.**
