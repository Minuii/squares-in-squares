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
| **our file (`submission_final.csv`)** | **22.2569857322** | Kaggle scored it 22.2569857321 on 2026-11-02; after the first `--refresh` (36 newer public packings) |
| previous file | 22.2570079095 | Kaggle scored it 22.2570079095 on 2026-11-02; includes 614 public packings |
| own packings only | 22.9888002453 | Kaggle scored it 22.9888002452 on 2026-11-02 |
| best merge of public packings | 22.2570079163 | Living Atlas, newest run |
| aggregate of every record (2026-11-01) | 22.0562319827 | per-puzzle table |
| #1 team | 22.0544214515 | leaderboard, 2026-11-02 |
| puzzles still at grid | 564 → 9.3996 | `attack_surface.py` |
| …of which provably locked | 91 → 1.1567 | `k²`, `k²−1`, `k²−2` |
| …of which open | 473 → 8.2430 | |

Progress: **28.8042 → 22.2570**.

| move | gain |
|---|---:|
| published witnesses for `n ≤ 324` | 3.0346 |
| Goebel's centred block, `n > 324` | 1.2027 |
| L-lift closure | 1.4141 |
| Friedman's off-centre family and Göbel's diagonal strip, then lifted | 0.1640 |
| public packings, 614 puzzles (`merge_public.py`) | 0.7318 |

About 1,000 of 1,398 teams on the 2026-11-01 board sat between 22.18 and 22.72,
because public notebooks merge everyone's published packings. We now hold the
best public set: our own packings beat it nowhere, so every further gain has
to be a new record. #1 is about 0.2 ahead.

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
- [x] `make_submission.py` rebuilds everything in order. About 15 minutes on 8
      cores.
- [x] Own-work file uploaded: Kaggle 22.9888002452, local 22.9888002453.
- [x] Public packings merged (`merge_public.py`, sources in
      `best/provenance.json`): 22.2570079095, 0 rejected, confirmed on Kaggle.

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
deleting. Those need new packings; the remaining 0.2 gap to #1 lives there.

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

### Row-layout search falls 3–6 squares short

The 900+ packings are a grid plus two blocks of sheared rows in a pinwheel:
pitch `1/cos t` along a row, rows `cos t` apart, so `k` rows fill a strip of
height `H = k cos t + sin t`. `rows.py` builds that family from ~10 numbers
(the angle follows from `k` and `H`) and scans it. Measured 2026-11-02:

| n | fits at current L | needs |
|---|---:|---:|
| 920 | 914 | 920 |
| 930 | 924 | 930 |
| 984 | 979 | 984 |
| 994 | 991 | 994 |
| 998 | 995 | 998 |

The gap is the small filler squares at the ragged row ends. They cannot be
added afterwards: on `n = 994` only 2 points sit 1 from every centre, and
dropping 3 squares into the largest holes then relaxing at fixed `L` stalls
at penetration 0.04 (0.3 with rotation noise). Sheared rows are locked: a
row cannot slide without entering the next.

### Rounding the squares helps a little, not enough

`round_to_square.py` starts from random layouts of circles and turns them into
squares (rounded squares, corner radius 0.5 → 0) while the box shrinks, with an
optional pull toward one corner ("gravity") that fades with the radius. The
table gives the smallest leftover overlap over 32 random starts, before the
L-BFGS finish, with the box 0.04–0.08 above the record. Measured on CPU, 2026-11-02:

| n | target (record) | hard squares | rounded | rounded + gravity 0.05 | gravity 0.3 |
|---|---|---:|---:|---:|---:|
| 10 | 3.75 (3.7071) | 1.9e-4 | 1.3e-4 | 6.6e-6 | 9.0e-3 |
| 18 | 4.90 (4.8229) | 1.0e-3 | 1.2e-5 | 5.8e-7 | 2.8e-5 |
| 27 | 5.75 (5.7071) | 9.3e-3 | 9.0e-3 | 9.0e-3 | 8.9e-3 |

Rounding with weak gravity gives the best starts 10–1000× less overlap than
hard squares, and strong gravity jams. But no variant gets any start to zero,
even 1–2% above a record that is decades old. On 16 starts with the full
finish, `n = 10` first succeeds at `L = 3.8`, with 1 start out of 16 for both
hard and rounded squares. Random starts cannot reach the structured layouts
above `n ≈ 30`, so this can be used only as a loosening step on warm starts.

`--warm` tries that. It starts from the record in `best/`, rounds the corners
to `r0`, and shrinks the box from `L` to the target. On `n = 206` and `260`
(better records exist 2.6e-5 and 2.7e-4 below):

| test | result |
|---|---|
| target `L + 0.001`, no noise, hard squares | 0 / 16 |
| target `L + 0.001`, no noise, `r0 = 0.05` | 16 / 16, rounding beats the 97% shrink as a loosening |
| target `L + 0.001`, noise 0.002, `r0 = 0.05` | 0 / 16 |
| targets `L − 2e-5` and `L − 2e-4`, `r0` 0.02–0.2, noise 0–0.003 | 0 in every case |

Rounding lets a record that has been nudged settle back into itself, but not
into anything smaller. The better records for these `n` have different
layouts, which no smooth path from ours reaches.

### Free flips do not exist

A window flip (mirror or rotate everything inside a rectangle that no square
crosses) keeps the packing valid at the same `L` but changes contacts, so it
could unjam the LP at no cost. `flips.py` finds no clean window holding a
tilted square on `n = 376, 457, 930, 994`, even at 1e-3 tolerance or anchored
at the corners. The best window with 5+ tilted squares inside still cuts 7
squares (`n = 994`) or 10 (`n = 457`): the blocks interlock wall to wall.

Both results say the same thing: local or discrete edits to these layouts
have nowhere to go. A gain needs a whole new layout with fillers built in.

### Bands are stacks of separately rotated rows

On the Living Atlas, most records from `n ≈ 150` to 273 look like bent bands.
`atlas_families.py` labels every record in `best/`, and `bands.py` builds a
grid plus two mirrored bands of tilted rows. Measured 2026-11-02:

- **The gap is not in one family.** Against the 2026-11-01 per-puzzle table,
  the 0.2008 gap splits diamond 0.058, strip 0.054, pinwheel 0.059, multi
  0.027, grid 0.003, at about 5e-4 per puzzle over 400 puzzles. Records that
  sit above their neighbours (residual against `n ± 2` in the same `k` band)
  correlate with the gap (Spearman 0.42), but the 40 weakest are beaten no
  more often than the rest (73% vs 79%).
- **The bent band is two blocks placed diagonally, not two strips on the
  walls.** In `n = 240` a band of 9 rows of 3–6 squares runs from the left
  wall to the middle, its mirror in `y = x` runs on to the right wall
  (centres within 0.08 of the mirror image), and the grid fills the staircase
  on both sides. `rows.py` builds only thin strips on two walls.
- **No single-angle lattice reaches these records.** Each row in the band
  has its own angle (22.9, 20.2, 17.8, 17.9, 17.9, 19.2, 19.2, 18.7, 19.4
  degrees on `n = 240`), and the row starts do not follow one shear. At the
  record's `L` the counts are:

| n | L | `rows.py` | `bands.py`, 300 s |
|---|---:|---:|---:|
| 240 | 15.96969 | 235 | 233 |
| 273 | 16.98393 | 268 | 262 |
| 211 / 212 / 242 / 274 | `k − 0.001…0.01` | 206 / 206 / 237 / 268 | |

### Rigid-row bands: the fill is solved, the search is not

`rowband.py` makes every row a rigid bar with its own angle, length and
offset from the wall. Each row is pushed up until it touches the rows above
(exactly, through the Minkowski sum of two squares: checked against SAT on
2000 random pairs). The band is mirrored in `y = x`, then filled with axis
squares. Measured 2026-11-02:

- **The fill.** `rows.fill` is greedy, but an exact independent set over the
  four corner grids finds the same count, so the greedy pass was not the
  loss. What it lacked is squares on one grid line slid along it until they
  touch a band: `n = 240` has 6 of them, `n = 273` has 23. `fill_mis` adds
  these candidates and solves the set with HiGHS (0.5 s). From the records'
  tilted squares alone it rebuilds `n = 182`, 210 and 240 exactly and 272 of
  273. Most axis squares sit on the top-right grid (109 of 156 on `n = 240`)
  or the bottom-left grid (37).
- **The bands.** Rows read off the `n = 240` record and restacked land 0.08
  from the record's squares (median, 0.27 max), and that alone costs 18
  squares: 222 against 240. The rows are not quite rigid either: some end in
  a single filler square at another angle (27.3 and 6.5 degrees on `n = 240`).
  Climbing on the square count from the fit reaches 233, worse than
  `rows.py`.
- **The frontier.** Seeded from the next record down, at `L = k − 0.001`:

| n | seed | `rows.py` | `rowband.py`, 240 s |
|---|---|---:|---:|
| 274 | 273 | 268 | 271 |
| 242 | 240 | 237 | 236 |

Counting squares at a fixed `L` is a poor objective for jammed layouts: a
band 0.01 out of place costs whole rows of grid.

Scoring by `L` after polishing does not help either, because there is no
loose start. The `n = 240` rows, refitted, hold with the exact fill:

| L | 15.97 | 15.98 | 15.99 | 16.00 | 16.02 | 16.05 |
|---|---:|---:|---:|---:|---:|---:|
| squares | 222 | 224 | 226 | 229 | 233 | 235 |

A plain grid holds 256 at `L = 16`. The bands beat the grid only when they
are tight, so a build that fits `n` easily is a grid, and the contact LP
cannot shrink a grid. A band search has to start from a record's exact
squares, not from a fit.

### The record gap has no chain roots

Against `public/lb_table.json` (2026-11-01) we are behind on 417 puzzles for
0.2008 in total, ahead on none. The gap is spread thin (at most 0.0015 per
puzzle) and 80% of it sits at `n > 400`. Treating each record as a seed and
closing under lift and delete, 409 of the 417 are independent roots: the
records are not lifts of a few good packings. Almost all belong to one team
("Cats and boxes"), and similar puzzles have slightly different fractional
parts (.7939, .7941, .7938 at `n = 803, 544, 498`), so they look like
per-puzzle numerical optima, not exact constructions. Matching the best
single root (`n = 911`) is worth 0.0041 after lifting; the top 30 roots
together, 0.075.

Our weakest packings are the 45° diagonal strip at integer + 1/√2
(`n = 795, 852, 853, 911, 912, 973`, about 0.017 together). The pinwheel of
`rows.py` does not beat even those: just below our `L` it fits 908 of 911,
848 of 853, 790 of 795 and 968 of 973.

The crop rule (the reverse of lift, every subset size, now in
`lift_packings.py`) gains 1.9e-10 on `best/`, so `best/` is closed under it.

### Record sides carry no layout

`lb_table.json` gives each record's side to 50 digits, but no coordinates.
`decode_sides.py` tests whether the sides alone reveal how the records are
built. Measured 2026-11-02 on the 417 records that beat `best/`:

| test | result |
|---|---|
| same fractional part as another record (same gadget, bigger grid) | 32 of 417, in 13 groups, mostly lift chains |
| …and the group holds one of our packings, so it could be rebuilt | 1 group, worth 0.00021 |
| low-degree algebraic side (degree ≤ 4, small coefficients) | 13 of 417, all near-integer false hits; control: 23 of our 26 |
| digits past 1e-16 | rounding leftovers: 440 of 1000 sides are exactly a double |

Our packings are exact constructions and their sides are algebraic. The
records' sides are not, so the records are numerical optima, as the chain-root
test suggested. A side value says only where the frontier is, not how to
reach it.

---

## Next

1. ~~Upload the merged file~~ Done: Kaggle 22.2570079095, then 22.2569857321
   after the first `--refresh`. A local scheduled task re-runs
   `make_submission.py --refresh` every Monday and commits only gains.
2. ~~Polish the public packings~~ Done 2026-11-02 with `polish_best.py` (547 puzzles,
   20 s each): 6 improved, total gain 1.8e-8, 95% of it at `n = 916`. Score
   22.2570078917. They are effectively polished already; this lever is spent.
3. **New starting packings.** Make unjammed candidates for the polisher with a
   global search (L-BFGS on a penalty, on GPU as the public code does), or with
   new constructions. Row layouts without fillers and free flips are ruled out
   (see above). The remaining gap needs a per-puzzle global optimizer run
   from fresh starts, not edits to our layouts.
4. ~~Search seeds, ranked by chain value.~~ Done 2026-11-02: the record gap
   has no chain roots worth more than 0.004 each (see above).
5. **Attack the frontier** at `k² − (j_min − 1)`.
6. ~~Rigid-row band builder.~~ Built (`rowband.py`): the exact fill
   rebuilds records from their tilted squares, but searching the band rows
   on square count stops 3–7 short, and polishing from a looser `L` has no
   start to work from (see above). Left open: moving the record's own rows
   as rigid bodies at the frontier and refilling with `fill_mis`.
7. ~~Decode the record sides.~~ Done 2026-11-02 (`decode_sides.py`): the
   records are numerical optima, and their sides give no layout (see above).

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
