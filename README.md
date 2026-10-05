# TSM 5-day trend: a live machine-learning demo

**Question:** at today's close, will the TSM ADR close higher 5 trading days from now? UP or DOWN.

Built for a 75-minute MIS class demo, with a robot that makes a real call every trading day so the class can follow a live, timestamped track record week by week. A classroom demonstration, not investment advice.

| File | What it is |
|---|---|
| `tsm_trend_demo.ipynb` | The class notebook (open in Google Colab). Run-of-show is at the top. |
| `tsm_pipeline.py` | The engine: data, features, models, testing, charts. The notebook contains the same code. |
| `daily_predict.py` | The daily robot's script: logs today's call, scores old calls, writes the scorecard. |
| `.github/workflows/daily.yml` | The schedule: runs `daily_predict.py` every weekday at 22:30 UTC (06:30 Taipei). |
| `predictions_log.csv` | Created by the robot: every call, logged before its outcome was known. |
| `scorecard.md` / `scorecard.png` | Created by the robot: running accuracy for the weekly class update. |
| `data/prices.csv` | Created by the robot: daily price snapshot, the notebook's backup if Yahoo Finance is down. |
| `CLAUDE.md`, `.claude/rules/` | Context for Claude Code: open this folder in Claude Code and it picks up where we left off. |
| `docs/` | `DESIGN.md` (how it works and why), `DECISIONS.md` (choices and alternatives), `HANDOFF.md` (status, next steps). |
| `tools/` | `build_notebook.py` regenerates the notebook from the code; `smoke_test.py` runs offline checks. |

## One-time setup (about 15 minutes)

1. **Create a public GitHub repository** named `tsm-trend`. Public lets the notebook read the log without a password; nothing secret is stored in it.
2. **Upload the files** in this folder (*Add file → Upload files*), keeping the folder structure. The workflow must end up at `.github/workflows/daily.yml`, and the Claude rules at `.claude/rules/`. Folders starting with a dot are hidden on a Mac (press Cmd+Shift+. in Finder to show them). If the upload skips one, use *Add file → Create new file*, type the full path (for example `.github/workflows/daily.yml`) as the name, and paste the file's contents. Using `git push` from a terminal avoids this problem entirely.
3. **Start the robot once by hand:** *Actions* tab → enable workflows if asked → *Daily TSM prediction* → *Run workflow*. After 2–3 minutes the repo gains `predictions_log.csv`, `scorecard.md`, `scorecard.png` and `data/prices.csv`.
   If the run fails at *Save results to the repository* with a permission error: *Settings → Actions → General → Workflow permissions → Read and write permissions*, then run it again.
4. **Point the notebook at your repo:** in Part 2 of the notebook set
   `GITHUB_RAW = "https://raw.githubusercontent.com/<your-username>/tsm-trend/main"`.
5. **Open the notebook in Colab:** colab.research.google.com → *File → Open notebook → GitHub* → paste your repo URL → pick `tsm_trend_demo.ipynb`.

## Running the class

- **Before class:** *Runtime → Run all* (about a minute). If Yahoo Finance fails, set `DATA_SOURCE = "snapshot"` in Part 2 and run again.
- **Weekly update:** open `scorecard.md` on GitHub, or rerun Part 8 of the notebook.

## Good to know

- **Schedule:** 22:30 UTC Monday–Friday is after the New York close in both summer and winter time. GitHub sometimes starts scheduled runs a little late; that is fine.
- **Holidays and re-runs** are safe: a close that is already logged is never logged twice.
- **Missed days:** Yahoo Finance is free and unofficial and occasionally blocks cloud servers. The script retries; if a run still fails, GitHub emails you and you can press *Run workflow* later. A day that is never run simply has no call.
- **If GitHub ever emails that the scheduled workflow was disabled**, re-enable it from the *Actions* tab.
- **Change management:** the live record is only meaningful if the model stays fixed. If you change the features or models mid-semester, note the date in class; calls before and after are different models.
- **Test without internet:** `python daily_predict.py --source synthetic --out demo` runs everything on a fake random-walk stock (the `demo` folder is ignored by git).

## Changing the code

The notebook is generated from `tsm_pipeline.py`: never edit the `.ipynb` directly. After any change:

```bash
pip install -r requirements.txt nbformat nbconvert ipykernel   # Python 3.11 or newer
python tools/build_notebook.py          # regenerate the notebook
python tools/smoke_test.py --notebook   # offline checks, about a minute
```

To continue with Claude Code, open a `git clone` of your GitHub repo in Claude Code (a clone has the robot's latest log; a downloaded copy goes stale). It reads `CLAUDE.md` automatically, and `docs/HANDOFF.md` lists the next steps.
