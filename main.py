import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time

from strategy.stoikov import StoikovStrategy
from simulator.real_data_sim import RealDataSim
from scripts.analyze_fills import analyze_fills

plt.ion()


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

# --- Run simulation ---
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


plt.figure(figsize=(12, 8))

plt.plot(strategy.time_list, strategy.realized_pnl_list, label='Realized PnL', color='blue')
plt.plot(strategy.time_list, strategy.unrealized_pnl_list, label='Unrealized PnL', color='orange', linestyle='--')
plt.plot(strategy.time_list, strategy.pnl_list, label='Total PnL', color='green')

for log in strategy.logs:
    if log['event'] == 'drawdown_pause':
        plt.axvline(log['time'], color='red', linestyle='--', alpha=0.6, label='Pause' if 'Pause' not in plt.gca().get_legend_handles_labels()[1] else "")
    elif log['event'] == 'resume_trading':
        plt.axvline(log['time'], color='lime', linestyle='--', alpha=0.6, label='Resume' if 'Resume' not in plt.gca().get_legend_handles_labels()[1] else "")

plt.title('PnL Breakdown with Risk Events')
plt.xlabel('Time')
plt.ylabel('PnL')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('results/pnl_breakdown_with_logs.png')
plt.show()

analyze_fills(trades, orders)






