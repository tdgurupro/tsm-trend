"""
Generate tsm_trend_demo.ipynb from tsm_pipeline.py plus the teaching text below.

The notebook is a BUILD OUTPUT. Never edit the .ipynb by hand:
  - code changes go in tsm_pipeline.py (split into cells by its "# ==== SECTION: name ====" markers),
  - teaching text, cell order and the notebook-only cells go in this file.

Usage (from the repo root):
  python tools/build_notebook.py            # rewrite tsm_trend_demo.ipynb
  python tools/build_notebook.py --check    # exit 1 if the committed notebook is out of date
  python tools/build_notebook.py --out X    # write a scratch copy somewhere else

Needs: pip install nbformat
"""
import argparse
import re
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tsm_pipeline.py"
DEFAULT_OUT = ROOT / "tsm_trend_demo.ipynb"
EXPECTED_SECTIONS = ["settings", "data", "features", "target", "models",
                     "walkforward", "evaluation", "plotting", "live"]

text = SRC.read_text()
parts = re.split(r"^# ==== SECTION: (\w+) ====\n", text, flags=re.M)
sections = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
if list(sections) != EXPECTED_SECTIONS:
    sys.exit(f"tsm_pipeline.py sections are {list(sections)}; expected {EXPECTED_SECTIONS}. "
             "Every section must be placed in the notebook: update this builder too.")

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))


def hidden(title, body):
    code(f'# @title {title} {{ display-mode: "form" }}\n{body}')


md("""
# Can a machine predict TSMC's next week?

**A live machine-learning demo for MIS.** The question: *at today's close, will the TSM ADR close higher 5 trading days from now?*

| Time | Part | Take-away for the class |
|---|---|---|
| 0–10 min | 1. The business question | Machine learning starts with a precise question and a measurable answer |
| 10–20 | 2. The data | Where the data comes from, and how two markets line up across time zones |
| 20–30 | 3. Signals and the answer key | Turning raw prices into a table a model can learn from; the base rate |
| 30–40 | 4. Testing honestly | Simple baselines, and how a shuffled test fools you |
| 40–55 | 5. Results | Accuracy against the baselines, year by year, and what the model learned |
| 55–65 | 6. Does it make money? | Accuracy is not profit: costs and risk |
| 65–75 | 7–9. Live call, scorecard, discussion | Deployment, monitoring and governance |

**Before class:** *Runtime → Run all* (takes about a minute). If Yahoo Finance fails, set `DATA_SOURCE = "snapshot"` in Part 2.
Grey cells marked with a title are plumbing; double-click one to see its code.

*A classroom demonstration, not investment advice.*
""")

hidden("Install libraries", "%pip install -q --upgrade yfinance")

md("""
## Part 1. The business question

A vague goal ("predict the stock") cannot be built or graded. A precise one can:

> **At today's close, will TSM close higher 5 trading days from now? UP or DOWN.**

- **Why TSMC?** It trades in two places: as **2330** in Taipei and as the **TSM ADR** in New York (one ADR = 5 Taiwan shares). The ADR is listed on the NYSE; we use the Nasdaq-100 as the tech-market backdrop.
- **Why UP/DOWN?** It turns the problem into *classification*: every call is simply right or wrong, and it maps onto a decision (hold TSM next week, or not).
- **Class poll:** what accuracy would make this model *useful*? 60%? 80%? Write the guesses down; we come back to them.

**The recipe we will follow:** question → data → signals (features) → answer key (target) → model → honest test → decision → monitoring.

The cell below holds the knobs we can turn.
""")

code("# The knobs: change one, then Runtime → Run all\n" + sections["settings"])
hidden("Engine room: data plumbing, evaluation, charts and the live log",
       "\n\n\n".join([sections["data"], sections["evaluation"], sections["plotting"], sections["live"]])
       + "\n\n\nsetup_style()\nprint('Engine loaded.')")

md("""
## Part 2. The data

Six daily price series, free from Yahoo Finance: TSM, 2330.TW, the semiconductor sector (SOXX), the Nasdaq-100 (QQQ), the market "fear gauge" (VIX) and the USD/TWD exchange rate.
""")

code("""
# Where should the prices come from?
#   "yahoo"      live prices from Yahoo Finance (the normal choice)
#   "snapshot"   backup copy saved every morning by the GitHub robot (use if Yahoo fails in class)
#   "synthetic"  a FAKE random-walk stock that works offline (testing only)
DATA_SOURCE = "yahoo"
GITHUB_RAW = "https://raw.githubusercontent.com/tdgurupro-lgtm/tsm-trend/main"

panel = load_panel(DATA_SOURCE, GITHUB_RAW)
print(f"{len(panel):,} trading days, {panel.index[0]:%Y-%m-%d} to {panel.index[-1]:%Y-%m-%d}")
panel.tail()
""")

code("plot_price(panel)")

md("""
**One company, two clocks.** Taipei closes at 13:30 Taiwan time, 8 to 9 hours before New York opens (21:30 or 22:30 Taiwan time, depending on US daylight saving). So the Taiwan price dated *today* is already known when New York closes *today*, and it is fair to use. Tomorrow's Taiwan price is not. Joining two datasets by date without thinking about the clock is one of the easiest ways to accidentally let a model peek at the future.
""")

md("""
## Part 3. Turning prices into signals

A model cannot look at a chart. It reads a **table**: one row per trading day, one column per signal (a *feature*).

**The golden rule:** a row may only use information known at that day's close. Every line below respects it.
""")

code(sections["features"])
code('pd.DataFrame(FEATURE_INFO, index=["Family", "Meaning"]).T')

md("""
### The answer key

To learn, the model needs the right answer for every past day: did TSM close higher 5 trading days later? This is the *target*. It is the only column allowed to look into the future, because it is what we are trying to predict.
""")

code(sections["target"] + """


data = make_dataset(panel)
print(f"{len(data):,} rows x {len(FEATURES)} features. The last {HORIZON} rows have no answer yet: that is the future.")
data[["ret_5d", "rsi_14", "adr_premium", "future_return", "target"]].tail(8)""")

md("One of the more interesting signals: how much extra US investors pay for TSMC in New York compared with Taipei.")
code("plot_adr_premium(data)")

md("""
### The base rate

Before any modelling: how often did TSM go up over a 5-day stretch? Saying "UP" every single time scores exactly this. **Any model must beat it to be worth anything.**
""")
code("plot_return_histogram(data)")

md("""
### Is there any pattern at all?

If last week's move told us next week's move, the dots below would form a slope. Compare the cloud with your accuracy guess from Part 1.
""")
code("plot_noise_scatter(data)")

md("""
## Part 4. Testing honestly

Two rules separate a real result from a fake one:

1. **Beat the no-brainers.** *Always up* (the base rate) and *Momentum* (assume the past week's direction continues).
2. **Grade the model only on days it has never seen, and that come after its training days.** That is how it will be used in real life.

Our two contenders:
""")
code(sections["models"])

md("""
### The trap: grading on shuffled days

The most common beginner method shuffles all days and holds out a random 25% for grading. For time series it is **wrong**: each test day sits right next to training days, and neighbouring days share 4 of the same 5 future days. A flexible model can memorise the answer key instead of learning anything.

Below we grade one flexible model both ways, on real TSM and on a **fake stock that is pure coin flips**, where no honest model can beat chance.
""")
code(sections["walkforward"])
code("""
fake = make_dataset(make_synthetic_panel())     # a random walk: unpredictable by construction
flex = make_flexible_model()
leakage = {
    "Real TSM": {
        "Shuffled days (wrong)": split_test(data, flex, shuffle=True),
        "Time order (right)": split_test(data, flex, shuffle=False),
    },
    "Fake coin-flip stock": {
        "Shuffled days (wrong)": split_test(fake, flex, shuffle=True),
        "Time order (right)": split_test(fake, flex, shuffle=False),
    },
}
plot_leakage(leakage)
""")

md("""
If the shuffled test "predicts" a stock made of coin flips, the test is broken, not the market. **Manager's take-away:** when a vendor or analyst shows you a great accuracy number, the first question is *how was it tested?*

### The right way: walk-forward testing

We replay history as if we were living through it: train on everything up to a date, predict the next quarter, then move forward and retrain. A 5-day gap separates training and testing so no answer key leaks across.
""")
code("plot_walk_forward_scheme()")
code("""
calls, probs = run_walk_forward_suite(data)     # about 20-40 seconds: dozens of retrainings
acc = accuracy_table(calls)
plot_accuracy_bars(acc)
acc.style.format({"Accuracy": "{:.1%}", "95% range low": "{:.1%}", "95% range high": "{:.1%}", "Calls tested": "{:,}"})
""")

md("""
## Part 5. Reading the results

- **Compare against Always up, not against 50%.** A model that loses to "always say UP" adds nothing.
- **The 95% range** shows how far luck alone could move the score. Calls on neighbouring days share most of the same week, so the range counts every 5 daily calls as one independent week. Overlapping ranges mean we cannot honestly call a winner.
- Go back to the class poll from Part 1. How do the guesses compare?
""")
code("plot_accuracy_by_year(accuracy_by_year(calls))")

md("""
Markets change mood: what worked in a calm year can fail in a crash or a boom. A single overall number hides this.

### What did the simple model learn?

The logistic model is a weighted checklist, so we can read its weights. Gradient boosting is a *black box*: often more powerful, much harder to explain to a boss, a client or a regulator.
""")
code("plot_logistic_weights(logistic_weights(data))")

md("""
## Part 6. Does it make money?

Accuracy is not profit. One big miss can wipe out many small wins, and every trade costs money. We turn each model's calls into a portfolio: each day's call decides what 1/5 of the money does for 5 days (in TSM if UP, in cash if DOWN). A call made tonight is traded at tomorrow's close, and every change of position pays 0.10%.
""")
code("""
results = run_backtests(calls, panel)
plot_equity(results)
performance_table(results).style.format({
    "$10,000 grows to": "${:,.0f}", "Return per year": "{:.1%}",
    "Worst fall from a peak": "{:.1%}", "Time invested in TSM": "{:.0%}"})
""")

md("""
Look at more than the final number: how deep were the falls, and how much of the time was the money actually invested? Sitting in cash can lower risk *and* returns.

## Part 7. Today's live call

The models now train on all history with a known answer and make a call for the newest close. Nobody knows the answer yet, including us.
""")
code("""
as_of, today = predict_latest(data)
show_prediction_card(as_of, panel.loc[as_of, "TSM_RawClose"], today)
""")

md("""
## Part 8. The live scorecard (weekly update)

Every trading day a small robot (GitHub Actions) repeats Part 7 and writes the call into a public log **before** the outcome is known. Five trading days later it marks the call right or wrong. Backtests can be fooled; a timestamped live record cannot.

**Each week in class:** Are we above Always up? Is the 95% range still too wide to tell? (20 daily calls overlap so much that they are worth about 4 independent weeks.) Did a news event explain a run of misses?
""")
code("""
log = load_log(f"{GITHUB_RAW}/predictions_log.csv")
if log.empty:
    print("No live log found yet. Set GITHUB_RAW in Part 2 and let the daily robot run for a week.")
else:
    plot_live_scorecard(log); plt.show()
    display(scorecard_table(log).style.format(
        {"Accuracy": "{:.0%}", "95% range low": "{:.0%}", "95% range high": "{:.0%}"}, na_rep="n/a"))
    display(log[["as_of_date", "tsm_close", "call_logistic", "call_boosting",
                 "actual_return_5d", "actual"]].tail(10).iloc[::-1])
""")

md("""
## Part 9. Discussion: would you deploy this?

1. **Decision rights.** Who acts on the model's call, and what does a wrong call cost compared with a right one? What accuracy, after costs, would justify using it?
2. **Data supply chain.** Everything rests on a free, unofficial data feed. What breaks if it changes or disappears, and what would a bank pay for instead?
3. **Monitoring.** The live scorecard is a monitoring system. Decide *now*, before seeing more results, what would make you switch the model off.
4. **Audit trail.** Why does it matter that every call is saved, with a timestamp, before the outcome is known?
5. **Explainability.** When is a black-box model unacceptable even if it scores better: credit decisions, compliance, client advice?
6. **Competition.** If a simple model like this reliably made money, what would happen once everyone used it?

---

### Appendix: the daily robot, as an information system

```
Monday to Friday after the New York close (06:30 Taipei time, Tuesday to Saturday)
GitHub Actions: a free cloud computer
  1. Download fresh prices (Yahoo Finance) and save a snapshot   -> data/prices.csv
  2. Score every call made 5 trading days ago                    -> predictions_log.csv
  3. Retrain both models and log today's call
  4. Rewrite the weekly scorecard                                -> scorecard.md, scorecard.png
  5. Commit everything to the repository: a public, timestamped audit trail
```
The robot runs `daily_predict.py`, which uses exactly the same code as this notebook.
""")



def build():
    nb = nbf.v4.new_notebook()
    for i, cell in enumerate(cells):
        cell["id"] = f"cell-{i:02d}"          # stable ids so rebuilds are byte-identical
    nb["cells"] = cells
    nb["metadata"] = {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    }
    return nbf.writes(nb) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate the class notebook from tsm_pipeline.py")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true",
                        help="only check that the committed notebook matches; do not write")
    args = parser.parse_args()
    content = build()
    if args.check:
        current = DEFAULT_OUT.read_text() if DEFAULT_OUT.exists() else ""
        if current != content:
            sys.exit("tsm_trend_demo.ipynb is out of date: run  python tools/build_notebook.py")
        print("Notebook is up to date.")
        return
    args.out.write_text(content)
    print(f"Wrote {args.out} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
