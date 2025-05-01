import math
import numpy as np
from collections import OrderedDict

class StoikovStrategy:
    def __init__(self, sim, gamma, k, sigma, terminal_time, adjust_delay,
                 order_size, min_order_size, precision):
        self.sim = sim
        self.gamma = gamma
        self.k = k
        self.sigma = sigma
        self.terminal_time = terminal_time
        self.adjust_delay = adjust_delay
        self.order_size = order_size
        self.min_order_size = min_order_size
        self.precision = precision

        self.md_list = []
        self.trades_list = []
        self.updates_list = []
        self.all_orders = []
        self.ongoing_orders = OrderedDict()

        self.best_bid = -math.inf
        self.best_ask = math.inf
        self.cur_time = 0
        self.T_minus_t = 1
        self.cur_pos = 0

       
        self.max_drawdown = 3000
        self.max_pnl = 0
        self.pause_duration = 30     
        self.pause_until = -1       

        self.recent_prices = []
        self.volatility_window = 30
        self.volatility_threshold = 0.0015

        self.default_k = k
        self.default_gamma = gamma

        self.pnl = 0
        self.cash = 0

    def run(self):
        last_readjust = 0
        t_min = self.sim.md_queue[0].receive_ts
        t_max = self.sim.md_queue[-1].receive_ts
        max_inventory = 5

        while True:
            self.cur_time, updates = self.sim.tick()
            if updates is None:
                break

            self.updates_list += updates
            for update in updates:
                if update.type == 'md':
                    self.best_bid, self.best_ask = update_best_positions(
                        self.best_bid, self.best_ask, update)
                    self.md_list.append(update)

            if self.cur_time - last_readjust > self.adjust_delay:
                last_readjust = self.cur_time

                while self.ongoing_orders:
                    order_id, _ = self.ongoing_orders.popitem(last=False)
                    self.sim.cancel_order(self.cur_time, order_id)

                self.T_minus_t = 1 - (self.cur_time - t_min) / (t_max - t_min) if self.terminal_time else 1

                central_price = self.get_central_price()
                if central_price is None:
                    continue

                
                self.recent_prices.append(central_price)
                if len(self.recent_prices) > self.volatility_window:
                    self.recent_prices.pop(0)

                    log_returns = [
                        math.log(self.recent_prices[i + 1] / self.recent_prices[i])
                        for i in range(len(self.recent_prices) - 1)
                    ]
                    volatility = np.std(log_returns)

                    if volatility > self.volatility_threshold:
                        self.k = self.default_k * 1.5
                        self.gamma = self.default_gamma * 1.5
                    else:
                        self.k = self.default_k
                        self.gamma = self.default_gamma

                # --- Max Drawdown Check ---
                cur_mid = central_price
                unrealized = self.cur_pos * cur_mid
                self.pnl = self.cash + unrealized
                self.max_pnl = max(self.max_pnl, self.pnl)
                drawdown = self.max_pnl - self.pnl

                if drawdown > self.max_drawdown and self.cur_time > self.pause_until:
                    print(f"‼️ Drawdown = {drawdown:.2f}, pausing trading for {self.pause_duration} steps.")
                    self.pause_until = self.cur_time + self.pause_duration

                if self.cur_time < self.pause_until:
                    continue  

                # --- Spread and Skew ---
                base_spread = self.gamma * self.sigma**2 * self.T_minus_t + \
                              2 / self.gamma * math.log(1 + self.gamma / self.k)
                lambda_inventory = 0.02
                spread = base_spread + lambda_inventory * (abs(self.cur_pos) ** 2)
                skew = -self.cur_pos * self.gamma * self.sigma**2 * self.T_minus_t

                price_bid = round(central_price - spread / 2 + skew, self.precision)
                price_ask = round(central_price + spread / 2 + skew, self.precision)

                if self.cur_pos < max_inventory:
                    self.place_order(self.cur_time, self.order_size, 'BID', price_bid)
                if self.cur_pos > -max_inventory:
                    self.place_order(self.cur_time, self.order_size, 'ASK', price_ask)

        return self.trades_list, self.md_list, self.updates_list, self.all_orders

    def get_central_price(self):
        if self.best_bid == -math.inf or self.best_ask == math.inf:
            return None
        midprice = (self.best_bid + self.best_ask) / 2
        indiff_price = midprice - (self.cur_pos / self.min_order_size) * \
                       self.gamma * self.sigma**2 * self.T_minus_t
        return indiff_price

    def place_order(self, ts, size, side, price):
        order = self.sim.place_order(ts, size, side, price)
        if getattr(order, 'type', None) == 'own_trade':
            self.trades_list.append(order)
            if order.side == 'BID':
                self.cur_pos += order.size
                self.cash -= order.size * order.price
            else:
                self.cur_pos -= order.size
                self.cash += order.size * order.price
        else:
            self.ongoing_orders[order.order_id] = order
            self.all_orders.append(order)

def update_best_positions(best_bid, best_ask, update):
    if update.bid_price is not None:
        best_bid = max(best_bid, update.bid_price)
    if update.ask_price is not None:
        best_ask = min(best_ask, update.ask_price)
    return best_bid, best_ask





