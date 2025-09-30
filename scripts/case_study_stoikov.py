
import os
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from strategy.stoikov import StoikovStrategy
from simulator.binance_l2_replay_sim import BinanceL2ReplaySim
from utils.binance_fetch import collect_if_needed



symbol: str = "SOLUSDT"
csv_path: str = f"logs/{symbol}_l2.csv"
target_date: Optional[str] = None  

MIN_ROWS: int = 5000 


def ensure_l2_csv(path: str, sym: str, min_rows: int = 5000) -> None:
    if not os.path.exists(path) or os.path.getsize(path) < 100_000:
        print(f"File missing or small. Collecting fresh L2 data for {sym}...")
        collect_if_needed(sym, path, n_snapshots=1000, delay=0.2)
        return

    with open(path, "r") as f:
        line_count = sum(1 for _ in f)

    if line_count < min_rows:
        print(f"Only {line_count} rows found. Re-collecting...")
        collect_if_needed(sym, path, n_snapshots=1000, delay=0.2)


class FilteredSim(BinanceL2ReplaySim):

    def __init__(self, csv_path: str, target_date: Optional[str] = None) -> None:
        super().__init__(csv_path)
        if target_date:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            dates = pd.to_datetime(self.df["datetime"]).dt.date
            self.df = self.df[dates == target_dt].copy()
            print(f"Filtered {len(self.df)} rows for {target_date}")
        else:
            print(f"Using all {len(self.df)} rows (no date filter)")

        self.timestamps = sorted(self.df["timestamp"].unique())


def compute_pnl(
    trades: List[Any],
    mid_prices: List[float],
) -> Tuple[List[float], List[float]]:
    inventory: List[float], pnl: List[float] = [], []
    pos: float = 0.0
    cash: float = 0.0

    for i, mid in enumerate(mid_prices):
        ts_trades = [tr for tr in trades if getattr(tr, "ts", -1) == i]
        for tr in ts_trades:
            side = getattr(tr, "side", "")
            size = float(getattr(tr, "size", 0.0))
            price = float(getattr(tr, "price", 0.0))
            if side == "BID":
                pos += size
                cash -= price * size
            elif side == "ASK":
                pos -= size
                cash += price * size

        inventory.append(pos)
        pnl.append(cash + pos * float(mid))

    return pnl, inventory


def compute_additional_metrics(
    pnl: List[float],
    inventory: List[float],
    trades: List[Any],
    per_periods_per_day: int = 1440,
) -> Dict[str, Any]:
    
    pnl_arr = np.asarray(pnl, dtype=float)
    inv_arr = np.asarray(inventory, dtype=float)

    if pnl_arr.size < 2:
        return {
            "Final PnL": "0.00 USDT",
            "Sharpe Ratio": "0.00",
            "Sortino Ratio": "0.00",
            "Max Drawdown": "0.00 USDT",
            "Inventory Std": "0.00",
            "Avg Trade Size": "0.00",
            "Total Trades": len(trades),
        }

    returns = np.diff(pnl_arr)
    total_pnl = pnl_arr[-1]
    max_dd = float(np.max(np.maximum.accumulate(pnl_arr) - pnl_arr))

    ret_std = float(np.std(returns)) if returns.size else 0.0
    neg = returns[returns < 0]
    neg_std = float(np.std(neg)) if neg.size else 0.0

    ann = np.sqrt(per_periods_per_day)
    sharpe = (float(np.mean(returns)) / ret_std * ann) if ret_std > 0 else 0.0
    sortino = (float(np.mean(returns)) / neg_std * ann) if neg_std > 0 else 0.0

    inv_std = float(np.std(inv_arr))
    avg_trade_size = float(np.mean([float(getattr(tr, "size", 0.0)) for tr in trades])) if trades else 0.0

    return {
        "Final PnL": f"{total_pnl:.2f} USDT",
        "Sharpe Ratio": f"{sharpe:.2f}",
        "Sortino Ratio": f"{sortino:.2f}",
        "Max Drawdown": f"{max_dd:.2f} USDT",
        "Inventory Std": f"{inv_std:.2f}",
        "Avg Trade Size": f"{avg_trade_size:.2f}",
        "Total Trades": len(trades),
    }


def main() -> None:
    ensure_l2_csv(csv_path, symbol, MIN_ROWS)

    sim = FilteredSim(csv_path, target_date)

    mid_series = sim.mid_prices()
    if len(mid_series) < 3:
        print("Not enough data for simulation.")
        return

    log_returns = np.diff(np.log(np.asarray(mid_series, dtype=float)))
    sigma = float(np.std(log_returns) * np.sqrt(1440))

    stoikov = StoikovStrategy(
        sim=sim,
        gamma=0.1,
        k=1.2,
        sigma=sigma,
        terminal_time=True,
        adjust_delay=1,
        order_size=1.0,
        min_order_size=0.2,
        precision=2,
    )

    trades, _, updates, orders = stoikov.run()
    mid_prices = [float(u.price) for u in updates if getattr(u, "price", None) is not None]
    if not mid_prices:
        print("No updates with mid price. Check data.")
        return

    pnl, inventory = compute_pnl(trades, mid_prices)
    metrics = compute_additional_metrics(pnl, inventory, trades)

    print("\nAdditional Metrics:")
    for k, v in metrics.items():
        print(f"- {k}: {v}")

    print(f"\nCase Study: {symbol} on {target_date or 'ALL DATA'}")
    print(f"- Number of trades: {len(trades)}")
    print(f"- Max inventory: {max(inventory):.2f}")
    print(f"- Final PnL: {pnl[-1]:.2f} USDT")

    fig, axs = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    axs[0].plot(pnl, label="PnL")
    axs[0].set_ylabel("PnL")
    axs[0].set_title("Stoikov PnL")
    axs[0].grid(True)

    axs[1].plot(inventory, label="Inventory")
    axs[1].set_ylabel("Inventory")
    axs[1].set_title("Stoikov Inventory")
    axs[1].grid(True)

    plt.xlabel("Time Step")
    plt.tight_layout()

    os.makedirs("results", exist_ok=True)
    plot_path = f"results/{symbol}_pnl_inventory.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()

    metrics_path = f"results/{symbol}_metrics.csv"
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)

    print(f"\nPlot saved to {plot_path}")
    print(f"Metrics saved to {metrics_path}")


if __name__ == "__main__":
    main()
