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
pos = 0
inventory.append(pos) 
for trade in trades:
    pos += trade.size if trade.side == 'BID' else -trade.size
    inventory.append(pos)


plt.figure(figsize=(12, 6))
plt.subplot(2, 1, 1)
plt.plot(mid_prices, label='Mid Price')
plt.title("Mid Price")
plt.legend()

plt.subplot(2, 1, 2)
plt.plot(inventory, color='orange', label='Inventory')
plt.title("Inventory Over Time")
plt.xlabel("Time")
plt.legend()
plt.tight_layout()
plt.show()

