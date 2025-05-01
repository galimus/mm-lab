
from strategy.stoikov import StoikovStrategy
from strategy.naive_mm import NaiveMMStrategy
from simulator.real_data_sim import RealDataSim
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

sns.set_style("whitegrid")

sim = RealDataSim('BTCUSDT_1min.csv', spread=1.0, k_bid=1.5, k_ask=1.5)
sigma = sim.realized_sigma
print(f"Realized sigma: {sigma:.4f}")

stoikov = StoikovStrategy(
    sim=sim,
    gamma=0.05,
    k=1.5,
    sigma=sigma,
    terminal_time=True,
    adjust_delay=1,
    order_size=1,
    min_order_size=1,
    precision=2
)
trades_stoikov, md, updates_stoikov, orders_stoikov = stoikov.run()

sim_naive = RealDataSim('BTCUSDT_1min.csv', spread=1.0, k_bid=1.5, k_ask=1.5)
naive = NaiveMMStrategy(
    sim=sim_naive,
    base_spread=5,            
    volatility_multiplier=2.0, 
    order_size=1,
    max_inventory=10,
    precision=2
)
trades_naive, mid_prices_naive = naive.run()
print(f"[NaiveMM] Executed {len(trades_naive)} trades")

# --- Evaluate PnL and Inventory ---
def compute_pnl(trades, mid_prices):
    inventory, pnl, pos, cash = [], [], 0, 0
    for i, mid in enumerate(mid_prices):
        ts_trades = [tr for tr in trades if tr.ts == i]
        for tr in ts_trades:
            if tr.side == 'BID':
                pos += tr.size
                cash -= tr.price * tr.size
            else:
                pos -= tr.size
                cash += tr.price * tr.size
        inventory.append(pos)
        pnl.append(cash + pos * mid)
    return pd.Series(inventory), pd.Series(pnl)

mid_prices = [u.price for u in md]
inv_s, pnl_s = compute_pnl(trades_stoikov, mid_prices)
inv_n, pnl_n = compute_pnl(trades_naive, mid_prices_naive)


plt.figure(figsize=(14, 10))

plt.subplot(3, 1, 1)
plt.plot(mid_prices, label='Mid Price')
plt.title("Mid Price")
plt.legend()

plt.subplot(3, 1, 2)
plt.plot(inv_s, label='Stoikov Inventory', alpha=0.6)
plt.plot(inv_n, label='NaiveMM Inventory', alpha=0.6)
plt.title("Inventory Comparison")
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(pnl_s, label='Stoikov PnL', alpha=0.9)
plt.plot(pnl_n, label='NaiveMM PnL', alpha=0.9)
plt.title("PnL Comparison")
plt.xlabel("Time")
plt.legend()

plt.tight_layout()
plt.show()
