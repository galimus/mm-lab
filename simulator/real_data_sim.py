import pandas as pd
import numpy as np
import math
import random
from types import SimpleNamespace

class RealDataSim:
    def __init__(self, csv_path, spread=1.0, k_bid=1.5, k_ask=1.5):
        self.df = pd.read_csv(csv_path).sort_values(by='timestamp')
        self.spread = spread
        self.k_bid = k_bid
        self.k_ask = k_ask
        self.t = 0

        self.df['log_return'] = np.log(self.df['close'] / self.df['close'].shift(1))
        self.realized_sigma = self.df['log_return'].std() * np.sqrt(1440)

        self.md_queue = [
            SimpleNamespace(
                receive_ts=row['timestamp'],
                price=row['close'],
                bid_price=row['close'] - spread / 2,
                ask_price=row['close'] + spread / 2,
                type='md'
            )
            for _, row in self.df.iterrows()
            if not np.isnan(row['close'])
        ]

    def tick(self):
        if self.t >= len(self.md_queue):
            return self.t, None
        update = self.md_queue[self.t]
        self.t += 1
        return self.t, [update]

    def place_order(self, ts, size, side, price):
        if ts == 0:
            return self._limit_order(ts, size, side, price)

        mid = self.md_queue[ts - 1].price

        if side == 'BID':
            distance = max(mid - price, 0)
            fill_prob = 1 - math.exp(-self.k_bid * distance)
        else:
            distance = max(price - mid, 0)
            fill_prob = 1 - math.exp(-self.k_ask * distance)

        if random.random() < fill_prob:
            return SimpleNamespace(
                order_id=ts,
                ts=ts,
                side=side,
                size=size,
                price=price,
                type='own_trade'
            )
        else:
            return self._limit_order(ts, size, side, price)

    def _limit_order(self, ts, size, side, price):
        return SimpleNamespace(
            order_id=ts,
            ts=ts,
            side=side,
            size=size,
            price=price,
            type='limit_order'
        )

    def cancel_order(self, ts, order_id):
        pass
