import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.ticker import EngFormatter, FuncFormatter

# ------------- style helpers -------------
_PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756",
    "#72B7B2", "#EECA3B", "#B279A2", "#FF9DA6",
]

def _get_theme_colors():
    # auto-adjust to Streamlit theme
    base = st.get_option("theme.base") or "light"
    if base == "dark":
        return dict(
            fig_face="#0f1218", ax_face="#0f1218",
            grid="#2a3342", text="#d1d5db", spine="#39465e"
        )
    else:
        return dict(
            fig_face="#ffffff", ax_face="#ffffff",
            grid="#e5e7eb", text="#111827", spine="#9ca3af"
        )

def _pretty_axes(ax, colors):
    ax.set_facecolor(colors["ax_face"])
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(colors["spine"])
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=colors["text"], labelsize=10)
    ax.grid(True, which="major", linewidth=0.8, alpha=0.6, color=colors["grid"])
    ax.grid(True, which="minor", linewidth=0.5, alpha=0.35, color=colors["grid"])
    ax.minorticks_on()

def _fmt_signed(x, _pos=None):
    # neat signed formatting: +1.2k / -0.8k
    sign = "+" if x > 0 else ""
    return f"{sign}{EngFormatter()(x)}"

def _annotate_last(ax, x, y, color):
    if not x or not y:
        return
    ax.scatter([x[-1]], [y[-1]], s=28, zorder=5, edgecolor=color, facecolor="white", linewidth=1.2)
    ax.annotate(
        f"{_fmt_signed(y[-1])}",
        xy=(x[-1], y[-1]),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, alpha=0.85)
    )

# ---------- data helpers ----------
def _resample_and_smooth(times, values, every: str = "5S", ema_span: int = 20):
    """Uniform time grid + EMA smoothing for cleaner visuals."""
    if values is None or len(values) == 0:
        return [], []
    if times is None or len(times) != len(values):
        s = pd.Series(values)
    else:
        idx = pd.to_datetime(times)
        s = pd.Series(values, index=idx).sort_index()
        try:
            s = s.resample(every).ffill().interpolate("time")
        except Exception:
            pass  

    if ema_span and ema_span > 1 and len(s) > 3:
        s = s.ewm(span=ema_span, adjust=False).mean()

    if isinstance(s.index, pd.DatetimeIndex):
        x = s.index.to_pydatetime().tolist()
    else:
        x = list(range(len(s)))
    return x, s.values.tolist()

# ---------- plots ----------
def show_pnl_plot(results):
    st.subheader("PnL Over Time")

    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        every = st.selectbox("Resample", ["1S", "2S", "5S", "10S", "30S", "1T"], index=2, key="pnl_every")
    with c2:
        ema_span = st.slider("EMA span", 1, 100, 20, key="pnl_span")
    with c3:
        show_labels = st.checkbox("Show last labels", True, key="pnl_labels")
    with c4:
        show_drawdown = st.checkbox("Shade drawdown", True, key="pnl_dd")

    colors = _get_theme_colors()
    fig, ax = plt.subplots(figsize=(12, 4), facecolor=colors["fig_face"])
    _pretty_axes(ax, colors)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: _fmt_signed(x)))

    any_data = False
    for i, (name, res) in enumerate(results.items()):
        x_raw = res.get("time")
        y_raw = res.get("pnl", [])
        x, y = _resample_and_smooth(x_raw, y_raw, every=every, ema_span=ema_span)
        if not x:
            continue
        any_data = True
        color = _PALETTE[i % len(_PALETTE)]
        ax.plot(x, y, label=name, linewidth=2.0, color=color)
        if show_drawdown and len(y) > 3:
            # drawdown shading from running max
            y_arr = np.asarray(y)
            roll_max = np.maximum.accumulate(y_arr)
            ax.fill_between(x, y_arr, roll_max, where=y_arr < roll_max, alpha=0.12, color=color, linewidth=0)

        if show_labels:
            _annotate_last(ax, x, y, color)

    ax.axhline(0, linewidth=1, alpha=0.5, color=colors["spine"])
    ax.set_xlabel("Time", color=colors["text"])
    ax.set_ylabel("PnL", color=colors["text"])
    ax.legend(frameon=False, ncol=min(3, len(results)))
    if any_data:
        fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

def show_inventory_plot(results):
    st.subheader("Inventory Over Time")

    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        every = st.selectbox("Resample", ["1S", "2S", "5S", "10S", "30S", "1T"], index=2, key="inv_every")
    with c2:
        ema_span = st.slider("EMA span", 1, 100, 20, key="inv_span")
    with c3:
        show_labels = st.checkbox("Show last labels", True, key="inv_labels")
    with c4:
        band = st.slider("Neutral band ±", 0, 100, 5, key="inv_band")  # inventory units

    colors = _get_theme_colors()
    fig, ax = plt.subplots(figsize=(12, 4), facecolor=colors["fig_face"])
    _pretty_axes(ax, colors)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: _fmt_signed(x)))

    # neutral band around zero
    if band > 0:
        ax.axhspan(-band, band, color="#9ca3af", alpha=0.15, zorder=0)

    any_data = False
    for i, (name, res) in enumerate(results.items()):
        x_raw = res.get("time")
        y_raw = res.get("inventory", [])
        x, y = _resample_and_smooth(x_raw, y_raw, every=every, ema_span=ema_span)
        if not x:
            continue
        any_data = True
        color = _PALETTE[i % len(_PALETTE)]
        ax.plot(x, y, label=name, linewidth=2.0, color=color)
        # light area under curve
        ax.fill_between(x, y, 0, alpha=0.08, color=color, linewidth=0)
        if show_labels:
            _annotate_last(ax, x, y, color)

    ax.axhline(0, linewidth=1, alpha=0.5, color=colors["spine"])
    ax.set_xlabel("Time", color=colors["text"])
    ax.set_ylabel("Inventory (units)", color=colors["text"])
    ax.legend(frameon=False, ncol=min(3, len(results)))
    if any_data:
        fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)

# ---------- metrics & misc ----------
def show_metrics(results):
    st.subheader("Strategy Evaluation")
    from scripts.evaluate_metrics import evaluate_strategy_metrics
    df = evaluate_strategy_metrics(results, return_df=True)
    if df is None or df.empty:
        st.info("No metrics to display.")
        return
    # Round numerics, leave strings untouched
    df_numeric = df.select_dtypes(include=["number"]).round(6)
    df[df_numeric.columns] = df_numeric
    st.dataframe(df, use_container_width=True)


def download_metrics_csv(results):
    from scripts.evaluate_metrics import evaluate_strategy_metrics
    df = evaluate_strategy_metrics(results, return_df=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Metrics CSV", csv, "strategy_metrics.csv", use_container_width=True)

def show_under_the_hood():
    st.markdown("---")
    st.markdown("### What’s happening under the hood?")
    st.markdown("""
- Strategies: Stoikov (risk-aware), NaiveMM (fixed spread).
- Execution: Binance/Bybit L2 replay; latency and fill model are parameterized.
- PnL: cash + inventory × mid.
- Visuals: uniform time grid, EMA smoothing, drawdown shading, inventory neutral band.
    """)
