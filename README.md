# Project Overview

Market making is a core component of modern electronic markets, providing liquidity, reducing bid–ask spreads and enabling efficient trading.  
This applied project delivers a compact, modular simulator that tests quoting policies on real Binance Level-2 (L2) order book data.  
We compare a risk-aware Avellaneda–Stoikov (AS) model to a simple heuristic baseline (Naive Market Maker, NMM), focusing on implementation, calibration, and decision support.  
The system is built to be extensible, reproducible, and auditable, with both CLI and Streamlit UI for experiment configuration and visualization.  

---

# Project Structure

The project is organised into modular components, each serving a specific role in the simulator:

MM-LAB/
│
├── env/               # Environment configuration files  
├── figures/           # Plots and diagrams for the report  
├── logs/              # Simulation logs and output CSVs  
│   ├── BTCUSDT_L2.csv  
│   ├── ETHUSDT_L2.csv  
│   └── SOLUSDT_L2.csv  
├── results/           # Generated metrics, reports, visualisations  
├── scripts/           # Analysis and batch-processing scripts  
│   ├── evaluate_metrics.py  
│   ├── batch_compare.py  
│   └── case_study_stoikov.py  
├── simulator/         # Core replay and execution engine  
│   └── binance_l2_replay_sim.py  
├── strategy/          # Trading strategy implementations  
│   ├── execution.py  
│   ├── naive_mm.py  
│   └── stoikov.py  
├── streamlit_app/     # Web interface for running simulations  
│   ├── app.py  
│   ├── logic.py  
│   └── ui.py  
├── utils/             # Helper utilities  
│   └── binance_fetch.py  
├── main.py            # Main entry point  
├── requirements.txt   # Python dependencies  
└── run.sh             # Shell script for launching simulations  

---

# Client Specification

**Client:** Head of Electronic Market Making, Digital Assets Desk  
**Business Question:** For large-cap crypto pairs on Binance, which approach—AS or NMM—should be the default, and within which parameter ranges, once execution frictions and inventory limits are considered?  

**Scope**  
- **Assets:** BTCUSDT, ETHUSDT, SOLUSDT  
- **Data:** Historical Binance L2 snapshots with step-by-step replay; computed mid, spread, top-of-book sizes, and imbalance  
- **Strategies:** Avellaneda–Stoikov (γ: risk aversion, k: intensity) and Naive MM (base spread, volatility multipliers)  
- **Execution:** Probabilistic fills with slippage; order size caps; hard inventory bounds  

**Deliverables**  
1. Runnable tool (CLI + Streamlit UI) to configure, run, and visualise experiments on L2 data  
2. Side-by-side evaluation on multiple assets and parameter sets, with clear recommendations (when to prefer AS vs NMM)  
3. Reproducible artefacts per run (CSV metrics, PNG charts, config + seed)  

---

# Acceptance Criteria

- Deterministic replay (fixed seeds); 2,000 snapshots complete within minutes  
- Metrics: cumulative PnL, Sharpe Ratio, Sortino Ratio, maximum drawdown (USDT), inventory st.dev., average trade size, total trades, fill rate (%), turnover, average holding period  
- Documented calibration for γ, k (AS) and spreads (NMM); sensitivity analysis included  
- No live trading or exchange connectivity (simulation-only mode)  
- Reduced-form modelling of queue position, latency and hidden liquidity  
- Fixed evaluation windows to ensure auditability and comparability  
