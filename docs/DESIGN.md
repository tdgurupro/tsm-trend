# Design: how the TSM demo works and why

This document explains every moving part and the reasoning behind it. `CLAUDE.md` has the short
rules; `docs/DECISIONS.md` has the alternatives that were rejected; `docs/HANDOFF.md` has status.

## 1. Purpose and constraints

- **Audience:** an MIS class of MBA students, mostly non-coders. td presents; students watch (and
  may run the Colab notebook themselves).
- **Format:** one 75-minute live demo, then a daily robot that keeps making real predictions, with
  a short update in class roughly weekly.
- **Goal:** show how a machine-learning problem really works, as "illustrative and real as
  possible" (the project brief). Honesty beats a flattering result. A model that fails to beat a
  simple baseline is a valid, even useful, outcome for the class.
- **Practical constraints:** free tools only (Yahoo Finance, Colab, GitHub Actions); the whole
  notebook should run in about a minute; nothing the class sees may depend on Claude being present.

## 2. System overview

```
                      Yahoo Finance (free, unofficial)
                                  │  6 daily series
                                  ▼
                        tsm_pipeline.py  ◄── single source of truth
                       ╱                ╲
     tools/build_notebook.py             daily_predict.py
     (code sections + teaching text)     (GitHub Actions, 22:30 UTC Mon–Fri)
                 │                                   │ commits to the repo
                 ▼                                   ▼
     tsm_trend_demo.ipynb                predictions_log.csv   scorecard.md/.png   data/prices.csv
     (class, in Colab) ◄──────── Part 8 reads the log; Part 2 can fall back to the snapshot
```

The same functions build features, train models and make calls in class and in the robot, so the
live track record belongs to exactly the model students saw.

## 3. Data

### Series and why each is there

| Name in code | Yahoo ticker | Why |
|---|---|---|
| `TSM` | `TSM` | The asset: TSMC's ADR on the NYSE. Its trading calendar is the spine of the dataset. |
| `TW2330` | `2330.TW` | TSMC's shares in Taipei. Enables the "two markets, one company" story and the ADR premium. |
| `SOXX` | `SOXX` | US semiconductor sector: is TSM moving with its industry? |
| `QQQ` | `QQQ` | Nasdaq-100: the broad tech market (the project brief mentions Nasdaq data; TSM itself is NYSE-listed). |
| `VIX` | `^VIX` | The market's "fear gauge". |
| `USDTWD` | `TWD=X` | Exchange rate, needed to compare the ADR with the Taiwan shares. |

History starts on 2010-01-01: about 16 years, enough for roughly 3 years of initial training plus
many test years spanning calm markets, crashes and the AI boom.

### Calendar alignment (the most leakage-prone step)

- Rows follow TSM's New York trading days. Other series are reindexed onto that calendar.
- **Taipei closes at 13:30 local time (05:30 UTC), 8–9 hours before New York opens on the same
  calendar date (13:30 or 14:30 UTC, depending on US daylight saving).** So a 2330.TW price dated *t* is known at New York's close on *t* and may be used for
  row *t*. Yahoo returns 2330.TW with an `Asia/Taipei` time zone; the code drops the time zone with
  `tz_localize(None)`, which keeps the local calendar date. `tz_convert` would shift dates by a day.
- Holidays differ between markets (Lunar New Year in Taipei, US holidays in New York). Gaps are
  filled **forward only** (`ffill`): a missing value takes the last known one, never a later one.
- Yahoo's FX daily bar can close after New York does, so features use **yesterday's** USD/TWD rate.
- A series that stops updating for more than 10 days prints a staleness warning.

### Raw versus adjusted prices

Yahoo is called with `auto_adjust=False`, which returns both the quoted `Close` and the
dividend-adjusted `Adj Close`.
- `*_Close` columns hold **adjusted** prices: correct for returns and the target, because a dividend
  payment is not a loss for the holder.
- `*_RawClose` columns hold **quoted** prices: correct for same-day ratios (ADR premium, intraday
  range) and for anything shown to people. Adjusted levels are rescaled by dividends paid *after*
  the date, which would distort a ratio between two differently adjusted series and smuggle in
  a little future information.

### Unfinished bars

During New York trading hours Yahoo includes today's incomplete bar. `download_prices` drops it
until 16:30 New York time, so a manual robot run (or an evening class in Taipei, which is daytime
in New York) never treats an intraday price as the close.

### Fallbacks

`load_panel(source, github_raw)` supports:
- `"yahoo"`: live download (default). If it fails and a repo URL is configured, it falls back to
  the snapshot automatically.
- `"snapshot"`: `data/prices.csv`, rewritten by the robot every morning: Plan B for class.
- `"synthetic"`: `make_synthetic_panel()`, a fake stock built from independent random daily moves
  (a random walk with a small upward drift), plus matching fake sector, market, VIX, FX and Taiwan
  series. Its future is unpredictable by construction. It powers the "coin-flip stock" sanity check
  in class and all offline testing.

## 4. The target

`target` = 1 if TSM's adjusted close 5 trading days later is higher than today's, else 0.
`future_return` is that 5-day return. These are the only columns that look forward.

- **Why binary:** every call is simply right or wrong, accuracy needs no explanation, and the call
  maps onto a business decision (hold TSM next week or not).
- **Why 5 days:** "the next few days" from the brief; long enough to matter, short enough to score
  every week in class.
- **Base rate:** a rising stock goes up in somewhat more than half of all weeks, so "always UP"
  scores above 50%. Models are compared with that, not with a coin flip.
- **Consequence of daily 5-day labels:** neighbouring days share 4 of the same 5 future days, so
  their labels agree most of the time (about 80% on the synthetic stock). This one fact drives the
  purge gap, the shuffled-split trap and the overlap-adjusted confidence ranges below.

The last `HORIZON` rows have no target yet: they are "the future" and are what the live call uses.

## 5. Features

18 features in six families, chosen because each is easy to explain to a business audience, not
because they were found to predict well. They were fixed before seeing any real results and must
not be tuned for performance (see `docs/DECISIONS.md`, D-09).

| Family | Features | Idea in class |
|---|---|---|
| Momentum | `ret_1d`, `ret_5d`, `ret_20d` | Does recent direction continue? |
| Trend | `gap_ma20`, `gap_ma50`, `rsi_14` | Is the price stretched above or below normal? |
| Risk | `volatility_20d`, `range_5d` | How bumpy has it been? |
| Attention | `volume_ratio` | Is unusual trading going on? |
| Sector & market | `soxx_ret_5d`, `qqq_ret_5d`, `rel_strength_20d`, `vix_level`, `vix_chg_5d` | Is it the stock, or the whole market? |
| Taiwan link | `tw_ret_1d`, `adr_premium`, `adr_premium_vs_60d`, `twd_chg_20d` | What did Taipei just do; is the ADR expensive versus Taiwan? |

`adr_premium` = raw ADR price / (5 × raw 2330 price / yesterday's USD-TWD) − 1. It is the most
distinctive, Taiwan-relevant signal and gets its own chart. `FEATURE_INFO` holds each feature's
family and plain-English meaning; the notebook's feature table and chart labels come from it.

## 6. Models

| Model | Settings | Why |
|---|---|---|
| Logistic regression | `StandardScaler` + `LogisticRegression(C=0.1)` | A "weighted checklist" students can read (weights chart). Strong regularisation because the signal is weak and noisy. |
| Gradient boosting | `HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50, l2_regularization=1.0)` | The powerful "black box" for the explainability discussion. scikit-learn's built-in version of the LightGBM-style algorithm: nothing extra to install in class. Shallow and regularised for the same noise reason. |
| Random forest (demo only) | 300 deep trees, `min_samples_leaf=1` | Used *only* in the leakage demo, because a flexible model memorises neighbouring days and makes the shuffled-split trap obvious. |

A call is UP when the predicted probability of UP is above 0.5. Hyperparameters were set once,
by judgement, and are not tuned: tuning on a noisy target would overfit and undercut the lesson.

## 7. Evaluation

### Baselines
- **Always up:** the base rate. The bar every model must clear.
- **Momentum:** call UP if the past 5 days were up. The simplest "smart-sounding" rule.

### The trap: shuffled split (deliberately wrong)
`split_test(data, model, shuffle=True)` holds out a random 25% of days. Because neighbouring days
share most of their future, the training set contains near-copies of each test day's answer.
`split_test(..., shuffle=False)` holds out the most recent 25% instead, with a 5-day gap.
On the synthetic random walk, the flexible forest scored **about 61% shuffled versus about 45% in
time order**: a model "predicting" coin flips is proof the test is broken. The class sees this on
real TSM and on the fake stock side by side. Manager's lesson: always ask *how was it tested?*

### Walk-forward (the honest test)
`walk_forward(data, model)`: expanding window. Train on everything before a block, predict the next
63 trading days (a quarter), roll forward, retrain. The first test starts after 750 labelled days
(about 3 years). The last `HORIZON` rows before each test block are dropped from training, because
their answers depend on prices inside the test block (a "purge gap"). Quarterly retraining keeps
the whole notebook to about a minute on Colab.

### Uncertainty
`wilson_interval(hits, n)` gives a 95% range for a hit rate, but with an effective sample size of
`n / HORIZON`, because overlapping daily calls are strongly correlated (an independent review found
consecutive hits correlated at about 0.6). Without this, the ranges would be roughly half as wide as
they should be. With 20 live calls, the honest range is very wide, which is itself a teaching point.

### Other views
- **Accuracy by year:** shows that results swing with market regimes.
- **Logistic weights:** standardised coefficients, blue pushes toward UP and red toward DOWN.

## 8. Backtest ("does it make money?")

`backtest(signal, daily_return)`:
- **Five sleeves:** each day's call controls 1/5 of the money for 5 days, so the holding period
  matches the 5-day prediction. Position = mean of the last 5 calls.
- **Execution:** a call made after the close on day *t* is traded at the close of *t+1*, so it
  earns the return from *t+1* to *t+2* onward (`daily_return.shift(-2)`). No instant trading at a
  price just observed.
- **Costs:** 0.10% times the change in position each day. Cash earns nothing.
- **Reported:** growth of $10,000, return per year, worst fall from a peak, share of time invested,
  against buy-and-hold (which has the same one-day delay).
- **Not modelled:** taxes, interest on cash, bid-ask spread beyond the flat cost, ADR fees. Fine for
  a classroom comparison; mention if students ask.

## 9. The live system (the daily robot)

### Schedule
`.github/workflows/daily.yml` runs at **22:30 UTC Monday to Friday** (06:30 Taipei, Tuesday to
Saturday). That is after the New York close in both summer time (20:00 UTC) and winter time
(21:00 UTC) with margin for Yahoo to settle. `workflow_dispatch` adds a manual "Run workflow"
button. The job installs `requirements.txt`, runs `python daily_predict.py`, and commits outputs
with the built-in `GITHUB_TOKEN` (`permissions: contents: write`).

### One run, step by step (`update_log`)
1. Download prices (dropping an unfinished bar) and save `data/prices.csv`.
2. **Score** every logged call whose 5 trading days have now passed: find its `as_of_date` in
   today's download, take the close 5 trading days later, fill `checked_on`, `actual_return_5d`,
   `actual` and the `hit_*` columns. Both prices come from the *same* download, so dividend
   adjustments cancel out.
3. Build the dataset, train both models on **all** history with a known answer, and predict the
   newest row.
4. If that close (`as_of_date`) is already logged (holiday, re-run), add nothing. Otherwise append
   one row. This makes the robot idempotent.
5. Write `scorecard.md` (latest call, accuracy with honest ranges, last 10 calls) and
   `scorecard.png` (running accuracy chart).

### Log schema (`predictions_log.csv`, one row per New York close)

| Column | Meaning |
|---|---|
| `as_of_date` | The close the call is based on (New York date). Unique. |
| `predicted_at_utc` | When the robot made the call. Proves it came before the outcome. |
| `tsm_close` | Raw quoted TSM close on `as_of_date` (what people see on Yahoo). |
| `prob_up_logistic`, `prob_up_boosting` | Each model's probability of UP. |
| `call_logistic`, `call_boosting`, `call_always_up` | UP or DOWN. |
| `check_on_approx` | Rough due date (5 business days later, ignores holidays). |
| `checked_on` | The actual trading day used for scoring. |
| `actual_return_5d`, `actual` | Realised 5-day return and direction. |
| `hit_logistic`, `hit_boosting`, `hit_always_up` | 1 if the call was right. |

### Why GitHub
- Free scheduling with no machine of td's left switched on.
- Every commit is a timestamped, public record made **before** outcomes are known: an audit trail
  students can inspect. That is an MIS lesson in itself.
- The repo is public so Colab can read the raw files without credentials. Nothing secret is stored.

### Failure handling
| What can go wrong | What happens |
|---|---|
| Yahoo rate-limits the cloud server | Up to 3 attempts per ticker with increasing waits; if all fail the run fails, GitHub emails td, who can press "Run workflow" later. A day never run simply has no call. |
| Run during New York trading hours | Today's unfinished bar is dropped; the call uses yesterday's close (or is a no-op if already logged). |
| Log file damaged (bad merge, manual edit, emptied, wrong header) | `load_log` raises; the run fails instead of overwriting the track record with an empty log. Only a log that does not exist yet starts fresh. |
| Workflow disabled by GitHub after long inactivity | Daily commits normally prevent this; re-enable from the Actions tab if GitHub emails. |
| A logged date vanishes from Yahoo's history | That row stays "pending" (rare; not handled further). |

## 10. Notebook generation

`tools/build_notebook.py` splits `tsm_pipeline.py` on its `# ==== SECTION: name ====` markers and
interleaves the code with the teaching text written in the builder.

| Section | Where it appears in the notebook |
|---|---|
| `settings` | Visible, Part 1 ("the knobs") |
| `data`, `evaluation`, `plotting`, `live` | One collapsed "Engine room" cell (Colab `# @title ... {display-mode: "form"}`) |
| `features` | Visible, Part 3 |
| `target` | Visible, Part 3, followed by building the dataset |
| `models` | Visible, Part 4 |
| `walkforward` | Visible, Part 4 (contains `walk_forward`, `make_flexible_model`, `split_test`) |

The engine-room cell runs right after the settings cell, so default arguments that reference
settings constants resolve; everything else is looked up at call time. Cell ids are fixed
(`cell-00` …) so rebuilds are byte-identical, and `--check` detects a stale notebook.

## 11. Charts

All charts are matplotlib (reliable in Colab and able to save PNGs headlessly for the robot). The
palette is the validated reference palette from the dataviz skill used during the build:
entity colours are fixed across every chart (logistic blue, boosting orange, momentum aqua,
baseline grey dashed, random forest violet), UP/DOWN uses the blue/red diverging pair, text uses
neutral inks, and there is never a second y-axis. Titles state the point; a grey subtitle says how
to read the chart; legends sit below or away from the data.

| Chart (function) | Teaching purpose |
|---|---|
| `plot_price` | Context: 16 years of TSM, log scale explained. |
| `plot_adr_premium` | The two-markets story; an unusual, Taiwan-relevant signal. |
| `plot_return_histogram` | The base rate: the score of "always UP". |
| `plot_noise_scatter` | "Is last week a clue for next week?" A shapeless cloud sets expectations. |
| `plot_leakage` | Shuffled vs time-ordered grading, real TSM and fake stock (hatched = wrong). |
| `plot_walk_forward_scheme` | Diagram of walk-forward rounds and the 5-day gap. |
| `plot_accuracy_bars` | Strategies vs the coin-flip line. |
| `plot_accuracy_by_year` | Regime dependence. |
| `plot_logistic_weights` | Explainability: what the simple model learned. |
| `plot_equity` | Accuracy is not profit: $10,000 paths after costs. |
| `show_prediction_card` | Today's live call, as an HTML card. |
| `plot_live_scorecard` | Running live accuracy; also saved as `scorecard.png` by the robot. |

## 12. Teaching design

| Time | Part | Learning goal | Key moment |
|---|---|---|---|
| 0–10 | 1. Business question | ML starts from a precise, scoreable question | Class poll: "what accuracy would be useful?" |
| 10–20 | 2. Data | Data supply chain; time zones | "One company, two clocks" |
| 20–30 | 3. Features and target | Turning prices into a table; the base rate | Noise scatter vs the poll |
| 30–40 | 4. Testing honestly | Baselines; leakage | The coin-flip stock "predicted" by a shuffled test |
| 40–55 | 5. Results | Compare with "always up"; regimes; explainability | Accuracy by year; weights |
| 55–65 | 6. Money | Accuracy is not profit; costs and risk | $10,000 chart |
| 65–75 | 7–9. Live call, scorecard, discussion | Deployment, monitoring, governance | Today's call that nobody can know yet |

The discussion questions (decision rights, data supply chain, monitoring with a pre-committed
switch-off rule, audit trail, explainability, competition eroding any edge) turn the technical demo
into MIS content. The weekly update reuses Part 8: are we above "always up", is the range still too
wide, did news explain a run of misses?

Markdown never states specific result numbers: the text must remain true whatever the real data
shows. Charts compute their own numbers.

## 13. Testing

`tools/smoke_test.py` runs offline in about 20 seconds (`--notebook` adds a full notebook execution):

| Check | Guards against |
|---|---|
| `features_and_target_use_only_the_past` | Scrambles every price after a date (and the FX rate *on* that date); features and targets up to that date must not change. |
| `walk_forward_uses_only_the_past` | Same perturbation, cut 2 days into a test block; walk-forward probabilities up to the cut must not change (catches a missing purge gap). |
| `backtest_trades_at_the_next_close` | The return credited to day *t* must be day *t+2*'s. |
| `shuffled_test_is_fooled_by_a_random_walk` | Keeps the leakage demo dramatic (shuffled > 56% and at least 5 points above time order). |
| `live_log_scores_the_right_day_and_never_duplicates` | 27 simulated robot runs including a re-run; every score checked independently. |
| `damaged_log_fails_loudly` | Merge-conflict, empty and wrongly headed logs must raise; a missing one must start fresh. |
| `yahoo_shaped_data_is_aligned_correctly` | Mocked Yahoo data with MultiIndex columns, Taipei time zone and holidays on both sides. |
| `daily_script_runs_twice_without_duplicating` | The CLI end to end, twice. |
| `notebook_is_in_sync_with_the_code` | The committed notebook equals a fresh build (SKIP if nbformat is missing). |

The suite was mutation-checked: seven deliberately planted bugs (no FX lag, no purge gap, trading
at the same close, back-filling Taiwan holidays, swallowing log errors, scoring the wrong day, a
centred moving average) were each caught.

## 14. Known limitations

- Never run on real Yahoo data or real GitHub Actions yet (see `docs/HANDOFF.md`).
- yfinance is unofficial; Yahoo can change formats or block cloud IPs without notice.
- The backtest ignores taxes, cash interest and ADR fees.
- `check_on_approx` ignores holidays (display only; scoring uses the real calendar).
- The leakage demo's exact percentages depend on the data; the smoke test only guarantees the gap
  on the synthetic stock.
