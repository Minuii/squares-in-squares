# Squares in Squares

Packing `n` unit squares into the smallest square, for every `n` from 1 to 1000,
for the Kaggle competition
[Squares in Squares](https://www.kaggle.com/competitions/squares-in-squares).

Each puzzle scores `L/√n − 1`, where `L` is the side of the tightest
axis-aligned square around the packing. The leaderboard is the sum over all
1000 puzzles, and lower is better.

**Current score: 23.1527917816**, measured locally. All 1000 puzzles pass a
check built from the metric's own rules. The file has not been uploaded to
Kaggle yet.

| reference (2026-11-02) | score |
|---|---:|
| all-grid baseline | 28.9377 |
| this repository | 23.1528 |
| best merge of public packings | 22.2591 |
| #1 on the leaderboard | 22.0544 |

## How the score is built

| step | script | gain |
|---|---|---:|
| Published best-known packings for `n ≤ 324` | `witness_to_packing.py` | 3.0346 |
| Goebel's centred diagonal block for `n > 324` | `gobel_packings.py` | 1.2027 |
| L-lift and delete closure | `lift_packings.py` | 1.4141 |

The L-lift adds an L-shaped strip of `2⌊L⌋ + 1` unit squares to a packing of
side `L`:

```
s(n + 2⌊s(n)⌋ + 1) ≤ s(n) + 1
```

## Passing the grader

The grader is much stricter than a double-precision overlap test, and a rejected
puzzle fails quietly by scoring as the plain grid. Three things matter:

- Pairs near contact are certified with interval arithmetic up to 500 digits. An
  overlap of 1e-16 is rejected.
- Squares touching exactly at non-dyadic coordinates cannot be certified and are
  rejected too.
- Kaggle reads coordinates as doubles, so certify the doubles, not the text.

`merge_best.py` opens every contact with a 1e-12 expansion, which costs about
1e-9 of score, and `grader_check.py` then applies the metric's rules to the
coordinates as written.

## Running it

Needs 64-bit Python 3.14.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python fetch_witnesses.py
.venv/Scripts/python make_submission.py
```

`make_submission.py` takes about 30 minutes on 8 cores. It writes
`submission_final.csv`, and `best/` only ever improves. On Linux or macOS use
`.venv/bin/python`.

## Layout

| path | contents |
|---|---|
| `best/` | best packing found for each `n` |
| `submission_final.csv` | the current submission |
| `make_submission.py` | the whole pipeline, in order |
| `grader_check.py` | the submission gate |
| `squares_core.py` | geometry, validators, submission I/O |
| `plan.md` | findings, status and next steps |
| `description.md` | the problem, the metric and the known results |
| `packing_unit_squares.ipynb`, `visual_tour.ipynb` | executed notebooks |
| `figures/` | generated images |

## Next steps

- Build a contact-graph LP polisher.
- Search for better seeds, ranked by how far an improvement lifts.
- Attack the puzzles just past the sub-grid frontier.

Details are in [`plan.md`](plan.md).

## Credits and licence

Code here is under the Apache License 2.0, see [`LICENSE`](LICENSE).

- **Published packings.** The `n ≤ 324` packings in `best/`, and the lifted
  packings derived from them, come from
  [The Squares Project](https://github.com/jlevy/squares) and are used under
  CC BY 4.0. Coordinates were normalised and expanded slightly.
- **Grader logic.** `grader_check.py` follows Kaggle's
  [metric notebook](https://www.kaggle.com/code/metric/squares-in-squares),
  Apache 2.0.
- **Mathematics.** E. Friedman, *Packing Unit Squares in Squares*, Electronic
  Journal of Combinatorics, Dynamic Survey DS7. The block family is due to
  F. Göbel.
