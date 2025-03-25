from strategy.stoikov import StoikovStrategy
from simulator.minimal_sim import MinimalSim
import matplotlib.pyplot as plt


gamma = 0.05
k = 1.5
sigma = 0.1
terminal_time = True
adjust_delay = 1
order_size = 1
min_order_size = 1
precision = 2


sim = MinimalSim(T=200, start_price=100.0, sigma=sigma)
strategy = StoikovStrategy(
    sim=sim,
    gamma=gamma,
    k=k,
    sigma=sigma,
    terminal_time=terminal_time,
    adjust_delay=adjust_delay,
    order_size=order_size,
    min_order_size=min_order_size,
    precision=precision
)


trades, md, updates, orders = strategy.run()


mid_prices = [u.price for u in md]
inventory = []
pnl = []
cash = 0
pos = 0

for i in range(len(mid_prices)):
    mid = mid_prices[i]
    trades_at_i = [tr for tr in trades if tr.ts == i]
    
    for trade in trades_at_i:
        price = getattr(trade, 'price', mid)  
        size = trade.size
        side = trade.side

        if side == 'BID':
            pos += size
            cash -= price * size
        else:
            pos -= size
            cash += price * size
    
    inventory.append(pos)
    pnl.append(cash + pos * mid)

plt.figure(figsize=(12, 9))

plt.subplot(3, 1, 1)
plt.plot(mid_prices, label='Mid Price')
plt.title("Mid Price")
plt.legend()

plt.subplot(3, 1, 2)
plt.plot(inventory, color='orange', label='Inventory')
plt.title("Inventory Over Time")
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(pnl, color='green', label='PnL')
plt.title("PnL Over Time")
plt.xlabel("Time")
plt.legend()

plt.tight_layout()
plt.show()


