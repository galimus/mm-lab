import pandas as pd
import matplotlib.pyplot as plt

def analyze_fills(trades, orders):
    df_trades = pd.DataFrame([vars(tr) for tr in trades])
    df_orders = pd.DataFrame([vars(o) for o in orders])

    
    total_orders = len(df_orders)
    filled_orders = len(df_trades)
    fill_rate = filled_orders / total_orders if total_orders else 0
    avg_fill_price = df_trades['price'].mean()
    min_price, max_price = df_trades['price'].min(), df_trades['price'].max()

    print("\n🧾 Execution Report")
    print(f"Total Orders: {total_orders}")
    print(f"Filled Orders: {filled_orders}")
    print(f"✅ Fill Rate: {fill_rate:.2%}")
    print(f"💰 Avg Fill Price: {avg_fill_price:.2f}")
    print(f"📉 Min / Max Fill Price: {min_price:.2f} / {max_price:.2f}")

    
    plt.figure(figsize=(10, 4))
    plt.hist(df_trades['price'], bins=50, alpha=0.7, color='green', edgecolor='black')
    plt.title("Histogram of Fill Prices")
    plt.xlabel("Price")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("results/hist_fill_prices.png")
    plt.show()


    if 'type' in df_orders.columns:
        plt.figure(figsize=(6, 4))
        df_orders['type'].value_counts().plot(kind='bar', color='steelblue')
        plt.title("Order Type Counts")
        plt.xticks(rotation=0)
        plt.grid(axis='y')
        plt.tight_layout()
        plt.savefig("results/order_type_counts.png")
        plt.show()
