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
   `tdgurupro` in `tools/build_notebook.py`, `tools/smoke_test.py` and the notebook's
   `GITHUB_RAW` line (the same one-line substitution in builder and notebook; cell ids are
   positional, so this equals a rebuild, but `--check` has not been run). The folder became a git
   repo on branch `main`; creating the public GitHub repo and pushing is left to td, because
   publishing needs td's own approval. The repo lives on td's GitHub account `tdgurupro`
   (logged in with `gh`, now the machine's active account; the older `davidkuo0720` login is kept
   but inactive). Commits in this folder are authored as `tdgurupro <tdgurupro@gmail.com>`
   (repo-local git config; the machine-wide identity is unchanged). td created the repo and
   started the first robot run as `tdgurupro-lgtm`, then renamed that account to `tdgurupro` the
   same day (account id 324321998), and every URL was updated. At td's request the git history
   was then rewritten once (2026-10-05, about 05:00 UTC, before anyone outside had seen the repo)
   so the two early commits carry the author `tdgurupro` instead of `tdgurupro-lgtm`. This
   changed the hash of the robot's first commit ("Daily TSM call 2026-10-05"), not its content.
   **Never rewrite history again**: the commits are the live record's audit trail (D-17, D-19).
7. **Same session: first notebook run on real data**, in Colab through td's Chrome (Colab had
   scikit-learn 1.6.1, pandas 2.2.3, numpy 2.1.3). It ran without errors. Findings and fixes:
   impossible Yahoo FX rates (D-27, which makes the model v1.1); the Part 7 card disagreeing with the
   robot's logged boosting call for the same close (D-28, explained in the notebook); and cosmetics
   (the price chart labelled only $10 and $100, the feature table cutting text short, the accuracy
   bars without a subtitle and with a label crossing the 50% line). td then approved a project-only
   `.venv` (gitignored) so the smoke test can run locally. `pip` stalled for 30+ minutes: td's ISP
   (HiNet) routes PyPI's CDN (Fastly) via NTT to an overseas server (about 85 ms, 65–450 KB/s,
   IPv6 not working), while conda-forge is served by Cloudflare in Taipei (7 ms, about 6.5 MB/s).
   So `.venv` is a conda environment built with
   `C:\Users\David\miniforge3\Scripts\mamba.exe create -p ./.venv -c conda-forge python=3.12 ...`
   (the packages in `requirements.txt` plus nbformat, nbconvert, ipykernel); run
   `.venv/python.exe` (with the PATH line from `CLAUDE.md`). Running on Windows for the first time
   also exposed two Windows-only bugs, both fixed: the notebook builder wrote the notebook in the
   locale encoding (cp950 on td's machine) instead of UTF-8, which Colab cannot read; and the
   smoke test pasted a backslash Windows path into a Python string. td re-logged in to `gh` as `tdgurupro`
   and plans to make `davidkuo0720` the machine's default again, so other projects are unaffected;
   from then on push from this folder with `GH_TOKEN=$(gh auth token --user tdgurupro) git push`.

## Current state

### Built
- `tsm_pipeline.py`: data, 18 features, target, two models, walk-forward, shuffled-split demo,
  backtest, 11 charts plus an HTML prediction card, live log and scorecard.
- `tsm_trend_demo.ipynb`: 40 cells, nine parts, 75-minute run-of-show at the top.
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

### Verified live (2026-10-05)
- **First robot run on GitHub Actions on real Yahoo data**, started by hand (run 37265051979, 44 s,
  Python 3.12.14). The download worked from Actions; `data/prices.csv` has 4,213 trading days from
  2010-01-04 to 2026-10-02 with no empty cells in recent rows. First live call, for the close of
  Fri 2026-10-02 (TSM $472.78), logged Mon 2026-10-05 04:48 UTC before New York opened:
  logistic UP (0.547), boosting DOWN (0.4961). The bot committed all four outputs.
- Watch: GitHub warned that `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19. Check the first
  run after that date.
- **Whole notebook in Colab on real data (model v1, before the FX fix):** about 1.5 minutes, no
  errors; collapsed form cells and the HTML prediction card render. Real numbers, data through
  2026-10-02: base rate 55.6% UP weeks. Walk-forward over 3,398 calls: always up 56.0%, logistic
  52.7%, boosting 50.5%, momentum 49.2%. Leakage demo: real TSM 64.3% shuffled vs 50.6% time order;
  fake stock 61.6% vs 44.8%. $10,000 from 2013: buy and hold $387,340, logistic $116,820, boosting
  $44,093. The honest "models do not beat always up" result the class is built around.

- **Model v1.1 verified locally on 2026-10-05** (conda `.venv`: pandas 2.3.2, scikit-learn 1.9.1,
  numpy 2.2.6, matplotlib 3.11.2, yfinance 1.7.0): `smoke_test.py --notebook` 11/11 passed;
  `drop_impossible_fx` on the real history drops exactly 2011-10-25 and 2014-12-31 and keeps the
  other 4,211 rates (27.4 to 33.7); a real-data robot dry run into a scratch folder succeeded.

### NOT yet verified
- **The notebook in Colab with model v1.1** (after the FX fix and chart changes). Rerun it there
  before class.
- **Scheduled runs** (the 22:30 UTC cron) and scoring of a matured call (first one: the 10-09 run).
- The partial-bar guard (needs a run during New York trading hours).

### Reference numbers from the synthetic stock (NOT real results)
With `make_synthetic_panel()` ending 2026-10-05: walk-forward accuracy always up 54.3%, momentum 53.0%,
logistic 48.5%, boosting 48.5%; leakage demo 61.4% shuffled versus 44.7% time-ordered. The numbers
shift a little with the end date (the synthetic stock ends "today" by default). Useful only to
sanity-check that the code behaves; real TSM numbers will differ.

## Next steps (in order; first class is Wednesday 2026-10-07)

1. ~~td: create the repo and push, start the robot once~~ Done 2026-10-05 (see "Verified live").
2. ~~First notebook run in Colab~~ Done 2026-10-05 (session item 7). **Rerun it after the v1.1
   push** and check the FX message under Part 2, the ADR premium chart (no -90% spikes), the price
   chart's axis, the feature table and the accuracy bars:
   `https://colab.research.google.com/github/tdgurupro/tsm-trend/blob/main/tsm_trend_demo.ipynb`.
   Fix wording or axis ranges in the builder or `tsm_pipeline.py`, never in Colab. Do not tune the
   model to the results (D-03, D-11).
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

Answered 2026-10-05: first class Wednesday 2026-10-07; repo `tdgurupro/tsm-trend`; students
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
| 2026-10-04 | Model v1: 18 features, logistic regression C=0.1, gradient boosting depth 3 | The call for the close of 2026-10-02 |
| 2026-10-05 | Model v1.1: impossible USD/TWD rates ignored (D-27); features, models and settings unchanged | Calls from the close of 2026-10-05 on (first robot run after the push) |
