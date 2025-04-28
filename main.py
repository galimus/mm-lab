import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from strategy.stoikov import StoikovStrategy
from simulator.real_data_sim import RealDataSim
import time


print("Fetching fresh data from Binance...")

symbol = 'BTC/USDT'
timeframe = '1m'
since = int((time.time() - 60 * 60 * 24) * 1000)  
limit = 1000

exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
df.to_csv('BTCUSDT_1min.csv', index=False)

print("Data fetched and saved.")


sns.set_style("whitegrid")  

sim = RealDataSim('BTCUSDT_1min.csv', spread=1.0, k_bid=1.5, k_ask=1.5)
sigma = sim.realized_sigma
print(f"Realized sigma: {sigma:.4f}")

strategy = StoikovStrategy(
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

trades, md, updates, orders = strategy.run()


mid_prices = [u.price for u in md]
inventory, pnl, pos, cash = [], [], 0, 0

for i, mid in enumerate(mid_prices):
    ts_trades = [tr for tr in trades if tr.ts == i]
    for tr in ts_trades:
        price = tr.price
        if tr.side == 'BID':
            pos += tr.size
            cash -= price * tr.size
        else:
            pos -= tr.size
            cash += price * tr.size
    inventory.append(pos)
    pnl.append(cash + pos * mid)

inv_series = pd.Series(inventory)
pnl_series = pd.Series(pnl)

plt.figure(figsize=(12, 9))

plt.subplot(3, 1, 1)
plt.plot(mid_prices, label='Mid Price')
plt.title("Mid Price")
plt.legend()

plt.subplot(3, 1, 2)
plt.plot(inv_series, color='orange', alpha=0.3, linestyle='--', label='Raw Inventory')
plt.plot(inv_series.rolling(5).mean(), color='orange', label='Inventory (SMA)')
plt.title("Inventory Over Time")
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(pnl_series, color='green', label='PnL')
plt.title("PnL Over Time")
plt.xlabel("Time")
plt.legend()

plt.tight_layout()
plt.show()





