import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone

def fetch_binance_l2_snapshot(symbol="ETHUSDT", limit=100):
    url = "https://api.binance.com/api/v3/depth"
    params = {"symbol": symbol.upper(), "limit": limit}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    timestamp = int(time.time() * 1000)
    dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

    rows = []
    for side, entries in [("bid", data["bids"]), ("ask", data["asks"])]:
        for price, size in entries:
            rows.append({
                "timestamp": timestamp,
                "datetime": dt,
                "side": side,
                "price": float(price),
                "size": float(size)
            })

    return pd.DataFrame(rows)


def collect_if_needed(symbol, csv_path, n_snapshots=10, delay=0.3):
   
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, "w") as f:
        f.write("timestamp,datetime,side,price,size\n")

    for i in range(n_snapshots):
        df = fetch_binance_l2_snapshot(symbol)
        df.to_csv(csv_path, mode="a", header=False, index=False)
        print(f"[{i+1}/{n_snapshots}] Snapshot collected at {df['datetime'].iloc[0]}")
        time.sleep(delay)

    print(f" Saved {n_snapshots} snapshots to {csv_path}")
