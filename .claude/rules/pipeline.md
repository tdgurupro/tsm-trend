---
paths:
  - "tsm_pipeline.py"
  - "daily_predict.py"
  - ".github/workflows/*.yml"
---

# Changing the engine or the daily robot

## Where your code ends up
Each `# ==== SECTION: name ====` block in `tsm_pipeline.py` becomes notebook cells (see `tools/build_notebook.py`).
- **Visible to students:** settings, features, target, models, walkforward. Keep these short, linear and
  commented in plain English. No clever one-liners; students read them on a projector.
- **Collapsed "engine room":** data, evaluation, plotting, live. Can be denser, still commented.
- Functions in collapsed sections are defined before the visible ones run, but default arguments are
  evaluated at definition time, so constants used as defaults must live in `settings`.

## Adding or changing a feature
1. Use only rows dated on or before *t*: no `shift(-k)`, no `rolling(..., center=True)`, no `bfill`,
   no statistics computed over the whole series (a full-sample mean or z-score leaks the future).
2. Returns from `*_Close` (dividend-adjusted); same-day ratios from `*_RawClose`.
3. Add it to `FEATURE_INFO` with a family and a plain-English meaning: that drives the feature
   table and chart labels in the notebook.
4. `python tools/smoke_test.py`, then `python tools/build_notebook.py`.

## Models, evaluation, backtest
- Model display names ("Logistic regression", "Gradient boosting") appear in many places (dict keys,
  hard-coded lists, chart labels, the builder's text). Before renaming, run
  `grep -rn "Gradient boosting" --include=*.py --include=*.md .` and change every hit.
- Adding a model changes the live log: append new `prob_up_*`, `call_*`, `hit_*` columns at the END
  of `LOG_COLUMNS`, extend `score_log`, `scorecard_table`, `write_scorecard` and the notebook. Changing
  models mid-semester breaks comparability of the live record: log the date in `docs/HANDOFF.md`.
- Keep: the `HORIZON` gap in `walk_forward` and in the time-ordered `split_test`; `shift(-2)` in
  `backtest`; the overlap adjustment in `wilson_interval`.
- Notebook runtime budget: the whole notebook should run in about a minute on Colab's 2 CPUs.
  That is why the walk-forward retrains quarterly (`RETRAIN_EVERY = 63`).

## The robot and its data
- One call per New York close (`as_of_date`); re-runs and holidays must stay no-ops.
- `download_prices` drops today's unfinished bar during New York trading hours; keep that guard.
- `load_log` may only treat a log that does not exist yet as empty. Empty files, parse errors and
  missing core columns (`REQUIRED_LOG_COLUMNS`) must raise.
- Yahoo quirks: MultiIndex columns; 2330.TW arrives tz-aware in Asia/Taipei, so use
  `tz_localize(None)` (keeps the local date), never `tz_convert`; `auto_adjust=False` gives both
  `Close` and `Adj Close`; cloud IPs get rate-limited, hence retries.
- The workflow commits `predictions_log.csv`, `scorecard.md`, `scorecard.png`, `data/prices.csv`.
  Before renaming any of them, `grep -rn "<old name>" .` and update every hit (workflow `git add`
  line, `daily_predict.py`, `write_scorecard`, notebook paths, smoke test, README, CLAUDE.md).
