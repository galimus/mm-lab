import math
import numpy as np
import pandas as pd
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

        # Risk management
        self.max_drawdown = 3000
        self.max_pnl = 0
        self.pause_duration = 30
        self.pause_until = -1
        self.drawdown_breached = False

        # Volatility adaptiveness
        self.recent_prices = []
        self.volatility_window = 30
        self.volatility_threshold = 0.0015
        self.default_k = k
        self.default_gamma = gamma

        
        self.max_hold_steps = 60  # Max time in one direction
        self.hold_start_time = 0
        self.prev_sign = 0

        self.pnl = 0
        self.cash = 0

       
        self.logs = []
        self.realized_pnl_list = []
        self.unrealized_pnl_list = []
        self.pnl_list = []
        self.time_list = []

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

                # --- Volatility Adaptation ---
                self.recent_prices.append(central_price)
                if len(self.recent_prices) > self.volatility_window:
                    self.recent_prices.pop(0)
                    log_returns = [
                        math.log(self.recent_prices[i + 1] / self.recent_prices[i])
                        for i in range(len(self.recent_prices) - 1)
                    ]
                    volatility = np.std(log_returns)

                    if volatility > self.volatility_threshold:
                        print(f"⚠️ High volatility: {volatility:.5f}. Increasing risk aversion at t={self.cur_time}")
                        self.logs.append({'time': self.cur_time, 'event': 'high_volatility'})
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

                self.realized_pnl_list.append(self.cash)
                self.unrealized_pnl_list.append(unrealized)
                self.pnl_list.append(self.pnl)
                self.time_list.append(self.cur_time)

                if drawdown > self.max_drawdown and not self.drawdown_breached:
                    print(f"‼️ Drawdown = {drawdown:.2f}, pausing trading for {self.pause_duration} steps.")
                    self.pause_until = self.cur_time + self.pause_duration
                    self.drawdown_breached = True
                    self.logs.append({'time': self.cur_time, 'event': 'drawdown_pause'})

                if self.cur_time >= self.pause_until and drawdown < self.max_drawdown and self.drawdown_breached:
                    print(f"✅ Drawdown recovered. Resuming trading at time {self.cur_time}.")
                    self.drawdown_breached = False
                    self.logs.append({'time': self.cur_time, 'event': 'resume_trading'})

                if self.cur_time < self.pause_until:
                    continue

                
                current_sign = int(np.sign(self.cur_pos))
                if current_sign != self.prev_sign:
                    self.prev_sign = current_sign
                    self.hold_start_time = self.cur_time

                if abs(self.cur_pos) >= max_inventory and (self.cur_time - self.hold_start_time) > self.max_hold_steps:
                    print(f"⚠️ Forced unwind at t={self.cur_time} to prevent stuck position.")
                    
                    self.place_order(self.cur_time, abs(self.cur_pos), 'ASK' if self.cur_pos > 0 else 'BID', central_price)
                    self.logs.append({'time': self.cur_time, 'event': 'forced_unwind'})
                    continue

            
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

        pd.DataFrame(self.logs).to_csv('logs.csv', index=False)
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




