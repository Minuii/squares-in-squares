# Progress

One line per working session, newest last. Details and measurements live in
[plan.md](plan.md); this file is only the timeline. Lower score is better.

| date | score | what happened |
|---|---|---|
| 2026-10-21 | 28.9377 | Start. All-grid baseline. |
| 2026-10-21 → 11-01 | 23.1528 | Published witnesses for `n ≤ 324` (−3.03), Göbel's centred block above 324 (−1.20), L-lift closure (−1.41). Built before the repository existed; first commit `3de3699`. |
| 2026-11-02 | 22.9888 | Friedman's off-centre family and Göbel's diagonal strip, lifted to 97 puzzles. Kaggle confirmed 22.9888002452 (own work only). |
| 2026-11-02 | 22.2570 | Merged 614 public packings from the Living Atlas output. Kaggle confirmed 22.2570079095. |
| 2026-11-02 | 22.2570 | Contact-LP polish over `best/`: 6 puzzles, gain 1.8e-8. Penalty search tried, finds nothing. |
| 2026-11-02 | 22.25699 | `make_submission.py --refresh` pulled 36 newer public packings. Kaggle confirmed 22.2569857321. |
| 2026-11-02 | 22.25699 | Dead ends, all recorded in plan.md: row-layout search (`rows.py`, 3–6 squares short), window flips (`flips.py`, no clean windows), crop rule (gain 1.9e-10), chain roots (409 of 417 record gaps are independent). Weekly refresh scheduled for Mondays. |

## Where it stands

- Gap to the sum of per-puzzle records: 0.2008 over 417 puzzles, 80% at `n > 400`.
- #1 team: 22.0544 (2026-11-02).
- Ruled out on our packings: polishing, kicks, penalty search from jittered
  starts, row layouts without fillers, free flips, lift/delete/crop closure.
- Open: a per-puzzle global optimizer from fresh starts; whether public
  packings count for prizes (C.14(a)).
