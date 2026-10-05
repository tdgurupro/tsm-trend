"""
Offline smoke test for the TSM demo. No internet needed: it uses a fake
random-walk stock and a mocked Yahoo Finance.

Run from the repo root after ANY change to the pipeline, the daily script or the notebook builder:

    python tools/smoke_test.py               # core checks, about 20 seconds
    python tools/smoke_test.py --notebook    # also execute the whole notebook offline (+30 s)
                                             # (needs: pip install nbformat nbconvert ipykernel)

What it guards, in order of importance:
  1. No look-ahead: features, targets, walk-forward predictions and the backtest
     never use information from after the decision time.
  2. The live log: outcomes scored against the right day, no duplicate calls,
     a damaged log fails loudly instead of being silently replaced.
  3. Plumbing: Yahoo-shaped data (MultiIndex columns, Taipei time zone, holidays),
     the daily script end to end, and the notebook being in sync with the code.
"""
import argparse
import subprocess
import sys
import tempfile
import time
import traceback
import types
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tsm_pipeline as tp  # noqa: E402

FIXED_END = "2026-10-02"   # fixed so results do not drift with today's date
CHECKS = []


class Skip(Exception):
    """Raised when a check cannot run in this environment."""


def check(fn):
    CHECKS.append(fn)
    return fn


def perturb_after(panel, cut, seed=1):
    """Scramble every price after `cut`. Anything dated on or before `cut` must not notice."""
    changed = panel.copy()
    after = changed.index > cut
    factors = np.random.default_rng(seed).uniform(0.5, 1.5, size=changed.loc[after].shape)
    changed.loc[after] = changed.loc[after].to_numpy() * factors
    return changed


def simulate_log(folder, panel, days=26, repeat_at=10):
    """Run the daily robot once per day over the last `days` days, re-running one day twice."""
    log_path = Path(folder) / "predictions_log.csv"
    runs = list(range(len(panel) - days + 1, len(panel) + 1))
    runs.insert(repeat_at, runs[repeat_at])
    for n in runs:
        p = panel.iloc[:n]
        now = pd.Timestamp(p.index[-1]).tz_localize("UTC") + pd.Timedelta(hours=22, minutes=30)
        log, _ = tp.update_log(tp.load_log(log_path), p, now=now)
        log.to_csv(log_path, index=False)
    return tp.load_log(log_path)


# ---------------------------------------------------------------- 1. no look-ahead
@check
def features_and_target_use_only_the_past(tmp):
    panel = tp.make_synthetic_panel(end="2020-12-31")
    cut = panel.index[2000]
    changed = perturb_after(panel, cut)
    changed.loc[cut, "USDTWD_Close"] *= 1.3        # features use YESTERDAY's FX rate
    pd.testing.assert_frame_equal(tp.build_features(panel).loc[:cut],
                                  tp.build_features(changed).loc[:cut])
    _, target_a = tp.make_target(panel)
    _, target_b = tp.make_target(changed)
    safe = panel.index[2000 - tp.HORIZON]          # day t's answer needs the close of t+5
    pd.testing.assert_series_equal(target_a.loc[:safe], target_b.loc[:safe])


@check
def impossible_fx_rates_are_judged_only_on_the_past(tmp):
    idx = pd.bdate_range("2024-01-01", periods=40)
    rate = pd.Series(30 + np.random.default_rng(3).normal(0, 0.1, 40), index=idx)
    rate.iloc[20] = 1.8                            # the kind of glitch Yahoo really has
    clean = tp.drop_impossible_fx(rate)
    assert idx[20] not in clean.index and len(clean) == 39, "the impossible rate was kept"
    later = rate.copy()
    later.iloc[25:] *= 0.5                         # whatever happens later must not change earlier days
    pd.testing.assert_series_equal(clean.loc[:idx[24]], tp.drop_impossible_fx(later).loc[:idx[24]])


@check
def walk_forward_uses_only_the_past(tmp):
    panel = tp.make_synthetic_panel(end="2016-12-31")
    data = tp.make_dataset(panel)
    # Cut 2 days into a test block: without the 5-day gap, that block's training
    # answers would need prices from after the cut.
    cut = data.dropna(subset=["target"]).index[tp.MIN_TRAIN_DAYS + 3 * tp.RETRAIN_EVERY + 2]
    model = tp.make_models()["Logistic regression"]
    a = tp.walk_forward(data, model)
    b = tp.walk_forward(tp.make_dataset(perturb_after(panel, cut)), model)
    pd.testing.assert_series_equal(a.loc[:cut], b.loc[:cut])


@check
def backtest_trades_at_the_next_close(tmp):
    idx = pd.bdate_range("2024-01-01", periods=30)
    signal = pd.Series((np.arange(30) % 3 == 0).astype(float), index=idx)
    daily = pd.Series(np.linspace(-0.02, 0.03, 30), index=idx)
    out = tp.backtest(signal, daily, cost=0.0)
    position = signal.rolling(tp.HORIZON).mean()
    t = 10   # decided at close t, traded at close t+1, so it earns the return of day t+2
    assert abs(out.loc[idx[t], "return"] - position.iloc[t] * daily.iloc[t + 2]) < 1e-12


@check
def shuffled_test_is_fooled_by_a_random_walk(tmp):
    data = tp.make_dataset(tp.make_synthetic_panel(end=FIXED_END))
    flex = tp.make_flexible_model()
    wrong = tp.split_test(data, flex, shuffle=True)
    right = tp.split_test(data, flex, shuffle=False)
    assert wrong > 0.56 and wrong - right > 0.05, f"shuffled {wrong:.3f} vs time order {right:.3f}"


# ---------------------------------------------------------------- 2. the live log
@check
def live_log_scores_the_right_day_and_never_duplicates(tmp):
    panel = tp.make_synthetic_panel(start="2015-01-01", end=FIXED_END)
    log = simulate_log(tmp, panel, days=26)
    assert len(log) == 26 and log["as_of_date"].is_unique, "a close was logged twice"
    close = panel["TSM_Close"]
    dates = list(close.index.strftime("%Y-%m-%d"))
    scored = tp.scored_rows(log)
    assert len(scored) == 26 - tp.HORIZON, f"{len(scored)} rows scored"
    for _, r in scored.iterrows():
        i = dates.index(r["as_of_date"])
        ret = close.iloc[i + tp.HORIZON] / close.iloc[i] - 1
        assert abs(ret - r["actual_return_5d"]) < 1e-6 and r["checked_on"] == dates[i + tp.HORIZON]
        actual = "UP" if ret > 0 else "DOWN"
        for key in ["logistic", "boosting", "always_up"]:
            assert r[f"hit_{key}"] == int(r[f"call_{key}"] == actual)
    tp.write_scorecard(log, tmp)
    assert (tmp / "scorecard.md").exists() and (tmp / "scorecard.png").exists()


@check
def damaged_log_fails_loudly(tmp):
    assert tp.load_log(tmp / "missing.csv").empty, "a missing log should start a new one"
    damaged = {
        "merge conflict": 'as_of_date,tsm_close\n"2026-01-01,1\n<<<<<<< HEAD\n',
        "empty file": "",
        "wrong header": "date;close;call\n2026-01-01;100;UP\n",
    }
    for name, content in damaged.items():
        bad = tmp / "bad.csv"
        bad.write_text(content)
        try:
            tp.load_log(bad)
        except Exception:
            continue
        raise AssertionError(f"a damaged log ({name}) loaded silently; the robot would overwrite the track record")


# ---------------------------------------------------------------- 3. plumbing
@check
def yahoo_shaped_data_is_aligned_correctly(tmp):
    syn = tp.make_synthetic_panel(start="2015-01-01", end=FIXED_END)
    column = {"TSM": "TSM_Close", "2330.TW": "TW2330_Close", "SOXX": "SOXX_Close",
              "QQQ": "QQQ_Close", "^VIX": "VIX_Close", "TWD=X": "USDTWD_Close"}

    def fake_download(ticker, start=None, end=None, auto_adjust=None, progress=None, threads=None):
        assert auto_adjust is False, "raw and adjusted prices are both needed"
        s = syn[column[ticker]].copy()
        if ticker == "2330.TW":   # Lunar New Year closure, Taipei time zone like real Yahoo data
            s = s.drop(pd.to_datetime(["2026-02-16", "2026-02-17", "2026-02-18"]))
            s.index = s.index.tz_localize("Asia/Taipei")
        if ticker == "TSM":       # a New York holiday
            s = s.drop(pd.to_datetime(["2026-07-03"]))
        if ticker == "TWD=X":     # an impossible rate, like Yahoo's 1.80 on 2011-10-25
            s.loc["2026-03-11"] /= 16
        df = pd.DataFrame({"Adj Close": s * 0.97, "Close": s, "High": s * 1.01,
                           "Low": s * 0.99, "Open": s, "Volume": 1e7})
        df.columns = pd.MultiIndex.from_product([df.columns, [ticker]], names=["Price", "Ticker"])
        return df

    saved_module, saved_sleep = sys.modules.get("yfinance"), tp.time.sleep
    sys.modules["yfinance"] = types.SimpleNamespace(download=fake_download)
    tp.time.sleep = lambda seconds: None
    try:
        panel = tp.download_prices(start="2015-01-01")
    finally:
        tp.time.sleep = saved_sleep
        if saved_module is None:
            sys.modules.pop("yfinance", None)
        else:
            sys.modules["yfinance"] = saved_module
    assert pd.Timestamp("2026-07-03") not in panel.index, "rows must follow TSM's New York calendar"
    assert (panel.loc["2026-02-18", "TW2330_RawClose"] == panel.loc["2026-02-13", "TW2330_RawClose"]), \
        "a Taiwan holiday must carry the last known price forward"
    assert (panel.loc["2026-03-11", "USDTWD_Close"] == panel.loc["2026-03-10", "USDTWD_Close"]), \
        "an impossible FX rate must be replaced by the last good one"
    assert np.allclose(panel["TSM_Close"] / panel["TSM_RawClose"], 0.97), "adjusted vs raw columns mixed up"
    assert np.isfinite(tp.build_features(panel).dropna().to_numpy()).all()


@check
def daily_script_runs_twice_without_duplicating(tmp):
    out = tmp / "cli"
    for _ in range(2):
        result = subprocess.run([sys.executable, str(ROOT / "daily_predict.py"), "--source", "synthetic",
                                 "--out", str(out)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr[-2000:]
    assert "already logged" in result.stdout
    for name in ["predictions_log.csv", "scorecard.md", "scorecard.png", "data/prices.csv"]:
        assert (out / name).exists(), f"{name} missing"


@check
def notebook_is_in_sync_with_the_code(tmp):
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "build_notebook.py"), "--check"],
                            capture_output=True, text=True)
    if "No module named 'nbformat'" in result.stderr:
        raise Skip("pip install nbformat to check the notebook")
    assert result.returncode == 0, (result.stdout + result.stderr).strip()


def execute_notebook(tmp):
    """Build a test copy that uses the fake stock and a simulated log, then run every cell."""
    import nbformat as nbf
    folder = tmp / "nb"
    folder.mkdir()
    simulate_log(folder, tp.make_synthetic_panel(start="2015-01-01", end=FIXED_END), days=30)
    nb = nbf.read(ROOT / "tsm_trend_demo.ipynb", as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = (cell.source
                           .replace("%pip install -q --upgrade yfinance", "pass")
                           .replace('DATA_SOURCE = "yahoo"', 'DATA_SOURCE = "synthetic"')
                           .replace("https://raw.githubusercontent.com/tdgurupro/tsm-trend/main",
                                    folder.as_posix()))   # forward slashes: a Windows path would break the string
    test_copy = folder / "test.ipynb"
    nbf.write(nb, test_copy)
    result = subprocess.run(["jupyter", "nbconvert", "--to", "notebook", "--execute", str(test_copy),
                             "--output", "executed.ipynb", "--ExecutePreprocessor.timeout=600"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-3000:]
    executed = nbf.read(folder / "executed.ipynb", as_version=4)
    problems = [f"cell {i}: {o.get('ename') or o.get('text', '')[:200]}"
                for i, c in enumerate(executed.cells) for o in c.get("outputs", [])
                if o.output_type == "error" or (o.output_type == "stream" and o.name == "stderr")]
    assert not problems, "\n".join(problems)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--notebook", action="store_true", help="also execute the whole notebook offline")
    args = parser.parse_args()
    checks = CHECKS + ([execute_notebook] if args.notebook else [])
    warnings.simplefilter("error", FutureWarning)   # catch pandas deprecations early
    failed = 0
    with tempfile.TemporaryDirectory() as root:
        for fn in checks:
            tmp = Path(root) / fn.__name__
            tmp.mkdir()
            start = time.time()
            try:
                fn(tmp)
                print(f"PASS  {fn.__name__}  ({time.time() - start:.1f}s)")
            except Skip as reason:
                print(f"SKIP  {fn.__name__}: {reason}")
            except Exception:
                failed += 1
                print(f"FAIL  {fn.__name__}\n{traceback.format_exc()}")
    print(f"\n{len(checks) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
