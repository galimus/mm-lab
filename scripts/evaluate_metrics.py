
import os
from typing import List, Dict, Optional
from types import SimpleNamespace

import numpy as np
import pandas as pd


def evaluate_strategy_metrics(
    results: Dict[str, Dict[str, List]],
    return_df: bool = False,
    annualization: int = 252,
    save_path: str = "results/evaluation_metrics.csv",
    verbose: bool = True,
) -> Optional[pd.DataFrame]:
    

    def _safe_int(x, default=0) -> int:
        try:
            if x is None:
                return default
            return int(x)
        except Exception:
            return default

    def _infer_total_orders(d: Dict) -> int:
        if "total_orders" in d and d["total_orders"] is not None:
            return _safe_int(d["total_orders"], 0)

        orders = d.get("orders")
        if isinstance(orders, (list, tuple, dict)):
            return len(orders)

        updates = d.get("updates", [])
        if isinstance(updates, (list, tuple)):
            keys_place = {"place_order", "quote", "submit", "place", "new_order"}
            cnt = 0
            for u in updates:
                if isinstance(u, dict):
                    ev = (u.get("event") or u.get("type") or u.get("action") or "").lower()
                    if ev in keys_place:
                        cnt += 1
            if cnt > 0:
                return cnt

        quotes = d.get("quotes")
        if isinstance(quotes, (list, tuple)):
            return len(quotes)

        trades = d.get("trades") or []
        return len(trades)

    def _as_float_array(x) -> np.ndarray:
        try:
            arr = np.asarray(x, dtype=float)
            if arr.ndim == 0:
                arr = np.array([], dtype=float)
            return arr
        except Exception:
            return np.array([], dtype=float)

    def sharpe(pnl: List[float]) -> float:
        arr = _as_float_array(pnl)
        if arr.size < 2:
            return 0.0
        ret = np.diff(arr)
        std = np.std(ret)
        if not np.isfinite(std) or std == 0.0:
            return 0.0
        mean_ret = np.mean(ret)
        if not np.isfinite(mean_ret):
            return 0.0
        return float(mean_ret / std * np.sqrt(annualization))

    def max_drawdown(pnl: List[float]) -> float:
        arr = _as_float_array(pnl)
        if arr.size == 0:
            return 0.0
        roll_max = np.maximum.accumulate(arr)
        drawdowns = roll_max - arr
        return float(np.max(drawdowns)) if drawdowns.size else 0.0

    def fill_rate(trades: List[SimpleNamespace], total_orders: int) -> float:
        to = _safe_int(total_orders, 0)
        if to <= 0:
            return 0.0
        rate = (len(trades) / to) * 100.0
        return min(rate, 100.0)  

    def turnover(trades: List[SimpleNamespace]) -> float:
        return float(np.sum([abs(getattr(t, "size", 0.0) or 0.0) for t in (trades or [])]))

    def avg_holding_period(trades: List[SimpleNamespace]) -> float:
        if not trades or len(trades) < 2:
            return 0.0
        ts = []
        for t in trades:
            val = getattr(t, "ts", None) or getattr(t, "time", None)
            try:
                if isinstance(val, pd.Timestamp):
                    ts.append(val.value)
                elif isinstance(val, str):
                    ts.append(pd.Timestamp(val).value)
                elif isinstance(val, (int, float)):
                    ts.append(int(val))
            except Exception:
                continue

        if len(ts) < 2:
            return 0.0

        ts = np.sort(np.asarray(ts, dtype="int64"))
        diffs = np.diff(ts) / 1e9  
        return float(np.mean(diffs)) if diffs.size else 0.0

    rows = []
    for name, data in (results or {}).items():
        pnl = data.get("pnl") or []
        trades = data.get("trades") or []
        total_orders = _infer_total_orders(data)

        row = {
            "Strategy": name,
            "Sharpe Ratio": round(sharpe(pnl), 3),
            "Max Drawdown": round(max_drawdown(pnl), 2),
            "Fill Rate (%)": round(fill_rate(trades, total_orders), 2),
            "Turnover": round(turnover(trades), 2),
            "Avg Holding Period (sec)": round(avg_holding_period(trades), 2),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    df.to_csv(save_path, index=False)

    if verbose:
        print("Strategy Evaluation Table:")
        try:
            print(df.to_markdown(index=False))
        except Exception:
            print(df)
        print(f"\nSaved to {save_path}")

    return df if return_df else None
