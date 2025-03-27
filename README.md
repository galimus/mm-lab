##  Project Overview

This project implements a  market-making simulator using the Avellaneda-Stoikov model. It uses real historical OHLCV data (e.g., BTCUSDT) and simulates probabilistic execution of limit orders. The goal is to study inventory risk, PnL dynamics, and quoting behavior under real market conditions.

##  Key Files

- `main.py` – Runs the Stoikov strategy simulation and plots mid price, inventory, and PnL.
- `strategy/stoikov.py` – Avellaneda-Stoikov implementation with inventory control and optimal quoting logic.
- `simulator/real_data_sim.py` – Market simulator using real OHLCV data with execution model based on distance to mid-price.
- `BTCUSDT_1min.csv` – Historical market data used as input for the simulation.
- `README.md` – Project description and usage guide.
- `results/` – Folder to store visualizations, logs, and (planned) trade/PnL exports.
- `grid_search.py` (planned) – Hyperparameter tuning for gamma and k.
- `notebooks/eda.ipynb` (planned) – Exploratory data analysis and strategy visualization.
- `config.json` (planned) – Centralized strategy parameter config file.
