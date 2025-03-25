import numpy as np
from types import SimpleNamespace

class MinimalSim:
    def __init__(self, T=200, start_price=100.0, sigma=0.1):
        self.T = T
        self.t = 0
        self.cur_price = start_price
        self.sigma = sigma
        self.md_queue = [self._generate_md(i) for i in range(T)]
        self.order_id = 0
        self.orders = {}

    def _generate_md(self, t):
        price = self.cur_price + np.random.randn() * self.sigma
        return SimpleNamespace(
            receive_ts=t,
            price=price,
            bid_price=price - 0.5,
            ask_price=price + 0.5,
            type='md'
        )

    def tick(self):
        if self.t >= self.T:
            return self.t, None
        update = self.md_queue[self.t]
        self.cur_price = update.price
        self.t += 1
        return self.t, [update]

    def place_order(self, ts, size, side, price):
        self.order_id += 1
        order = SimpleNamespace(
            order_id=self.order_id,
            ts=ts,
            size=size,
            side=side,
            price=price
        )
      
        if np.random.rand() < 0.5:
            trade = SimpleNamespace(
                order_id=order.order_id,
                side=side,
                size=size,
                ts=ts,
                type='own_trade'
            )
            return trade
        self.orders[self.order_id] = order
        return order

    def cancel_order(self, ts, order_id):
        self.orders.pop(order_id, None)
