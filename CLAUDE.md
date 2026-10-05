# TSM 5-day trend demo

A teaching project, not a trading system. td (based in Taiwan, Asia/Taipei time) runs it as a
**75-minute live demo in an MIS class for MBA students** (mostly non-coders), in Google Colab,
then follows a **live daily track record** with the class roughly once a week.

**The question:** at today's New York close, will the TSM ADR close higher 5 trading days later?
Binary UP / DOWN classification.

**The point is the method, not beating the market.** On real data the models are expected to land
near the "always say UP" baseline. That honest result *is* the lesson: precise problem framing,
leakage, walk-forward testing, accuracy is not profit, monitoring and governance. Never tune
features or parameters to make the backtest look better.

## Status (last updated 2026-10-05)

- Built and tested **offline only**. The first build session had no network access to Yahoo
  Finance, so nothing has run on real TSM prices yet. The first real run happens in Colab or
  GitHub Actions on td's side; check its output before trusting any chart text about results.
- Repo: `https://github.com/tdgurupro/tsm-trend` (public). `GITHUB_RAW` in the notebook points
  at it (set in `tools/build_notebook.py`). td creates the repo and starts the robot on
  2026-10-05; check `git log` for "Daily TSM call" commits before assuming it is live.
- Work in a `git clone` of that repo (`C:\Users\David\Workspace\tsm-trend` is one once pushed):
  the robot commits the live log there daily, so `git pull` before changing anything.
- **First class demo: Wednesday 2026-10-07.** td runs the notebook in Colab; students only watch.
  All class materials in English. Open items and history: `docs/HANDOFF.md`.

## Files

| Path | Role |
|---|---|
| `tsm_pipeline.py` | The engine and single source of truth: data, features, target, models, testing, backtest, charts, live log. |
| `daily_predict.py` | The daily robot's entry point (thin CLI over `tsm_pipeline.py`). |
| `.github/workflows/daily.yml` | Runs the robot 22:30 UTC Mon–Fri (06:30 Taipei) and commits its outputs. |
| `tsm_trend_demo.ipynb` | Class notebook. **Generated file**, see rule 3. |
| `tools/build_notebook.py` | Generates the notebook from `tsm_pipeline.py` sections plus the teaching text it contains. |
| `tools/smoke_test.py` | Offline tests: look-ahead checks, live-log checks, plumbing, notebook sync. |
| `predictions_log.csv`, `scorecard.md`, `scorecard.png`, `data/prices.csv` | Written by the robot in the repo. Never edit by hand. |
| `README.md` | User-facing setup and class routine for td. |
| `.claude/rules/` | Checklists that load only when you touch the pipeline/robot or the notebook. |
| `docs/` | Design rationale, decision log, handoff notes (see below). |

## Commands (run from the repo root)

```bash
pip install -r requirements.txt nbformat nbconvert ipykernel   # runtime + notebook tooling
python tools/smoke_test.py               # offline checks, ~20 s; run after ANY code change
python tools/smoke_test.py --notebook    # also executes the whole notebook offline, ~30 s more
python tools/build_notebook.py           # regenerate the notebook after changing code or teaching text
python tools/build_notebook.py --check   # fails if the committed notebook is out of date
python daily_predict.py --source synthetic --out /tmp/demo   # dry-run the robot without internet
python daily_predict.py --out /tmp/real                      # real data, if this machine can reach Yahoo
```

## Rules that must not break

1. **No look-ahead.** Row *t* may use only information known at the New York close of day *t*:
   - Taiwan prices dated *t* are fine (Taipei closes 8–9 h before New York opens); never *t+1*.
   - Gaps across holidays are filled **forward only**.
   - The USD/TWD rate is lagged one day (Yahoo's FX bar can close after New York).
   - The target (`future_return`, `target`) is the only forward-looking column.
   - Walk-forward leaves a `HORIZON`-row gap between training and test blocks.
   - The backtest trades at the **next** close (`daily_return.shift(-2)`).
   Every new feature must pass `features_and_target_use_only_the_past` in the smoke test.
2. **Never shuffle time series for evaluation.** The only shuffled split is the deliberate
   "wrong way" demo, `split_test(..., shuffle=True)`.
3. **The notebook is generated. Never hand-edit `tsm_trend_demo.ipynb`.** Code goes in
   `tsm_pipeline.py`; teaching text and cell order go in `tools/build_notebook.py`. Rebuild, run
   the smoke test with `--notebook`, and commit (or upload) the code and the notebook together.
4. **Section markers** (`# ==== SECTION: name ====`) in `tsm_pipeline.py` decide which notebook
   cell each piece of code lands in. The builder requires exactly these nine, in order: settings,
   data, features, target, models, walkforward, evaluation, plotting, live.
5. **The live log is the audit trail.** It is append-only: never rewrite, delete or backfill past
   calls. Never run `daily_predict.py` locally with its default `--out .`, because the robot owns
   the repo's log and outputs. Keep `LOG_COLUMNS` stable (add new columns only at the end). A
   log that is empty, unreadable or wrongly headed must fail loudly (only a log that does not exist
   yet starts fresh). If the model changes
   mid-semester, record the date in `docs/HANDOFF.md` (and tell the class), because calls before
   and after come from different models.
6. **Two kinds of price.** Returns and the target use dividend-adjusted closes (`*_Close`).
   Same-day ratios (ADR premium, intraday range) and any price shown to people use raw quoted
   closes (`*_RawClose`).
7. **Honest uncertainty.** `wilson_interval` divides the number of calls by `HORIZON`, because
   daily 5-day calls overlap. Do not remove this.
8. **Run `python tools/smoke_test.py` after every change**, plus `--notebook` when notebook text,
   charts or anything the notebook calls has changed.

## Conventions

- **Audience first.** Notebook text, chart titles and printed messages are plain English for MBA
  students. Explain any technical term the first time it appears. A chart title states the point;
  the subtitle says how to read the chart.
- **Chart colours follow the entity in every chart:** logistic regression blue `#2a78d6` (single-series
  TSM charts also use it),
  gradient boosting orange `#eb6834`, momentum aqua `#1baf7a`, always-up / buy-and-hold grey
  `#8a8984` (dashed), flexible random forest violet `#4a3aa7`. UP/DOWN polarity uses blue
  `#2a78d6` / red `#e34948`. One y-axis per chart, legends below or out of the data.
- **Small dependency set**: yfinance, pandas, numpy, scikit-learn, matplotlib. Code must work on
  Colab's defaults (pandas 2.2, scikit-learn 1.6) and on pandas 3 (what Actions installs). Actions
  uses Python 3.12; the offline checks were last run on Python 3.13.
- Colab collapses plumbing cells that start with `# @title ... { display-mode: "form" }`.
- Prefer showing the real, possibly unflattering result over a polished one.

## Deeper docs (read when relevant)

- `docs/DESIGN.md`: architecture and why each piece works the way it does (data alignment,
  features, target, models, evaluation, backtest, live log, charts, teaching flow). Read before
  changing modelling, evaluation or the robot.
- `docs/DECISIONS.md`: numbered decision log with the alternatives that were rejected. Read before
  reversing an earlier choice.
- `docs/HANDOFF.md`: how the project got here, what is verified and what is not, next steps and
  open questions. Update it at the end of each working session.
- `README.md`: td's setup steps (GitHub, Colab) and weekly class routine.
