import math

class NaiveMMStrategy:
    def __init__(self, sim, base_spread=10, volatility_multiplier=1.5, order_size=1, max_inventory=10, precision=2):
        self.sim = sim
        self.base_spread = base_spread
        self.volatility_multiplier = volatility_multiplier
        self.order_size = order_size
        self.max_inventory = max_inventory
        self.precision = precision

    def run(self):
        trades = []
        inventory = 0
        cash = 0
        mid_prices = []
        last_mid_price = None

        while True:
            ts, updates = self.sim.tick()
            if updates is None:
                break

            update = updates[0]
            mid_price = update.price
            mid_prices.append(mid_price)

            if last_mid_price is not None:
                volatility = abs(mid_price - last_mid_price)
            else:
                volatility = 0

            last_mid_price = mid_price

          
            dynamic_spread = self.base_spread + self.volatility_multiplier * volatility

            half_spread = dynamic_spread / 2
            bid_price = round(mid_price - half_spread, self.precision)
            ask_price = round(mid_price + half_spread, self.precision)

            
            bid_qty = self.order_size if inventory < self.max_inventory else 0
            ask_qty = self.order_size if inventory > -self.max_inventory else 0

            ts_trades = []

            if bid_qty > 0:
                result = self.sim.place_order(ts, bid_qty, 'BID', bid_price)
                if getattr(result, 'type', None) == 'own_trade':
                    ts_trades.append(result)

            if ask_qty > 0:
                result = self.sim.place_order(ts, ask_qty, 'ASK', ask_price)
                if getattr(result, 'type', None) == 'own_trade':
                    ts_trades.append(result)

           
            for tr in ts_trades:
                if tr.side == 'BID':
                    inventory += tr.size
                    cash -= tr.price * tr.size
                else:
                    inventory -= tr.size
                    cash += tr.price * tr.size

            trades.extend(ts_trades)

        return trades, mid_prices

