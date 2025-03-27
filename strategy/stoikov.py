import math
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

                spread = self.gamma * self.sigma**2 * self.T_minus_t + \
                         2 / self.gamma * math.log(1 + self.gamma / self.k)

                price_bid = round(central_price - spread / 2, self.precision)
                price_ask = round(central_price + spread / 2, self.precision)

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
            else:
                self.cur_pos -= order.size
        else:
            self.ongoing_orders[order.order_id] = order
            self.all_orders.append(order)


def update_best_positions(best_bid, best_ask, update):
    if update.bid_price is not None:
        best_bid = max(best_bid, update.bid_price)
    if update.ask_price is not None:
        best_ask = min(best_ask, update.ask_price)
    return best_bid, best_ask

