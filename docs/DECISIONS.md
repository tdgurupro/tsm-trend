# Decision log

Each entry: what was decided, why, and what was rejected. Read the relevant entry before reversing
a choice; add a new entry (do not rewrite old ones) when a decision changes.
All decisions so far were made on 2026-10-04/05 while building the project with td.
"td decided" marks a choice td made; everything else was proposed by Claude and accepted as part of
the build.

## Framing

**D-01. Binary 5-day direction as the target** (td decided).
"At today's close, will TSM close higher 5 trading days from now?"
- Why: easy to explain and score, a coin-flip reference point, maps to a hold/not-hold decision.
- Rejected: regressing the price (hard to grade for non-specialists, invites misleading error
  metrics); 3 classes with a ±1% "flat" band (kept as a possible extension, not built).

**D-02. A 75-minute MIS class demo for MBA students, plus daily live runs with weekly updates** (td decided).
- Consequences: plain-English notebook, collapsed plumbing, a timed run-of-show, an automated
  daily robot and a weekly scorecard.

**D-03. Expect and show an honest, probably unimpressive result.**
- Why: markets are close to unpredictable over days; the lesson is method and judgement.
  The notebook never states result numbers in prose, so it stays true whatever the data says.
- Rejected: tuning features or hyperparameters until the backtest looks good (that is the
  overfitting the class is warned about).

## Data

**D-04. TSM ADR as the asset, Nasdaq-100 (QQQ) as market context.**
- Why: TSMC is Taiwan's flagship company and trades in two markets, which makes a rich and local
  story. The brief mentioned "Nasdaq data", but TSM is NYSE-listed; QQQ supplies the Nasdaq angle.

**D-05. Yahoo Finance through yfinance.**
- Why: free, no account, works in Colab and GitHub Actions.
- Rejected: paid feeds (cost, keys). Accepted risk: unofficial and occasionally blocked; mitigated
  by retries, the daily snapshot fallback and discussing it in class ("data supply chain").

**D-06. Six series: TSM, 2330.TW, SOXX, QQQ, ^VIX, TWD=X; history from 2010.**
- Why: each supports one idea in class (stock, Taiwan link, sector, market, fear, currency).
  2010 gives about 16 years: 3 for initial training and many test years across regimes.

**D-07. Same-day Taiwan data is allowed; the FX rate is lagged one day; gaps are filled forward only.**
- Why: Taipei closes 8–9 hours before New York opens, so 2330.TW dated *t* is known at New York's
  close *t*. Yahoo's FX bar may close after New York, so it is lagged to stay safe.

**D-08. Use raw quoted prices for same-day ratios and display; adjusted prices for returns.**
- Why (found by the independent review): dividend-adjusted levels are rescaled by dividends paid
  later, which distorts the ADR premium and leaks a little future information. Download now uses
  `auto_adjust=False` to get both.

## Features and models

**D-09. Eighteen classic, explainable features in six families, fixed up front.**
- Why: each can be explained to MBA students in one sentence; fixing them before seeing results
  avoids data snooping.
- Rejected: large automated feature sets, news/sentiment data (more moving parts, harder to
  explain, paid data).

**D-10. Logistic regression plus gradient boosting, both strongly regularised.**
- Why: an explainable "weighted checklist" versus a powerful "black box" sets up the explainability
  discussion. scikit-learn's `HistGradientBoostingClassifier` was used instead of LightGBM (the
  first plan mentioned LightGBM): same algorithm family, nothing extra to install in class.
- Rejected: deep learning or an LSTM (slow in Colab, adds nothing to the lesson; "fancier is not
  better" can be made verbally).

**D-11. Hyperparameters set once by judgement, never tuned.**
- Why: on a target this noisy, tuning mostly fits noise, and walk-forward tuning would make the
  notebook too slow for class.

## Evaluation

**D-12. Walk-forward with an expanding window, quarterly retraining and a 5-day purge gap.**
- Why: mirrors real use (only the past is available). Quarterly retraining keeps the notebook to
  about a minute in Colab. The gap removes training answers that overlap the test block.

**D-13. A random forest is used only for the shuffled-split demonstration.**
- Why: with the regularised boosting model the shuffled split reached only about 55% on the
  synthetic stock (versus 46% time-ordered), roughly the "always up" rate, so the trap did not look
  dramatic. A deep random forest
  memorises neighbouring days: about 61% shuffled versus 45% time-ordered on a pure random walk.
  Showing it on real TSM and on the fake stock side by side is the clearest leakage lesson.

**D-14. Baselines are "always up" and "momentum"; models are compared with "always up", not 50%.**

**D-15. Confidence ranges use an effective sample size of n / 5** (from the independent review).
- Why: overlapping 5-day labels make consecutive hits correlated (about 0.6), so the plain Wilson
  interval was about half as wide as it should be.

**D-16. Backtest: five overlapping sleeves, trade at the next close, 0.10% per change in position.**
- Why: sleeves match the 5-day horizon; next-close execution avoids trading at a price only just
  observed (tightened after the independent review); a flat cost keeps the arithmetic explainable.

## The live system

**D-17. The daily robot runs on GitHub Actions.**
- Why: free, needs no computer of td's left on, and each commit is a public timestamped audit trail,
  which is MIS content in itself.
- Rejected: a Claude scheduled task (the build environment could not reach Yahoo Finance); td
  running Colab by hand every day (easy to forget, no audit trail); a cron job on td's computer
  (must stay on).

**D-18. Schedule 22:30 UTC Monday–Friday (06:30 Taipei).**
- Why: after the New York close in both summer and winter time, with margin for data to settle.

**D-19. The log is append-only, idempotent per close, and scored from a single download.**
- Why: an audit trail must never be rewritten; re-runs and holidays must be harmless; taking both
  prices from the same download cancels dividend adjustments.
- Plus (from the reviews): a damaged, empty or wrongly headed log raises instead of being replaced
  by an empty one; only a log that does not exist yet starts fresh.

**D-20. Drop today's unfinished bar during New York trading hours** (from the review).
- Why: a manual run (or a class held during New York hours) would otherwise log a call on an
  intraday price that could never be corrected.

**D-21. Public repository; the notebook reads the log and the price snapshot from raw GitHub URLs.**
- Why: no credentials in a classroom notebook; nothing secret is stored.

**D-22. The robot keeps a daily price snapshot as the notebook's Plan B.**

## Engineering

**D-23. `tsm_pipeline.py` is the single source of truth; the notebook is generated from it.**
- Why: guarantees the class sees the exact code making live calls. Section markers map code to
  cells; Colab form cells hide plumbing; stable cell ids keep rebuilds byte-identical.
- Rejected: maintaining notebook and script separately (they drift); having the notebook download
  the module from GitHub (one more thing to break in class).

**D-24. matplotlib for all charts, with the validated reference palette and fixed entity colours.**
- Why: renders reliably in Colab and saves PNGs headlessly for the robot. Rejected: plotly
  (interactive but heavier, and the robot still needs static images).

**D-25. An offline smoke test with perturbation-based look-ahead checks, mutation-checked.**
- Why: Yahoo is not always reachable from development machines, and look-ahead bugs are silent:
  results just look slightly too good.

**D-26. Dependencies limited to yfinance, pandas, numpy, scikit-learn, matplotlib, pinned by major
version range.**
- Why: fast installs in Colab and Actions; code verified on pandas 2.2/scikit-learn 1.6 (Colab) and
  pandas 3/scikit-learn 1.9.
