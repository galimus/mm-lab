import sys
import argparse
import streamlit as st
from logic import run_strategy
from ui import (
    show_metrics,
    show_pnl_plot,
    show_inventory_plot,
    show_under_the_hood,
    download_metrics_csv,
)

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--debug_mode", type=int, default=0)
_args, _ = _parser.parse_known_args(sys.argv[1:])
DEFAULT_DEBUG = bool(_args.debug_mode)


st.set_page_config(
    page_title="Market Making Simulator",
    layout="wide",
)

#
CSS_STYLE = """
<style>
.stApp { background: #0f1218; }
[data-testid="stSidebar"] { background: #0b0e13; }
.mm-header { display:flex; align-items:center; gap:12px; }
.mm-badge {
  font-size:12px; padding:4px 10px; border-radius:999px;
  background: linear-gradient(135deg,#1f2937,#111827);
  border:1px solid #2a3342; color:#cbd5e1;
}
button[kind="primary"] {
  border-radius: 14px !important;
  border: 1px solid #273043 !important;
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
}
.kpi {
  background: linear-gradient(180deg, rgba(24,28,38,.9), rgba(15,18,24,.9));
  border: 1px solid #232a3a; border-radius: 18px; padding: 16px 18px;
}
.kpi .label { color:#9aa4b2; font-size:13px; margin-bottom:6px; }
.kpi .value { color:#e5e7eb; font-size:24px; font-weight:700; }
.kpi .sub { color:#8b95a7; font-size:12px; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
  background: #0c0f16; border: 1px solid #1f2736; border-radius: 12px;
}
.stTabs [aria-selected="true"] {
  border-color:#344055 !important;
  box-shadow: inset 0 0 0 1px #3b82f6;
}
</style>
"""
st.markdown(CSS_STYLE, unsafe_allow_html=True)

st.markdown(
    '<div class="mm-header">'
    '<h1 style="margin:0">Market Making Strategy Simulator</h1>'
    '<span class="mm-badge">Binance L2 · Real ticks</span>'
    '</div>',
    unsafe_allow_html=True
)
st.markdown("Simulate and compare **Stoikov** and **NaiveMM** strategies on real **Binance L2** data.")


c0, c1, c2, c3 = st.columns([1.1, 1.4, 1.0, 1.2])

with c0:
    symbol = st.selectbox(
        "Choose symbol",
        ["ETHUSDT", "BTCUSDT", "SOLUSDT"],
        index=0,
        key="symbol_select",
    )

with c1:
    strategy_choice = st.radio(
        "Choose strategies to run",
        ["Stoikov", "NaiveMM", "Both"],
        horizontal=True,
        key="strategy_choice",
    )

with c2:
    minutes = st.number_input(
        "Data window (minutes)",
        min_value=5, max_value=240, value=60, step=5,
        help="Use last X minutes from CSV.",
        key="minutes_input",
    )

with c3:
    max_ticks_in = st.number_input(
        "Max ticks (override)",
        min_value=0, max_value=1_000_000, value=0, step=10_000,
        help="If > 0, overrides minutes and uses the last N ticks.",
        key="max_ticks_input",
    )
    max_ticks = int(max_ticks_in) if max_ticks_in and max_ticks_in > 0 else None


st.sidebar.header("Strategy Parameters")

with st.sidebar.expander("Stoikov parameters", expanded=True):
    gamma = st.slider("Risk aversion (gamma)", 0.01, 1.00, 0.10, key="gamma_slider")
    k = st.slider("Market depth param (k)", 0.50, 2.00, 1.20, key="k_slider")
    stoikov_order_size = st.number_input(
        "Order size", min_value=0.10, max_value=10.00, value=1.00, step=0.10, key="stoikov_order_size"
    )

with st.sidebar.expander("NaiveMM parameters", expanded=True):
    base_spread = st.slider("Base spread", 0.10, 5.00, 1.50, key="base_spread_slider")
    vol_multiplier = st.slider("Volatility multiplier", 0.10, 5.00, 2.00, key="vol_multiplier_slider")
    naive_order_size = st.number_input(
        "Order size", min_value=0.10, max_value=10.00, value=1.00, step=0.10, key="naive_order_size"
    )

# CLI default applied here; user can still toggle it in the UI
debug = st.sidebar.toggle("Enable Debug Logs", value=DEFAULT_DEBUG, key="debug_toggle")


if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_context" not in st.session_state:
    st.session_state.last_context = ""

def kpi_card(col, label: str, value: str, sub: str = "") -> None:
    with col:
        st.markdown(
            f'<div class="kpi">'
            f'<div class="label">{label}</div>'
            f'<div class="value">{value}</div>'
            f'<div class="sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


run_clicked = st.button("Run Simulation", type="primary", use_container_width=True, key="run_button")

if run_clicked:
    context_str = f"{strategy_choice} · {symbol} · " + (f"{max_ticks:,} ticks" if max_ticks else f"{int(minutes)} min")
    st.info(f"Running {strategy_choice} on {symbol} — {context_str}")
    try:
        with st.spinner("Simulating..."):
            results = run_strategy(
                symbol=symbol,
                choice=strategy_choice,
                gamma=gamma,
                k=k,
                stoikov_order_size=stoikov_order_size,
                base_spread=base_spread,
                vol_multiplier=vol_multiplier,
                naive_order_size=naive_order_size,
                debug=bool(debug),
                minutes=int(minutes),
                max_ticks=max_ticks,
            )
        if not results:
            st.warning("No results produced. Try increasing the data window (minutes or ticks).")
            st.session_state.last_results = None
        else:
            st.session_state.last_results = results
            st.session_state.last_context = context_str
            st.success("Simulation complete.")
    except Exception as e:
        st.error(f"Simulation failed: {e}")
        st.session_state.last_results = None


results = st.session_state.last_results
if results:
    names = list(results.keys())
    finals = {}
    for name in names:
        try:
            finals[name] = float(results[name]["pnl"][-1])
        except Exception:
            finals[name] = float("nan")

    c1, c2, c3, c4 = st.columns(4)
    if "Stoikov" in finals:
        kpi_card(c1, "Stoikov — Final PnL", f"{finals['Stoikov']:.2f}", st.session_state.last_context)
    if "NaiveMM" in finals:
        kpi_card(c2, "NaiveMM — Final PnL", f"{finals['NaiveMM']:.2f}", st.session_state.last_context)

    if "Stoikov" in finals and "NaiveMM" in finals:
        winner = "Stoikov" if finals["Stoikov"] > finals["NaiveMM"] else "NaiveMM"
        edge = finals["Stoikov"] - finals["NaiveMM"]
        kpi_card(c3, "Winner", winner, f"Edge: {edge:+.2f}")

    kpi_card(c4, "Insights", "See tabs below", "PnL • Inventory • Metrics")

    tabs = st.tabs(["PnL over time", "Inventory", "Metrics", "Under the hood"])
    with tabs[0]:
        show_pnl_plot(results)
    with tabs[1]:
        show_inventory_plot(results)
    with tabs[2]:
        show_metrics(results)
        download_metrics_csv(results)
    with tabs[3]:
        show_under_the_hood()
else:
    st.caption("Run a simulation to see results.")
