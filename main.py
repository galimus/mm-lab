
import argparse
import os
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import matplotlib.pyplot as plt

from strategy.stoikov import StoikovStrategy
from strategy.naive_mm import NaiveMMStrategy
from simulator.binance_l2_replay_sim import BinanceL2ReplaySim
from scripts.evaluate_metrics import evaluate_strategy_metrics
from utils.binance_fetch import collect_if_needed


try:
    from scipy.ndimage import gaussian_filter1d
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def _moving_avg(x: List[float], k: int = 7) -> np.ndarray:

    if k <= 1 or len(x) < k:
        return np.asarray(x, dtype=float)
    c = np.cumsum(np.r_[0.0, x], dtype=float)
    y = (c[k:] - c[:-k]) / k
    pad_left = [y[0]] * (k // 2)
    pad_right = [y[-1]] * (len(x) - len(y) - len(pad_left))
    return np.r_[pad_left, y, pad_right]


def _smooth(arr: List[float], sigma: int = 2, ma_window: int = 7) -> np.ndarray:
   
    a = np.asarray(arr, dtype=float)
    if _HAS_SCIPY and sigma and sigma > 0:
        return gaussian_filter1d(a, sigma=sigma)
    return _moving_avg(a.tolist(), k=ma_window)


def _remove_roundtrips_same_tick(trades: List[Any]) -> List[Any]:
   
    cleaned: List[Any] = []
    last_ts: Optional[int] = None
    taken_side: Optional[str] = None
    for tr in trades:
        ts = getattr(tr, "ts", None)
        side = getattr(tr, "side", None)
        if ts != last_ts:
            last_ts = ts
            taken_side = None
        if taken_side is None or side == taken_side:
            cleaned.append(tr)
            taken_side = side
    return cleaned


def compute_pnl(trades: List[Any], mid_prices: List[float]) -> Tuple[List[float], List[float]]:
    inventory, pnl = [], []
    pos, cash = 0.0, 0.0

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


def main(
    strategy_name: str,
    symbol: str,
    collect_data: bool,
    minutes: Optional[int] = None,
    max_ticks: Optional[int] = None,
    snapshots: int = 1000,
    delay: float = 0.05,
) -> None:
    csv_path = f"logs/{symbol}_l2.csv"

    if collect_data:
        collect_if_needed(symbol, csv_path, n_snapshots=snapshots, delay=delay)

    use_minutes = None if (minutes is None or minutes <= 0) else minutes

    sim_for_sigma = BinanceL2ReplaySim(csv_path, minutes=use_minutes, max_ticks=max_ticks)
    mid_series = sim_for_sigma.mid_prices()
    print(f"Loaded {len(mid_series)} mid prices")
    if len(mid_series) < 2:
        print("Not enough mid prices to compute volatility.")
        return

    mid_vals = np.asarray([m for m in mid_series if m is not None], dtype=float)
    log_returns = np.diff(np.log(mid_vals))
    sigma = float(np.std(log_returns) * np.sqrt(1440))
    print(f"Estimated sigma = {sigma:.5f}")

    results: Dict[str, Dict[str, Any]] = {}
    outdir = f"figures/{symbol}"
    os.makedirs(outdir, exist_ok=True)

    if strategy_name in ["stoikov", "both"]:
        stoikov = StoikovStrategy(
            sim=BinanceL2ReplaySim(csv_path, minutes=use_minutes, max_ticks=max_ticks),
            gamma=0.01,
            k=0.5,
            sigma=sigma,
            terminal_time=True,
            adjust_delay=1,
            order_size=1.0,
            min_order_size=0.2,
            precision=2,
        )
        trades_s, _, updates_s, orders_s = stoikov.run()
        trades_s = _remove_roundtrips_same_tick(trades_s)
        mid_prices_s = [float(u.price) for u in updates_s if getattr(u, "price", None) is not None]
        pnl_s, inv_s = compute_pnl(trades_s, mid_prices_s)
        results["Stoikov"] = {
            "pnl": pnl_s,
            "inventory": inv_s,
            "trades": trades_s,
            "total_orders": len(orders_s),
        }

    if strategy_name in ["naivemm", "both"]:
        naive = NaiveMMStrategy(
            sim=BinanceL2ReplaySim(csv_path, minutes=use_minutes, max_ticks=max_ticks),
            base_spread=4.0,            # шире базовый спред
            volatility_multiplier=1.0,  # мягче адаптация к воле
            order_size=0.2,             # меньше размер заявки
            max_inventory=6.0,
            precision=2,
        )
        trades_n, mid_prices_n = naive.run()
        trades_n = _remove_roundtrips_same_tick(trades_n)
        mid_prices_n = [float(p) for p in mid_prices_n if p is not None]
        pnl_n, inv_n = compute_pnl(trades_n, mid_prices_n)
        results["NaiveMM"] = {
            "pnl": pnl_n,
            "inventory": inv_n,
            "trades": trades_n,
            "total_orders": len(mid_prices_n),
        }

    if "Stoikov" in results and "NaiveMM" in results:
        # Matplotlib defaults for a clean look
        plt.rcParams.update(
            {
                "figure.facecolor": "white",
                "axes.grid": True,
                "grid.alpha": 0.25,
                "legend.frameon": True,
                "legend.framealpha": 0.9,
                "legend.edgecolor": "#e5e7eb",
                "lines.linewidth": 2.4,
                "font.family": "DejaVu Serif",
            }
        )

        pnl_s = np.asarray(results["Stoikov"]["pnl"], dtype=float)
        pnl_n = np.asarray(results["NaiveMM"]["pnl"], dtype=float)
        pnl_s = pnl_s - pnl_s[0]
        pnl_n = pnl_n - pnl_n[0]
        pnl_s_sm = _smooth(pnl_s, sigma=2, ma_window=7)
        pnl_n_sm = _smooth(pnl_n, sigma=2, ma_window=7)

        plt.figure(figsize=(12, 5.5))
        plt.plot(pnl_s_sm, label="Stoikov PnL")
        plt.plot(pnl_n_sm, label="NaiveMM PnL")
        plt.title(f"PnL Comparison — {symbol}")
        plt.xlabel("Time (updates)")
        plt.ylabel("PnL (normalized to t0)")
        plt.legend(loc="best")

        idx_max_s = int(np.argmax(pnl_s_sm))
        val_max_s = float(pnl_s_sm[idx_max_s])
        plt.scatter(idx_max_s, val_max_s, s=60, zorder=5)
        plt.annotate(
            "Max PnL (Stoikov)",
            xy=(idx_max_s, val_max_s),
            xytext=(idx_max_s + max(10, len(pnl_s_sm) // 20), val_max_s * 1.02),
            arrowprops=dict(arrowstyle="->"),
            fontsize=10,
        )

        idx_min_n = int(np.argmin(pnl_n_sm))
        val_min_n = float(pnl_n_sm[idx_min_n])
        plt.scatter(idx_min_n, val_min_n, s=60, zorder=5)
        plt.annotate(
            "Drawdown (NaiveMM)",
            xy=(idx_min_n, val_min_n),
            xytext=(idx_min_n + max(10, len(pnl_n_sm) // 20), val_min_n * 1.02),
            arrowprops=dict(arrowstyle="->"),
            fontsize=10,
        )

        plt.tight_layout()
        plt.savefig(f"{outdir}/pnl_comparison.png", dpi=300, bbox_inches="tight")
        plt.close()

        inv_s = _smooth(results["Stoikov"]["inventory"], sigma=1, ma_window=5)
        inv_n = _smooth(results["NaiveMM"]["inventory"], sigma=1, ma_window=5)
        plt.figure(figsize=(12, 5.2))
        plt.plot(inv_s, label="Stoikov Inventory")
        plt.plot(inv_n, label="NaiveMM Inventory")
        plt.title(f"Inventory Comparison — {symbol}")
        plt.xlabel("Time (updates)")
        plt.ylabel("Inventory (units)")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.25)
        plt.tight_layout()
        plt.savefig(f"{outdir}/inventory_comparison.png", dpi=300, bbox_inches="tight")
        plt.close()

    evaluate_strategy_metrics(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run and compare market-making strategies.")
    parser.add_argument("--strategy", type=str, choices=["stoikov", "naivemm", "both"], required=True)
    parser.add_argument("--symbol", type=str, default="ETHUSDT")
    parser.add_argument("--collect_data", action="store_true")
    parser.add_argument("--minutes", type=int, default=60, help="Use last X minutes from CSV (0 = all)")
    parser.add_argument("--max_ticks", type=int, default=None, help="Or use last N ticks (overrides minutes)")
    parser.add_argument("--snapshots", type=int, default=800, help="Snapshots to collect when --collect_data")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay (s) between snapshots during collection")
    args = parser.parse_args()

    main(
        strategy_name=args.strategy,
        symbol=args.symbol,
        collect_data=args.collect_data,
        minutes=args.minutes,
        max_ticks=args.max_ticks,
        snapshots=args.snapshots,
        delay=args.delay,
    )
