import pandas as pd
import numpy as np
from types import SimpleNamespace
from strategy.execution import ExecutionModel

class BinanceL2ReplaySim:
    def __init__(self, csv_path, level_volume=5, level_latency=0.1,
                 minutes=None, max_ticks=None,
                 demo_fills=True, demo_passive_threshold=5e-4):
       
        self.df = pd.read_csv(csv_path)

        if "datetime" in self.df.columns:
            self.df["datetime"] = pd.to_datetime(self.df["datetime"], errors="coerce")

        self.df = self.df.sort_values("timestamp").reset_index(drop=True)

        if minutes is not None and max_ticks is None and "datetime" in self.df.columns:
            last_dt = self.df["datetime"].dropna().max()
            if pd.notna(last_dt):
                cutoff = last_dt - pd.Timedelta(minutes=int(minutes))
                self.df = self.df[self.df["datetime"] >= cutoff].copy()

        snapshots = list(self.df.groupby("timestamp", sort=True))
        if max_ticks is not None:
            max_ticks = int(max_ticks)
            snapshots = snapshots[-max_ticks:] if max_ticks > 0 else snapshots

        self.snapshots = snapshots
        self.t = 0

        self.execution_model = ExecutionModel()
        self.level_volume = level_volume
        self.level_latency = level_latency

        self.demo_fills = bool(demo_fills)
        self.demo_passive_threshold = float(demo_passive_threshold)

    def reset(self):
        self.t = 0

    def tick(self):
        if self.t >= len(self.snapshots):
            return self.t, None

        ts_val, snapshot_df = self.snapshots[self.t]
        self.t += 1

        best_bid = snapshot_df[snapshot_df["side"] == "bid"]["price"].max()
        best_ask = snapshot_df[snapshot_df["side"] == "ask"]["price"].min()
        mid_price = (
            (best_bid + best_ask) / 2
            if pd.notna(best_bid) and pd.notna(best_ask) else None
        )

        update = SimpleNamespace(
            receive_ts=ts_val,
            price=mid_price,
            bid_price=best_bid,
            ask_price=best_ask,
            type="md",
        )
        return self.t, [update]

    def place_order(self, ts, size, side, price):
 
        if ts == 0 or ts >= len(self.snapshots):
            return self._limit_order(ts, size, side, price)

        _, prev_df = self.snapshots[ts - 1]
        _, cur_df  = self.snapshots[ts]

        prev_best_bid = prev_df[prev_df["side"] == "bid"]["price"].max()
        prev_best_ask = prev_df[prev_df["side"] == "ask"]["price"].min()
        cur_best_bid  = cur_df[cur_df["side"] == "bid"]["price"].max()
        cur_best_ask  = cur_df[cur_df["side"] == "ask"]["price"].min()

        mid     = (prev_best_bid + prev_best_ask) / 2 if pd.notna(prev_best_bid) and pd.notna(prev_best_ask) else np.nan
        new_mid = (cur_best_bid + cur_best_ask) / 2 if pd.notna(cur_best_bid) and pd.notna(cur_best_ask) else np.nan

       
        if self.demo_fills and pd.notna(cur_best_bid) and pd.notna(cur_best_ask):
            if side == "BID" and price >= cur_best_ask:
                return SimpleNamespace(order_id=ts, ts=ts, side=side, size=size,
                                       price=float(cur_best_ask), type="own_trade")
            if side == "ASK" and price <= cur_best_bid:
                return SimpleNamespace(order_id=ts, ts=ts, side=side, size=size,
                                       price=float(cur_best_bid), type="own_trade")

    
        if self.demo_fills and pd.notna(mid) and mid > 0:
            if abs(price - mid) / mid <= self.demo_passive_threshold:
                return SimpleNamespace(order_id=ts, ts=ts, side=side, size=size,
                                       price=float(price), type="own_trade")

       
        price_movement = 0.0 if (pd.isna(new_mid) or pd.isna(mid)) else (new_mid - mid)
        price_distance = 0.0 if pd.isna(mid) else abs(price - mid) / mid
        queue_position_ratio = min(1.0, size / self.level_volume)

        result = self.execution_model.simulate_fill(
            queue_position_ratio=queue_position_ratio,
            price_distance=price_distance,
            price_movement=price_movement,
        )

        if result == "filled":
            exec_price = price
        elif result == "slippage":
            exec_price = new_mid if pd.notna(new_mid) else price
        else:
            return self._limit_order(ts, size, side, price)

        return SimpleNamespace(order_id=ts, ts=ts, side=side, size=size,
                               price=float(exec_price), type="own_trade")

    def _limit_order(self, ts, size, side, price):
        return SimpleNamespace(order_id=ts, ts=ts, side=side, size=size,
                               price=price, type="limit_order")

    def cancel_order(self, ts, order_id):
        pass

    def mid_prices(self):
      
        mids = []
        for _, df in self.snapshots:
            bids = df[df["side"] == "bid"]["price"]
            asks = df[df["side"] == "ask"]["price"]
            if not bids.empty and not asks.empty:
                mids.append((bids.max() + asks.min()) / 2.0)
            else:
                mids.append(np.nan)
        return pd.Series(mids)

    def get_mid_prices(self):
  
        return self.mid_prices()

    def ticks_time(self):
     
        times = []
        have_dt = "datetime" in self.df.columns
        for ts_val, grp in self.snapshots:
            if have_dt and not grp["datetime"].isna().all():
                times.append(pd.to_datetime(grp["datetime"].iloc[0]))
            else:
                times.append(pd.to_datetime(ts_val, unit="ms", errors="coerce"))
        return times
