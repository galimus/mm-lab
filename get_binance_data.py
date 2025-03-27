import ccxt
import pandas as pd


symbol = 'BTC/USDT'
timeframe = '1m'  
since = ccxt.binance().parse8601('2024-03-01T00:00:00Z')
limit = 1000  


exchange = ccxt.binance()


ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)


df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')


df.to_csv('BTCUSDT_1min.csv', index=False)


print(df.head())
