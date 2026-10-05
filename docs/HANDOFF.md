# Handoff notes

Update this file at the end of every working session: what changed, what was verified, what is next.

## Start-of-session checklist (for Claude)

1. Read `CLAUDE.md` (loaded automatically) and this file.
2. `pip install -r requirements.txt nbformat nbconvert ipykernel`, then `python tools/smoke_test.py`.
3. Check whether the robot is live: are `predictions_log.csv` and `scorecard.md` present, and (if this
   folder is a git clone) does `git log` show daily "Daily TSM call" commits? If the folder is not a
   clone, ask td for the GitHub URL and work in a fresh `git clone`, because the robot's outputs live
   only on GitHub. Read `scorecard.md` before discussing results.
4. Ask td about anything under "Open questions" that matters for the task at hand.

## How we got here

The project began in a claude.ai Project called "stock trend prediction" (2026-10-04/05, Asia/Taipei).
Its brief: *demonstrate how a machine-learning problem works, using Nasdaq data, predicting the market
trend of the next few days, as illustrative and real as possible.*

1. **Planning.** Claude proposed starting from a precise target rather than a model, plus a roadmap
   (data → exploration → features → baselines → models → walk-forward → backtest). td chose the target:
   *will TSM's close 5 trading days from now be higher than today's close?*
2. **Context from td.** It is for an **MIS class with an MBA audience**, demoed **within 75 minutes**;
   td will **run the model daily for a while and update the class about weekly**.
3. **Build.** Claude built `tsm_pipeline.py`, the generated notebook, `daily_predict.py`, the GitHub
   Actions workflow and the README, then tested everything offline on a synthetic stock (the build
   sandbox could not reach Yahoo Finance).
4. **Independent review.** A separate review agent checked for look-ahead and robustness. It confirmed
   the core design and found four real problems, all fixed: a damaged log could be silently wiped;
   a manual run during New York hours would lock in an unfinished price; the ADR premium mixed
   dividend-adjusted series; confidence ranges ignored overlapping labels. It also prompted the
   one-day trading delay in the backtest and range-pinned requirements.
5. **Handoff (this session).** Added `CLAUDE.md`, `.claude/rules/`, these docs, and moved the notebook
   builder and an offline test suite into `tools/`. A cold read of the docs by a separate agent found
   that the notebook said Taipei closes "about 12 hours" before New York opens; it is 8–9 hours (fixed
   in the notebook text, code comment and docs). It also led to stricter log loading: an empty or
   wrongly headed log now fails loudly too.

td received the repo as `tsm-trend.zip`, plus the notebook on its own.

6. **Session 2026-10-05 (Claude Code on td's Windows machine).** Inventory of the project. td
   decided: start the robot now, td demos and students only watch, English only, first class
   **Wednesday 2026-10-07**. td asked not to set up a local Python environment (demo goes straight
   to Colab), so the smoke test was not run. The placeholder repo URL was replaced with
   `tdgurupro-lgtm` in `tools/build_notebook.py`, `tools/smoke_test.py` and the notebook's
   `GITHUB_RAW` line (the same one-line substitution in builder and notebook; cell ids are
   positional, so this equals a rebuild, but `--check` has not been run). The folder became a git
   repo on branch `main`; creating the public GitHub repo and pushing is left to td, because
   publishing needs td's own approval. The repo lives on td's GitHub account `tdgurupro-lgtm`
   (logged in with `gh`, now the machine's active account; the older `davidkuo0720` login is kept
   but inactive). Commits in this folder are authored as `tdgurupro-lgtm <tdgurupro@gmail.com>`
   (repo-local git config; the machine-wide identity is unchanged).

## Current state

### Built
- `tsm_pipeline.py`: data, 18 features, target, two models, walk-forward, shuffled-split demo,
  backtest, 11 charts plus an HTML prediction card, live log and scorecard.
- `tsm_trend_demo.ipynb`: 39 cells, nine parts, 75-minute run-of-show at the top.
- `daily_predict.py` + `.github/workflows/daily.yml`: the robot (22:30 UTC Mon–Fri).
- `tools/build_notebook.py`, `tools/smoke_test.py`.

### Verified (offline, 2026-10-05)
- Whole notebook executes without errors or warnings on the synthetic stock (pandas 3.0.5,
  scikit-learn 1.9.1, numpy 2.5.3, matplotlib 3.11.2, yfinance 1.7.0 installed but mocked).
- The review agent also ran everything on pandas 2.2.3 / scikit-learn 1.6.1 (Colab's versions).
- Look-ahead perturbation tests, live-log scoring over simulated daily runs, re-run idempotency,
  damaged-log behaviour, Yahoo-shaped data handling (mocked), the CLI twice.
- The smoke test catches seven deliberately planted bugs (see `docs/DESIGN.md` §13).
- All charts were rendered and visually checked for overlaps and legibility.

### NOT yet verified
- **Any run on real Yahoo data.** Real numbers, real chart shapes and the leakage demo on real TSM are
  unseen. Some chart axis ranges (for example the accuracy bars starting at 35%) may need adjusting.
- **GitHub Actions** has never run the workflow (action versions `checkout@v6` / `setup-python@v6`
  exist as tags but are untested here; Yahoo may rate-limit Actions IPs).
- **Colab rendering:** collapsed `# @title` form cells, the HTML prediction card, and runtime on
  Colab's CPUs (expected about a minute).
- The partial-bar guard (needs a run during New York trading hours).
- `python tools/smoke_test.py --notebook` and `build_notebook.py --check` after the 2026-10-05
  repo-URL change (no local Python environment on td's machine). Run them when one exists.

### Reference numbers from the synthetic stock (NOT real results)
With `make_synthetic_panel()` ending 2026-10-05: walk-forward accuracy always up 54.3%, momentum 53.0%,
logistic 48.5%, boosting 48.5%; leakage demo 61.4% shuffled versus 44.7% time-ordered. The numbers
shift a little with the end date (the synthetic stock ends "today" by default). Useful only to
sanity-check that the code behaves; real TSM numbers will differ.

## Next steps (in order; first class is Wednesday 2026-10-07)

1. **td: create the repo and push** from this folder:
   `gh repo create tdgurupro-lgtm/tsm-trend --public --source . --remote origin --push`,
   then start the robot once: `gh workflow run daily.yml`. Check that `predictions_log.csv`,
   `scorecard.md`, `scorecard.png` and `data/prices.csv` appear. This is the **first run on real
   Yahoo data**: check the last date in `data/prices.csv` and the logged call.
2. **First notebook run in Colab** on real data:
   `https://colab.research.google.com/github/tdgurupro-lgtm/tsm-trend/blob/main/tsm_trend_demo.ipynb`.
   Review every chart and sentence against the real output; fix wording or axis ranges in the
   builder or `tsm_pipeline.py`, never in Colab. Do not tune the model to the results (D-03, D-11).
3. **Time a rehearsal** against the 75-minute run-of-show; trim if over.
4. **What the live log will hold on Wednesday:** calls for the closes of Fri 2026-10-02 (the manual
   first run, logged on Mon 10-05 before New York opened), Mon 10-05 and Tue 10-06. None scored
   yet, so Part 8 prints "No predictions have matured yet". That is expected; it is the moment to
   explain why a call needs 5 trading days. The 10-02 call is first scored by the Fri 10-09 run
   (Sat 06:30 Taipei).
5. Every week before class: open `scorecard.md` or rerun Part 8.

## Open questions for td

- What time is the class? From about 21:30 Taipei time (22:30 in the northern winter) New York is
  trading: the notebook then uses the previous close, which is correct but worth knowing.
- How long should the robot keep running ("for a while")? When should it be switched off?

Answered 2026-10-05: first class Wednesday 2026-10-07; repo `tdgurupro-lgtm/tsm-trend`; students
only watch td's demo; English only for all class materials.

## Ideas raised but not agreed (do not build without asking)

- A 3-class target with a ±1% "flat" band.
- Other horizons (1 day, 20 days) as a comparison.
- A slide deck or one-page handout for the class.
- Annotating the live scorecard with news events.

## Model change log

The live record is only meaningful for a fixed model. Record any change here with its date.

| Date | Change | Calls affected |
|---|---|---|
| (none yet) | Model v1: 18 features, logistic regression C=0.1, gradient boosting depth 3 | All calls so far |
