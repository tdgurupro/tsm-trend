"""
tsm_pipeline.py: the engine behind the TSM ADR 5-day trend demo.

The daily runner imports this file, and the class notebook is generated from it
(same code, cell by cell), so the model students see in class is exactly the
model making the live predictions.

The question: "Will TSM's close 5 trading days from now be higher than
today's close?"  That is an UP / DOWN classification problem.
"""

# ==== SECTION: settings ====
import math
import time

import numpy as np
import pandas as pd

HORIZON = 5             # how far ahead we predict, in trading days
START = "2010-01-01"    # first day of history we download
ADR_RATIO = 5           # 1 TSM ADR = 5 ordinary TSMC shares in Taiwan
COST_PER_TRADE = 0.001  # 0.10% cost every time the portfolio changes position
MIN_TRAIN_DAYS = 750    # about 3 years of history before the first test
RETRAIN_EVERY = 63      # retrain the model every quarter (63 trading days)

TICKERS = {
    "TSM":    "TSM",      # TSMC ADR, traded in New York (NYSE)
    "TW2330": "2330.TW",  # TSMC ordinary shares, traded in Taipei
    "SOXX":   "SOXX",     # US semiconductor-sector ETF
    "QQQ":    "QQQ",      # Nasdaq-100 ETF: the broad tech market
    "VIX":    "^VIX",     # the "fear gauge": expected US market volatility
    "USDTWD": "TWD=X",    # New Taiwan dollars per 1 US dollar
}


# ==== SECTION: data ====
def _download_one(ticker, start=START, end=None, retries=3):
    """Download daily prices for one ticker from Yahoo Finance, with retries."""
    import yfinance as yf
    last_error = None
    for attempt in range(retries):
        try:
            df = yf.download(ticker, start=start, end=end, auto_adjust=False,
                             progress=False, threads=False)
            if df is not None and len(df) > 0:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                idx = pd.DatetimeIndex(df.index)
                if idx.tz is not None:
                    idx = idx.tz_localize(None)   # keep each market's local calendar date
                df.index = idx.normalize()
                return df[~df.index.duplicated(keep="last")]
        except Exception as err:          # network hiccup, rate limit, ...
            last_error = err
        if attempt < retries - 1:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Could not download {ticker} from Yahoo Finance ({last_error or 'no data returned'})")


def drop_impossible_fx(rate, max_move=0.20):
    """Free data has errors: Yahoo's USD/TWD feed contains a few impossible days
    (about 1.8 or 3.7 instead of about 30). A rate more than 20% away from the
    median of the PREVIOUS 5 days is treated as missing, so the last good rate is
    carried forward. Only past values are used to judge each day."""
    rate = rate.astype(float).dropna()
    reference = rate.rolling(5, min_periods=1).median().shift(1)
    bad = (rate / reference - 1).abs() > max_move
    if bad.any():
        print(f"Ignoring {bad.sum()} impossible USD/TWD rate(s) from Yahoo on: "
              + ", ".join(f"{d:%Y-%m-%d}" for d in rate.index[bad]))
    return rate[~bad]


def assemble_panel(raw):
    """Line every market up on TSM's New York trading calendar."""
    def adjusted(df):    # dividends added back: the right price for measuring returns
        return df["Adj Close"] if "Adj Close" in df else df["Close"]

    tsm = raw["TSM"]
    panel = pd.DataFrame(index=tsm.index)
    panel.index.name = "Date"
    panel["TSM_Close"] = adjusted(tsm).astype(float)
    # Raw prices as quoted that day: the right prices for same-day ratios.
    panel["TSM_RawClose"] = tsm["Close"].astype(float)
    panel["TSM_High"] = tsm["High"].astype(float)
    panel["TSM_Low"] = tsm["Low"].astype(float)
    panel["TSM_Volume"] = tsm["Volume"].astype(float)
    others = {
        "TW2330_Close": adjusted(raw["TW2330"]), "TW2330_RawClose": raw["TW2330"]["Close"],
        "SOXX_Close": adjusted(raw["SOXX"]), "QQQ_Close": adjusted(raw["QQQ"]),
        "VIX_Close": raw["VIX"]["Close"], "USDTWD_Close": drop_impossible_fx(raw["USDTWD"]["Close"]),
    }
    for col, s in others.items():
        s = s.astype(float).dropna()
        if s.index[-1] < panel.index[-1] - pd.Timedelta(days=10):
            print(f"Warning: {col} has no data after {s.index[-1]:%Y-%m-%d}; its values are stale.")
        # Taipei closes 8-9 hours before New York opens, so a Taiwan price
        # dated day t is already known when New York closes on day t. When a
        # market was shut for a holiday, carry its last known price FORWARD
        # (never backward: that would borrow information from the future).
        s = s.reindex(s.index.union(panel.index)).ffill()
        panel[col] = s.reindex(panel.index)
    return panel.dropna()


def download_prices(start=START, end=None):
    """Fresh daily history for every ticker in TICKERS."""
    raw = {}
    for name, ticker in TICKERS.items():
        raw[name] = _download_one(ticker, start, end)
        time.sleep(1)                     # be polite to a free data source
    panel = assemble_panel(raw)
    # During New York trading hours Yahoo includes today's unfinished bar. Its
    # "close" is just the latest trade, so leave it out until the market closes.
    now_ny = pd.Timestamp.now(tz="America/New_York")
    if panel.index[-1] >= pd.Timestamp(now_ny.date()) and (now_ny.hour, now_ny.minute) < (16, 30):
        print("New York is still trading today: leaving out today's unfinished price.")
        panel = panel.iloc[:-1]
    return panel


def make_synthetic_panel(start=START, end=None, seed=7):
    """A FAKE stock whose daily moves are independent coin flips (a random walk).

    Nothing about its future is predictable, by construction. Used for the
    sanity check in class and for testing without an internet connection.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end or pd.Timestamp.today().normalize())
    n = len(dates)
    market = rng.normal(0.0005, 0.012, n)
    sector = 1.2 * market + rng.normal(0.0002, 0.009, n)
    stock = sector + rng.normal(0.0002, 0.012, n)

    close = 20 * np.exp(np.cumsum(stock))
    opens = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(opens, close) * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = np.minimum(opens, close) * (1 - np.abs(rng.normal(0, 0.008, n)))

    log_vix = np.empty(n)
    log_vix[0] = math.log(18)
    for t in range(1, n):                 # mean-reverting fear gauge
        log_vix[t] = (log_vix[t - 1] + 0.04 * (math.log(18) - log_vix[t - 1])
                      - 3.0 * market[t] + rng.normal(0, 0.05))
    fx = 30 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    premium = 0.12 + 0.05 * np.sin(np.arange(n) / 150) + rng.normal(0, 0.01, n)

    taiwan = close * fx / ADR_RATIO / (1 + premium)
    return pd.DataFrame({
        "TSM_Close": close, "TSM_RawClose": close, "TSM_High": high, "TSM_Low": low,
        "TSM_Volume": np.exp(rng.normal(16, 0.35, n)).round(),
        "TW2330_Close": taiwan, "TW2330_RawClose": taiwan,
        "SOXX_Close": 50 * np.exp(np.cumsum(sector)),
        "QQQ_Close": 60 * np.exp(np.cumsum(market)),
        "VIX_Close": np.exp(log_vix),
        "USDTWD_Close": fx,
    }, index=pd.DatetimeIndex(dates, name="Date"))


def load_panel(source="yahoo", github_raw=None):
    """Get the price panel from Yahoo, the daily robot's snapshot, or a fake stock."""
    has_repo = bool(github_raw) and "YOUR-GITHUB-NAME" not in github_raw
    if source == "yahoo":
        try:
            return download_prices()
        except Exception as err:
            print(f"Yahoo Finance download failed: {err}")
            if not has_repo:
                raise
            print("Falling back to the snapshot saved by the daily robot.")
            source = "snapshot"
    if source == "snapshot":
        if not has_repo:
            raise ValueError("Set GITHUB_RAW to your repository first.")
        panel = pd.read_csv(f"{github_raw}/data/prices.csv", index_col="Date", parse_dates=True)
        print(f"Loaded snapshot saved through {panel.index[-1]:%Y-%m-%d}.")
        return panel
    if source == "synthetic":
        print("Using a FAKE random-walk stock. The numbers below are not TSM.")
        return make_synthetic_panel()
    raise ValueError(f"Unknown data source: {source!r}")


# ==== SECTION: features ====
def pct(series, days):
    """Percentage change over the past `days` trading days."""
    return series / series.shift(days) - 1


def rsi(close, window=14):
    """Relative Strength Index: 0-100 score of recent gains vs. recent losses."""
    change = close.diff()
    gain = change.clip(lower=0).rolling(window).mean()
    loss = (-change.clip(upper=0)).rolling(window).mean()
    return 100 - 100 / (1 + gain / loss)


# Every feature, its family, and what it means in plain English.
FEATURE_INFO = {
    "ret_1d":             ("Momentum", "TSM's return today"),
    "ret_5d":             ("Momentum", "TSM's return over the past week"),
    "ret_20d":            ("Momentum", "TSM's return over the past month"),
    "gap_ma20":           ("Trend", "How far the price sits above/below its 20-day average"),
    "gap_ma50":           ("Trend", "How far the price sits above/below its 50-day average"),
    "rsi_14":             ("Trend", "RSI: 0-100 score of recent gains vs. losses (>70 = 'overbought')"),
    "volatility_20d":     ("Risk", "How bumpy daily moves were over the past month"),
    "range_5d":           ("Risk", "Average high-to-low swing within a day, past week"),
    "volume_ratio":       ("Attention", "Today's trading volume vs. its 20-day average"),
    "soxx_ret_5d":        ("Sector & market", "Semiconductor sector's return over the past week"),
    "qqq_ret_5d":         ("Sector & market", "Nasdaq-100's return over the past week"),
    "rel_strength_20d":   ("Sector & market", "TSM's past-month return minus the sector's"),
    "vix_level":          ("Sector & market", "Level of the market 'fear gauge' (VIX)"),
    "vix_chg_5d":         ("Sector & market", "Change in the fear gauge over the past week"),
    "tw_ret_1d":          ("Taiwan link", "TSMC's return in Taipei today (trades before New York opens)"),
    "adr_premium":        ("Taiwan link", "Extra % US investors pay for the ADR vs. the Taiwan shares"),
    "adr_premium_vs_60d": ("Taiwan link", "Today's ADR premium vs. its 60-day average"),
    "twd_chg_20d":        ("Taiwan link", "Change in the USD/TWD exchange rate over the past month"),
}
FEATURES = list(FEATURE_INFO)


def build_features(panel):
    """Turn raw prices into signals. Row t uses ONLY information known at the close of day t."""
    p, close = panel, panel["TSM_Close"]
    daily = pct(close, 1)
    f = pd.DataFrame(index=p.index)

    f["ret_1d"], f["ret_5d"], f["ret_20d"] = daily, pct(close, 5), pct(close, 20)
    f["gap_ma20"] = close / close.rolling(20).mean() - 1
    f["gap_ma50"] = close / close.rolling(50).mean() - 1
    f["rsi_14"] = rsi(close)
    f["volatility_20d"] = daily.rolling(20).std()
    f["range_5d"] = ((p["TSM_High"] - p["TSM_Low"]) / p["TSM_RawClose"]).rolling(5).mean()
    f["volume_ratio"] = p["TSM_Volume"] / p["TSM_Volume"].rolling(20).mean()

    f["soxx_ret_5d"] = pct(p["SOXX_Close"], 5)
    f["qqq_ret_5d"] = pct(p["QQQ_Close"], 5)
    f["rel_strength_20d"] = f["ret_20d"] - pct(p["SOXX_Close"], 20)
    f["vix_level"] = p["VIX_Close"]
    f["vix_chg_5d"] = pct(p["VIX_Close"], 5)

    # Yahoo's currency bar for day t can close after New York does, so we use
    # YESTERDAY's exchange rate to stay safely on the known side of the clock.
    fx = p["USDTWD_Close"].shift(1)
    # Same-day price ratios use RAW quoted prices; returns use dividend-adjusted ones.
    taiwan_value_usd = p["TW2330_RawClose"] * ADR_RATIO / fx
    f["tw_ret_1d"] = pct(p["TW2330_Close"], 1)
    f["adr_premium"] = p["TSM_RawClose"] / taiwan_value_usd - 1
    f["adr_premium_vs_60d"] = f["adr_premium"] - f["adr_premium"].rolling(60).mean()
    f["twd_chg_20d"] = pct(fx, 20)
    return f[FEATURES]


# ==== SECTION: target ====
def make_target(panel, horizon=HORIZON):
    """The answer key: did TSM close higher `horizon` trading days later?"""
    close = panel["TSM_Close"]
    future_return = close.shift(-horizon) / close - 1      # looks AHEAD on purpose
    target = (future_return > 0).astype(float).where(future_return.notna())
    return future_return, target


def make_dataset(panel, horizon=HORIZON):
    """Features + answer key in one table. The last `horizon` rows have no answer yet."""
    X = build_features(panel).replace([np.inf, -np.inf], np.nan)
    future_return, target = make_target(panel, horizon)
    data = X.assign(future_return=future_return, target=target)
    return data.dropna(subset=FEATURES)     # drop the warm-up days


# ==== SECTION: models ====
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_models():
    """Two contenders: a simple, explainable model and a flexible 'black box'."""
    return {
        # A weighted checklist: each feature pushes the odds of UP up or down.
        "Logistic regression": make_pipeline(
            StandardScaler(), LogisticRegression(C=0.1, max_iter=1000)),
        # Hundreds of small decision trees, each correcting the last one's mistakes.
        "Gradient boosting": HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=50,
            l2_regularization=1.0, random_state=0),
    }


# ==== SECTION: walkforward ====
def walk_forward(data, model, min_train=MIN_TRAIN_DAYS, step=RETRAIN_EVERY, horizon=HORIZON):
    """Honest testing: train only on the past, predict the next block, roll forward."""
    labeled = data.dropna(subset=["target"])
    X, y = labeled[FEATURES], labeled["target"]
    prob_up = pd.Series(np.nan, index=labeled.index)
    for start in range(min_train, len(labeled), step):
        end = min(start + step, len(labeled))
        # Leave a 5-day gap: the last 5 training answers depend on prices that
        # fall inside the test block, so keeping them would leak the future.
        train_end = start - horizon
        fitted = clone(model).fit(X.iloc[:train_end], y.iloc[:train_end])
        prob_up.iloc[start:end] = fitted.predict_proba(X.iloc[start:end])[:, 1]
    return prob_up.dropna()


def make_flexible_model():
    """A very flexible model: 300 deep decision trees that can memorize fine detail."""
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=1, n_jobs=-1, random_state=0)


def split_test(data, model, shuffle, test_share=0.25, horizon=HORIZON):
    """Hold out 25% of the days for grading: SHUFFLED days (wrong) or the most RECENT 25% (right)."""
    from sklearn.model_selection import train_test_split
    labeled = data.dropna(subset=["target"])
    X, y = labeled[FEATURES], labeled["target"]
    if shuffle:
        # Tempting but WRONG: every test day has its neighbours in the training
        # set, and neighbouring days share 4 of the same 5 future days.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_share, shuffle=True, random_state=0)
    else:
        # Right: train on the past, grade on the most recent quarter of the data.
        cut = int(len(labeled) * (1 - test_share))
        X_train, y_train = X.iloc[:cut - horizon], y.iloc[:cut - horizon]
        X_test, y_test = X.iloc[cut:], y.iloc[cut:]
    fitted = clone(model).fit(X_train, y_train)
    return float((fitted.predict(X_test) == y_test).mean())


# ==== SECTION: evaluation ====
def run_walk_forward_suite(data, models=None):
    """Walk-forward calls for every model, plus two no-brain baselines.

    Returns (calls, probs): `calls` holds 1 = UP / 0 = DOWN for each strategy
    and the real outcome; `probs` holds each model's probability of UP.
    """
    models = models or make_models()
    labeled = data.dropna(subset=["target"])
    probs = pd.DataFrame({name: walk_forward(data, m) for name, m in models.items()}).dropna()
    calls = pd.DataFrame(index=probs.index)
    calls["Always up"] = 1
    calls["Momentum"] = (labeled.loc[probs.index, "ret_5d"] > 0).astype(int)
    for name in models:
        calls[name] = (probs[name] > 0.5).astype(int)
    calls["actual"] = labeled.loc[probs.index, "target"].astype(int)
    calls["future_return"] = labeled.loc[probs.index, "future_return"]
    return calls, probs


STRATEGIES = ["Always up", "Momentum", "Logistic regression", "Gradient boosting"]


def accuracy_table(calls):
    rows = []
    for s in STRATEGIES:
        hits = int((calls[s] == calls["actual"]).sum())
        n = len(calls)
        low, high = wilson_interval(hits, n)
        rows.append({"Strategy": s, "Accuracy": hits / n, "95% range low": low,
                     "95% range high": high, "Calls tested": n})
    return pd.DataFrame(rows).set_index("Strategy")


def accuracy_by_year(calls):
    hit = pd.DataFrame({s: (calls[s] == calls["actual"]) for s in STRATEGIES})
    return hit.groupby(hit.index.year).mean()


def wilson_interval(hits, n, overlap=HORIZON, z=1.96):
    """95% range for a hit rate (Wilson score interval).

    Calls made on neighbouring days share most of the same 5-day window, so
    their hits move together: n daily calls carry about as much evidence as
    n / 5 separate weeks. The range uses that smaller, honest sample size.
    """
    if n == 0:
        return float("nan"), float("nan")
    p = hits / n
    n = max(n / overlap, 1.0)
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def logistic_weights(data):
    """What the logistic model learned, fitted on all history with a known answer."""
    labeled = data.dropna(subset=["target"])
    model = clone(make_models()["Logistic regression"]).fit(labeled[FEATURES], labeled["target"])
    weights = pd.Series(model[-1].coef_[0], index=FEATURES)
    return weights.reindex(weights.abs().sort_values().index)


def backtest(signal, daily_return, cost=COST_PER_TRADE, horizon=HORIZON):
    """Turn UP/DOWN calls into a portfolio.

    Each day's call controls 1/5 of the money for 5 days ('5 sleeves'), so the
    holding period matches the 5-day prediction. A call made after today's close
    is traded at tomorrow's close: no instant trading at a price we only just saw.
    Money not in TSM sits in cash earning nothing. Every change of position pays
    COST_PER_TRADE.
    """
    position = signal.rolling(horizon, min_periods=horizon).mean()
    next_day = daily_return.shift(-2).reindex(position.index)   # decided at close t, earns t+1 -> t+2
    trading_cost = position.diff().abs() * cost
    out = pd.DataFrame({"position": position, "return": position * next_day - trading_cost})
    return out.dropna()


def run_backtests(calls, panel):
    daily = pct(panel["TSM_Close"], 1)
    results = {"Buy and hold TSM": backtest(calls["Always up"].astype(float), daily)}
    for name in ["Logistic regression", "Gradient boosting"]:
        results[name] = backtest(calls[name].astype(float), daily)
    return results


def performance_table(results, start_value=10_000):
    rows = []
    for name, r in results.items():
        growth = (1 + r["return"]).cumprod()
        years = len(r) / 252
        rows.append({
            "Strategy": name,
            f"${start_value:,} grows to": start_value * growth.iloc[-1],
            "Return per year": growth.iloc[-1] ** (1 / years) - 1,
            "Worst fall from a peak": (growth / growth.cummax() - 1).min(),
            "Time invested in TSM": r["position"].mean(),
        })
    return pd.DataFrame(rows).set_index("Strategy")


# ==== SECTION: plotting ====
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

INK, INK_2, INK_3, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
COLORS = {
    "Logistic regression": "#2a78d6",   # blue
    "Gradient boosting":   "#eb6834",   # orange
    "Momentum":            "#1baf7a",   # aqua
    "Always up":           "#8a8984",   # neutral gray = the baseline
    "Buy and hold TSM":    "#8a8984",
    "TSM":                 "#2a78d6",
}
UP_COLOR, DOWN_COLOR = "#2a78d6", "#e34948"   # diverging pair: blue = UP, red = DOWN
FLEX_COLOR = "#4a3aa7"                         # violet = the flexible random forest


def setup_style():
    plt.rcParams.update({
        "figure.figsize": (10, 4.2), "figure.dpi": 110,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": INK_2, "ytick.color": INK_2, "text.color": INK,
        "legend.frameon": False, "lines.linewidth": 2, "font.size": 10.5,
    })


def _pct_axis(ax, axis="y", decimals=0):
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_locator(mticker.MaxNLocator(steps=[1, 2, 5, 10]))
    target.set_major_formatter(mticker.PercentFormatter(1.0, decimals=decimals))


def _subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10, va="bottom")


def feature_table():
    """Every signal with its family and meaning, in full (plain pandas cuts long text short)."""
    table = pd.DataFrame(FEATURE_INFO, index=["Family", "Meaning"]).T
    return table.style.set_properties(**{"text-align": "left"})


def plot_price(panel):
    fig, ax = plt.subplots()
    ax.plot(panel.index, panel["TSM_Close"], color=COLORS["TSM"])
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5)))   # $5, $10, $20, $50, ...
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_title("TSM ADR price (dividend-adjusted, log scale)", pad=22)
    _subtitle(ax, "On a log scale, equal vertical distances mean equal % moves")
    plt.show()


def plot_adr_premium(data):
    fig, ax = plt.subplots()
    ax.plot(data.index, data["adr_premium"], color=COLORS["TSM"], linewidth=1.5)
    ax.axhline(0, color=INK_3, linewidth=1)
    _pct_axis(ax)
    ax.set_title("ADR premium: what US investors pay above the Taiwan shares", pad=22)
    _subtitle(ax, "TSM ADR price vs. 5 x (2330.TW price / USD-TWD rate)")
    plt.show()


def plot_return_histogram(data):
    r = data["future_return"].dropna()
    up_share = (r > 0).mean()
    fig, ax = plt.subplots()
    bins = np.linspace(-0.2, 0.2, 61)
    ax.hist(r[r <= 0].clip(-0.2), bins=bins, color=DOWN_COLOR, edgecolor=SURFACE, linewidth=0.5,
            label=f"DOWN weeks ({1 - up_share:.0%})")
    ax.hist(r[r > 0].clip(upper=0.2), bins=bins, color=UP_COLOR, edgecolor=SURFACE, linewidth=0.5,
            label=f"UP weeks ({up_share:.0%})")
    _pct_axis(ax, "x")
    ax.set_xlabel("TSM return over the next 5 trading days")
    ax.set_ylabel("Number of days")
    ax.legend(loc="upper left")
    ax.set_title("Every 5-day outcome since the start of the data", pad=22)
    _subtitle(ax, f"{up_share:.1%} of all weeks went UP. That is the score to beat by just saying 'UP'.")
    plt.show()


def plot_noise_scatter(data):
    d = data.dropna(subset=["target"])
    corr = d["ret_5d"].corr(d["future_return"])
    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    ax.scatter(d["ret_5d"], d["future_return"], s=8, alpha=0.35, color=COLORS["TSM"], linewidths=0)
    lim = 0.25
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.axhline(0, color=INK_3, linewidth=1); ax.axvline(0, color=INK_3, linewidth=1)
    _pct_axis(ax, "x"); _pct_axis(ax, "y")
    ax.set_xlabel("TSM return over the PAST 5 days")
    ax.set_ylabel("TSM return over the NEXT 5 days")
    ax.set_title("Is last week a clue for next week?", pad=22)
    _subtitle(ax, f"Correlation = {corr:+.2f}  (0 means no straight-line relationship)")
    plt.show()


def plot_walk_forward_scheme(n_folds=5):
    train_color, test_color = "#a3a29c", INK
    fig, ax = plt.subplots(figsize=(10, 2.9))
    for i in range(n_folds):
        y = n_folds - i
        train_len = 6 + i * 2
        ax.barh(y, train_len, left=0, height=0.55, color=train_color)
        ax.barh(y, 2, left=train_len + 0.6, height=0.55, color=test_color)
        ax.text(-0.3, y, f"Round {i + 1}", ha="right", va="center", color=INK_2)
    ax.text(0, n_folds + 0.62, "Train on the past", color=INK_2, fontweight="bold")
    ax.text(6.6, n_folds + 0.62, "Test on the next quarter", color=INK, fontweight="bold")
    ax.annotate("5-day gap", xy=(14.3, 0.7), xytext=(14.3, 0.05), ha="center", va="center",
                color=INK_2, fontsize=9, arrowprops=dict(arrowstyle="->", color=INK_2))
    ax.set_xlim(-2.5, 17.5); ax.set_ylim(-0.2, n_folds + 1.1)
    ax.axis("off")
    ax.set_title("Walk-forward testing: the model never sees the period it is graded on", pad=8)
    ax.annotate("time", xy=(5, 0.05), xytext=(0, 0.05), color=INK_2, va="center",
                arrowprops=dict(arrowstyle="->", color=INK_2))
    plt.show()


def _hbar_axes(ax, y, labels, values):
    for yi, v in zip(y, values):   # the background keeps a label readable where it crosses the 50% line
        ax.text(v + 0.004, yi, f"{v:.1%}", va="center", color=INK, fontweight="bold",
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))
    ax.axvline(0.5, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_ylim(min(y) - 0.95, max(y) + 0.5)
    ax.text(0.5, min(y) - 0.75, " coin flip (50%)", color=INK_2, va="center")
    ax.set_yticks(y, labels)
    ax.set_xlim(0.35, max(values) + 0.07)
    _pct_axis(ax, "x")
    ax.grid(axis="y", visible=False)


def plot_accuracy_bars(acc, title="How often each strategy called the week right (walk-forward test)"):
    names = list(acc.index)
    values = list(acc["Accuracy"])
    fig, ax = plt.subplots(figsize=(10, 0.7 * len(names) + 1.3))
    y = np.arange(len(names))[::-1]
    ax.barh(y, values, color=[COLORS[n] for n in names], height=0.6)
    _hbar_axes(ax, y, names, values)
    ax.set_title(title, pad=22)
    _subtitle(ax, "Every call was made on days the model had not seen. The bar to beat is grey "
                  "(always say UP), not the 50% line.")
    plt.show()


def plot_leakage(scores):
    """scores = {group: {"Shuffled days (wrong)": acc, "Time order (right)": acc}, ...}"""
    labels, values, y, pos = [], [], [], 0.0
    for group, results in scores.items():
        for method, v in results.items():
            labels.append(f"{group}: {method}"); values.append(v); y.append(pos); pos -= 0.8
        pos -= 0.6
    fig, ax = plt.subplots(figsize=(10, 0.65 * len(labels) + 1.6))
    for yi, label, v in zip(y, labels, values):
        wrong = "shuffled" in label.lower()
        ax.barh(yi, v, height=0.6, color="none" if wrong else FLEX_COLOR,
                edgecolor=FLEX_COLOR, hatch="///" if wrong else "", linewidth=1.2)
    _hbar_axes(ax, y, labels, values)
    ax.set_title("Same flexible model, two ways of grading it", pad=22)
    _subtitle(ax, "Hatched = shuffled days (wrong). Solid = train on the past, test on the future (right).")
    plt.show()


def plot_accuracy_by_year(by_year):
    fig, ax = plt.subplots()
    for s in ["Always up", "Logistic regression", "Gradient boosting"]:
        ax.plot(by_year.index, by_year[s], marker="o", markersize=6, color=COLORS[s], label=s,
                linestyle="--" if s == "Always up" else "-")
    ax.axhline(0.5, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    _pct_axis(ax)
    ax.set_xticks(by_year.index)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=3)
    ax.set_title("Accuracy year by year", pad=22)
    _subtitle(ax, "A model that wins in one market mood can lose in the next")
    plt.show()


def plot_logistic_weights(weights):
    fig, ax = plt.subplots(figsize=(10, 6.2))
    labels = [f"{k}  ({FEATURE_INFO[k][0]})" for k in weights.index]
    colors = [UP_COLOR if w > 0 else DOWN_COLOR for w in weights]
    ax.barh(labels, weights, color=colors, height=0.65)
    ax.axvline(0, color=INK, linewidth=1)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Weight (per 1 standard deviation of the feature)")
    ax.set_title("What the logistic model learned", pad=22)
    _subtitle(ax, "Blue bars push the call toward UP, red toward DOWN. Longer = stronger.")
    plt.show()


def plot_equity(results, start_value=10_000):
    fig, ax = plt.subplots()
    ends = {}
    for name, r in results.items():
        growth = start_value * (1 + r["return"]).cumprod()
        ax.plot(growth.index, growth, color=COLORS[name], label=name,
                linestyle="--" if name.startswith("Buy") else "-")
        ends[name] = (growth.index[-1], growth.iloc[-1])
    ax.set_yscale("log")
    # End-of-line value labels, nudged apart so they never overlap.
    lo, hi = np.log10(ax.get_ylim())
    min_gap = (hi - lo) * 0.06
    placed = []
    for name, (x, v) in sorted(ends.items(), key=lambda kv: kv[1][1]):
        pos = math.log10(v)
        if placed and pos - placed[-1] < min_gap:
            pos = placed[-1] + min_gap
        placed.append(pos)
        ax.text(x, 10 ** pos, f"  ${v:,.0f}", color=INK, va="center", fontsize=9.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.legend(loc="upper left")
    ax.set_title(f"What ${start_value:,} would have become (after 0.10% trading costs)", pad=22)
    _subtitle(ax, "Test period only. Every call made without seeing the future.")
    plt.show()


def show_prediction_card(as_of, close, probs, horizon=HORIZON):
    from IPython.display import HTML, display
    blocks = []
    for name, p in probs.items():
        call = "&#9650; UP" if p > 0.5 else "&#9660; DOWN"
        color = UP_COLOR if p > 0.5 else DOWN_COLOR
        blocks.append(
            f"<div style='flex:1;min-width:220px;border:1px solid {GRID};border-radius:10px;padding:14px 18px'>"
            f"<div style='color:{INK_2};font-size:13px'>{name}</div>"
            f"<div style='font-size:34px;font-weight:700;color:{color}'>{call}</div>"
            f"<div style='color:{INK};font-size:14px'>{p:.0%} chance of UP</div></div>")
    display(HTML(
        f"<div style='font-family:system-ui,sans-serif;color:{INK}'>"
        f"<div style='font-size:15px;margin-bottom:8px'>Based on the close of <b>{as_of:%a %d %b %Y}</b> "
        f"(TSM ${close:,.2f}): will TSM close higher {horizon} trading days later?</div>"
        f"<div style='display:flex;gap:12px;flex-wrap:wrap'>{''.join(blocks)}</div></div>"))


def plot_live_scorecard(log):
    done = scored_rows(log)
    if done.empty:
        print("No predictions have matured yet: each one needs 5 trading days.")
        return
    fig, ax = plt.subplots()
    x = pd.to_datetime(done["as_of_date"])
    for key, label in [("always_up", "Always up"), ("logistic", "Logistic regression"),
                       ("boosting", "Gradient boosting")]:
        running = done[f"hit_{key}"].astype(float).expanding().mean()
        ax.plot(x, running, color=COLORS[label], label=label, marker="o", markersize=5,
                linestyle="--" if key == "always_up" else "-")
    import matplotlib.dates as mdates
    ax.axhline(0.5, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_ylim(0, 1.02)
    _pct_axis(ax)
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Date of the call")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.18), ncol=3)
    ax.set_title("Live scorecard: running accuracy of real-time calls", pad=22)
    _subtitle(ax, f"{len(done)} calls scored so far, each logged BEFORE its outcome was known. "
                  "Dashed black line = coin flip.")
    return fig


# ==== SECTION: live ====
MODEL_KEYS = {"Logistic regression": "logistic", "Gradient boosting": "boosting"}
LOG_COLUMNS = [
    "as_of_date", "predicted_at_utc", "tsm_close",
    "prob_up_logistic", "prob_up_boosting",
    "call_logistic", "call_boosting", "call_always_up",
    "check_on_approx", "checked_on", "actual_return_5d", "actual",
    "hit_logistic", "hit_boosting", "hit_always_up",
]


def predict_latest(data, models=None):
    """Train on ALL history with a known answer, then call the newest day."""
    models = models or make_models()
    labeled = data.dropna(subset=["target"])
    latest = data.iloc[[-1]]
    probs = {}
    for name, m in models.items():
        fitted = clone(m).fit(labeled[FEATURES], labeled["target"])
        probs[name] = float(fitted.predict_proba(latest[FEATURES])[0, 1])
    return latest.index[0], probs


REQUIRED_LOG_COLUMNS = ["as_of_date", "tsm_close", "call_logistic", "call_boosting"]


def load_log(path):
    """Read the live log. Only a log that does not exist yet starts fresh. An empty,
    unreadable or wrongly-headed log fails loudly instead of being silently replaced
    (that would erase the track record)."""
    import urllib.error
    try:
        log = pd.read_csv(path, dtype={c: str for c in TEXT_COLUMNS})
    except (FileNotFoundError, urllib.error.URLError):
        return as_log_frame(pd.DataFrame(columns=LOG_COLUMNS))
    missing = [c for c in REQUIRED_LOG_COLUMNS if c not in log.columns]
    if missing:
        raise ValueError(f"{path} is missing columns {missing}: fix the file by hand, do not delete it.")
    return as_log_frame(log)


def scored_rows(log):
    return log.dropna(subset=["actual"]).reset_index(drop=True)


def score_log(log, panel, horizon=HORIZON):
    """Fill in the outcome of every prediction whose 5 trading days have passed."""
    log = as_log_frame(log)
    close = panel["TSM_Close"]
    dates = list(close.index.strftime("%Y-%m-%d"))
    for i, row in log.iterrows():
        if pd.notna(row["actual"]) or row["as_of_date"] not in dates:
            continue
        pos = dates.index(row["as_of_date"])
        if pos + horizon >= len(dates):
            continue                          # not matured yet
        # Use today's download for BOTH prices so dividend adjustments cancel out.
        ret = close.iloc[pos + horizon] / close.iloc[pos] - 1
        actual = "UP" if ret > 0 else "DOWN"
        log.loc[i, ["checked_on", "actual_return_5d", "actual"]] = [dates[pos + horizon], round(ret, 6), actual]
        for key in ["logistic", "boosting", "always_up"]:
            log.loc[i, f"hit_{key}"] = int(row[f"call_{key}"] == actual)
    return log


def update_log(log, panel, now=None):
    """Score matured calls, then add today's call if this close is not logged yet."""
    log = score_log(log, panel)
    data = make_dataset(panel)
    as_of, probs = predict_latest(data)
    as_of_str = as_of.strftime("%Y-%m-%d")
    if as_of_str in set(log["as_of_date"].astype(str)):
        return log, None
    now = now or pd.Timestamp.now(tz="UTC")
    row = {
        "as_of_date": as_of_str,
        "predicted_at_utc": now.strftime("%Y-%m-%d %H:%M"),
        "tsm_close": round(float(panel.loc[as_of, "TSM_RawClose"]), 4),
        "call_always_up": "UP",
        "check_on_approx": (as_of + pd.offsets.BDay(HORIZON)).strftime("%Y-%m-%d"),
    }
    for name, key in MODEL_KEYS.items():
        row[f"prob_up_{key}"] = round(probs[name], 4)
        row[f"call_{key}"] = "UP" if probs[name] > 0.5 else "DOWN"
    log.loc[len(log), list(row)] = list(row.values())
    return log, row


TEXT_COLUMNS = ["as_of_date", "predicted_at_utc", "call_logistic", "call_boosting",
                "call_always_up", "check_on_approx", "checked_on", "actual"]


def as_log_frame(log):
    """Same columns in the same order, text columns kept as text."""
    log = log.reindex(columns=LOG_COLUMNS).reset_index(drop=True)
    return log.astype({c: object for c in TEXT_COLUMNS})


def scorecard_table(log):
    done = scored_rows(log)
    rows = []
    for key, label in [("always_up", "Always up"), ("logistic", "Logistic regression"),
                       ("boosting", "Gradient boosting")]:
        hits, n = int(done[f"hit_{key}"].sum()) if len(done) else 0, len(done)
        low, high = wilson_interval(hits, n)
        rows.append({"Strategy": label, "Hits": hits, "Calls scored": n,
                     "Accuracy": hits / n if n else float("nan"),
                     "95% range low": low, "95% range high": high})
    return pd.DataFrame(rows).set_index("Strategy")


def write_scorecard(log, folder="."):
    """Write scorecard.md and scorecard.png for the weekly class update."""
    import os
    table = scorecard_table(log)
    latest = log.iloc[-1] if len(log) else None
    lines = ["# TSM 5-day call: live scorecard", ""]
    if latest is not None:
        lines += [f"**Latest call** (close of {latest['as_of_date']}, TSM ${float(latest['tsm_close']):,.2f}, "
                  f"result due about {latest['check_on_approx']}):", "",
                  f"- Logistic regression: **{latest['call_logistic']}** "
                  f"({float(latest['prob_up_logistic']):.0%} chance of UP)",
                  f"- Gradient boosting: **{latest['call_boosting']}** "
                  f"({float(latest['prob_up_boosting']):.0%} chance of UP)", ""]
    lines += ["## Accuracy so far", "",
              "| Strategy | Hits / scored | Accuracy | 95% range |", "|---|---|---|---|"]
    for name, r in table.iterrows():
        if r["Calls scored"]:
            lines.append(f"| {name} | {int(r['Hits'])} / {int(r['Calls scored'])} | {r['Accuracy']:.0%} | "
                         f"{r['95% range low']:.0%} to {r['95% range high']:.0%} |")
        else:
            lines.append(f"| {name} | 0 / 0 | n/a | n/a |")
    lines += ["", "The 95% range shows how much of the accuracy could be luck. Daily calls overlap "
              "(each covers 5 trading days), so the range treats N calls as about N/5 separate weeks.", "",
              "## Last 10 calls", "",
              "| Close of | Logistic | Boosting | Actual 5-day move |", "|---|---|---|---|"]
    for _, r in log.tail(10).iloc[::-1].iterrows():
        outcome = (f"{r['actual']} ({float(r['actual_return_5d']):+.1%})"
                   if pd.notna(r["actual"]) else "pending")
        lines.append(f"| {r['as_of_date']} | {r['call_logistic']} ({float(r['prob_up_logistic']):.0%}) | "
                     f"{r['call_boosting']} ({float(r['prob_up_boosting']):.0%}) | {outcome} |")
    lines += ["", "![Running accuracy](scorecard.png)", ""]
    with open(os.path.join(folder, "scorecard.md"), "w") as fh:
        fh.write("\n".join(lines))

    setup_style()
    fig = plot_live_scorecard(log)
    if fig is None:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, "Waiting for the first predictions to mature (5 trading days).",
                ha="center", va="center", color=INK_2, fontsize=12)
    fig.savefig(os.path.join(folder, "scorecard.png"), bbox_inches="tight")
    plt.close(fig)
