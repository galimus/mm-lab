
import numpy as np
import bisect
from collections import defaultdict
from typing import List, Optional, Tuple, Dict, Any

from simulator.binance_l2_replay_sim import BinanceL2ReplaySim
from strategy.stoikov import StoikovStrategy
from strategy.naive_mm import NaiveMMStrategy
from utils.binance_fetch import collect_if_needed



SIDE_BUY  = {"BID", "BUY", "BUY_LIMIT", "BUY_MARKET", "LONG"}
SIDE_SELL = {"ASK", "SELL", "SELL_LIMIT", "SELL_MARKET", "SHORT"}

def _trade_sign(side: Any) -> int:
    s = (str(side).upper() if side is not None else "")
    if s in SIDE_BUY:  return +1
    if s in SIDE_SELL: return -1
    return 0


def compute_sigma_from_mid(mid_series) -> float:
    arr = mid_series.dropna().values
    if len(arr) < 3:
        return 0.0
    log_ret = np.diff(np.log(arr))
    return float(np.std(log_ret) * np.sqrt(1440))  # minute → daily


def _trade_sign(side: Any) -> int:
    s = (str(side).upper() if side is not None else "")
    if s in SIDE_BUY:  return +1
    if s in SIDE_SELL: return -1
    return 0

def _to_epoch(x) -> float:
 
    try:
        if hasattr(x, "timestamp"):
            return float(x.timestamp())
        if hasattr(x, "value"):
            return float(x.value) / 1e9
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return np.nan

def compute_inventory_pnl(
    trades: List[Any],
    times: List[Any],                  
    mid_prices: List[Optional[float]],
) -> Tuple[List[float], List[float]]:
    n = len(mid_prices)
    assert len(times) == n and n > 0, "len(times) must match len(mid_prices) and be > 0"

   
    times_arr = np.array([_to_epoch(t) for t in times], dtype=float)
    if not np.all(np.isfinite(times_arr)):
        mask = np.isfinite(times_arr)
        times_arr[~mask] = np.interp(np.flatnonzero(~mask), np.flatnonzero(mask), times_arr[mask])

    mp = np.array(mid_prices, dtype=float)
    if not np.isfinite(mp[0]):
        idx = np.where(np.isfinite(mp))[0]
        if len(idx):
            mp[0] = mp[idx[0]]
    for i in range(1, n):
        if not np.isfinite(mp[i]):
            mp[i] = mp[i-1]

    by_idx = defaultdict(list)
    last_idx_count = 0
    unknown_side = 0

    for tr in trades:
        idx = None
        ts = getattr(tr, "ts", None)
        tt = getattr(tr, "time", None) or getattr(tr, "timestamp", None)

        if isinstance(ts, int) and 0 <= ts < n:
            idx = ts
        else:
            if ts is not None:
                ts_num = _to_epoch(ts)
                if np.isfinite(ts_num):
                    j = bisect.bisect_left(times_arr.tolist(), ts_num)
                    idx = min(max(0, j), n-1)

        if idx is None and tt is not None:
            tt_num = _to_epoch(tt)
            if np.isfinite(tt_num):
                j = bisect.bisect_left(times_arr.tolist(), tt_num)
                idx = min(max(0, j), n-1)

        if idx is None:
            idx = n - 1
            last_idx_count += 1

        by_idx[idx].append(tr)

    pos, cash = 0.0, 0.0
    inventory, pnl = [], []
    for i in range(n):
        for tr in by_idx.get(i, []):
            sign = _trade_sign(getattr(tr, "side", None))
            size = float(getattr(tr, "size", 0.0))
            price = float(getattr(tr, "price", 0.0))
            if sign == +1:
                pos += size
                cash -= price * size
            elif sign == -1:
                pos -= size
                cash += price * size
            else:
                unknown_side += 1
        inventory.append(pos)
        pnl.append(cash + pos * float(mp[i]))

    if last_idx_count > 0:
        print(f"[WARN] {last_idx_count} trades mapped to last tick (ts/times mismatch likely)")
    if unknown_side > 0:
        print(f"[WARN] {unknown_side} trades with unknown side")

    return inventory, pnl

def smooth_series(series: List[float], window: int = 20) -> List[float]:
    if window <= 1 or len(series) < 3:
        return series
    arr = np.asarray(series, dtype=float)
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same").tolist()



def run_strategy(symbol: str,
                 choice: str,
                 gamma: float,
                 k: float,
                 stoikov_order_size: float,
                 base_spread: float,
                 vol_multiplier: float,
                 naive_order_size: float,
                 debug: bool = False,
                 minutes: int = 60,
                 max_ticks: Optional[int] = None,
                 smooth_window: int = 20) -> Dict[str, Dict[str, Any]]:

    csv_path = f"logs/{symbol}_l2.csv"
    collect_if_needed(symbol, csv_path)

    sim_sigma = BinanceL2ReplaySim(csv_path, minutes=minutes, max_ticks=max_ticks)
    mid_series = sim_sigma.mid_prices()
    sigma = compute_sigma_from_mid(mid_series)

    results: Dict[str, Dict[str, Any]] = {}

    if choice in ("Stoikov", "Both"):
        sim_s = BinanceL2ReplaySim(csv_path, minutes=minutes, max_ticks=max_ticks)

        gamma_t  = max(1e-4, float(gamma))
        k_t      = max(1e-4, float(k))
        order_sz = max(0.1, float(stoikov_order_size))

        stoikov = StoikovStrategy(
            sim=sim_s,
            gamma=gamma_t,
            k=k_t,
            sigma=sigma,
            terminal_time=True,
            adjust_delay=1,
            order_size=order_sz,
            min_order_size=0.01,
            precision=3
        )
        trades_s, _, updates_s, orders_s = stoikov.run()

        if len(trades_s) == 0:
            if debug:
                print("[STOIKOV] No fills → retry with tighter quotes")
            sim_s = BinanceL2ReplaySim(csv_path, minutes=minutes, max_ticks=max_ticks)
            stoikov = StoikovStrategy(
                sim=sim_s,
                gamma=gamma_t * 0.5,
                k=k_t * 0.6,
                sigma=sigma,
                terminal_time=True,
                adjust_delay=1,
                order_size=max(0.1, order_sz * 0.5),
                min_order_size=0.01,
                precision=3
            )
            trades_s, _, updates_s, orders_s = stoikov.run()

        times_s = sim_s.ticks_time()
        mid_prices_s = list(sim_s.mid_prices())
        inv_s, pnl_s = compute_inventory_pnl(trades_s, times_s, mid_prices_s)

        if debug:
            print("\n[STOIKOV DEBUG]")
            print("sigma:", sigma)
            print("ticks:", len(times_s))
            print("mid non-NaN:", sum(1 for m in mid_prices_s if m is not None))
            print("orders:", 0 if orders_s is None else len(orders_s))
            print("trades:", len(trades_s))
            if trades_s:
                t0 = trades_s[0]
                print("sample trade:", dict(
                    side=getattr(t0, "side", None),
                    size=float(getattr(t0, "size", 0.0)),
                    price=float(getattr(t0, "price", 0.0)),
                    ts=getattr(t0, "ts", None),
                    time=getattr(t0, "time", None) or getattr(t0, "timestamp", None),
                ))

        results["Stoikov"] = {
            "time": times_s,
            "pnl": smooth_series(pnl_s, smooth_window),
            "inventory": smooth_series(inv_s, smooth_window),
            "trades": trades_s,
            "total_orders": len(orders_s) if orders_s is not None else None
        }

    if choice in ("NaiveMM", "Both"):
        sim_n = BinanceL2ReplaySim(csv_path, minutes=minutes, max_ticks=max_ticks)
        naive = NaiveMMStrategy(
            sim=sim_n,
            base_spread=base_spread,
            volatility_multiplier=vol_multiplier,
            order_size=naive_order_size,
            max_inventory=5.0,
            precision=2
        )
        orders_n = None
        try:
            trades_n, mid_prices_n, orders_n = naive.run(return_orders=True)
        except TypeError:
            out = naive.run()
            if len(out) == 3:
                trades_n, mid_prices_n, orders_n = out
            else:
                trades_n, mid_prices_n = out

        times_n = sim_n.ticks_time()
        mid_prices_full_n = list(sim_n.mid_prices())
        inv_n, pnl_n = compute_inventory_pnl(trades_n, times_n, mid_prices_full_n)

        results["NaiveMM"] = {
            "time": times_n,
            "pnl": smooth_series(pnl_n, smooth_window),
            "inventory": smooth_series(inv_n, smooth_window),
            "trades": trades_n,
            "total_orders": len(orders_n) if orders_n is not None else None
        }

    if debug:
        def _brief(res):
            return {
                "points": len(res.get("pnl", [])),
                "orders": res.get("total_orders"),
                "trades": len(res.get("trades", []))
            }
        print("[DEBUG] sigma:", sigma)
        print("[DEBUG] Stoikov:", _brief(results.get("Stoikov", {})))
        print("[DEBUG] NaiveMM:", _brief(results.get("NaiveMM", {})))

    return results
