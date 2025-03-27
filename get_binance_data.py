import ccxt
import pandas as pd

# --- Настройки ---
symbol = 'BTC/USDT'
timeframe = '1m'  # Можно '1m', '5m', '1h'
since = ccxt.binance().parse8601('2024-03-01T00:00:00Z')
limit = 1000  # Binance позволяет максимум 1000 свечей за раз

# --- Подключение ---
exchange = ccxt.binance()

# --- Получение данных ---
ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

# --- Создание DataFrame ---
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

# --- Сохранение в CSV ---
df.to_csv('BTCUSDT_1min.csv', index=False)

# --- Проверка ---
print(df.head())
