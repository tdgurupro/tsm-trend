---
paths:
  - "tsm_trend_demo.ipynb"
  - "tools/build_notebook.py"
  - "tools/smoke_test.py"
---

# Editing the class notebook

- `tsm_trend_demo.ipynb` is generated. Change teaching text and cell order in
  `tools/build_notebook.py` (helpers `md()`, `code()`, `hidden(title, body)`); change code in
  `tsm_pipeline.py`. Then `python tools/build_notebook.py && python tools/smoke_test.py --notebook`.
- Cell ids are fixed (`cell-00`, `cell-01`, ...) so rebuilds are byte-identical and diffs readable.
- The run-of-show table in the first cell must still add up to 75 minutes. Update it whenever you
  add, remove or move material between parts.
- Audience: MBA students, mostly non-coders. Plain English, one idea per markdown cell, and a
  sentence before each chart telling students what to look for. Name the business take-away.
- Keep these strings exact, because `tools/smoke_test.py` swaps them to run the notebook offline:
  `%pip install -q --upgrade yfinance`, `DATA_SOURCE = "yahoo"` and
  `https://raw.githubusercontent.com/tdgurupro-lgtm/tsm-trend/main`. If you change one, update
  `execute_notebook` in the smoke test too. (If the repo ever moves, change the URL in the
  builder and in the smoke test together. Keep the `YOUR-GITHUB-NAME` check in `load_panel`:
  it protects copies of the notebook that still carry the old placeholder.)
- Chart functions live in the `plotting` section of `tsm_pipeline.py` and call `plt.show()`
  themselves, except `plot_live_scorecard`, which returns the figure so the robot can save it.
- Never claim specific result numbers in markdown (accuracy, returns): the text must stay true
  whatever the live data says. Describe what to look for instead.
