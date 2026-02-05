# pip install alpaca-trade-api pandas numpy

import alpaca_trade_api as tradeapi
import pandas as pd
import time
from alpaca_trade_api.rest import TimeFrame
from config import API_KEY, API_SECRET, BASE_URL




api = tradeapi.REST(
    API_KEY,
    API_SECRET,
    BASE_URL,
    api_version="v2"
)




SYMBOLS = ["AXON","APP","BTC"]
LOOKBACK = 40
MAX_DOLLARS_PER_TRADE = 1000
LOOKBACK = 40

STOP_LOSS_PCT = 0.03
TAKE_PROFIT_PCT = 0.05

# -------------------------
# RSI Indicator
# -------------------------

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# -------------------------
# Data
# -------------------------

def calculate_qty(symbol, max_dollars):
    try:
        price = float(api.get_latest_trade(symbol).price)
    except Exception as e:
        print(f"Price error for {symbol}: {e}")
        return 0

    qty = int(max_dollars // price)
    return max(qty, 1)  # never return 0


def get_bars(symbol):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=LOOKBACK).df
    except Exception as e:
        print(f"Error fetching bars for {symbol}: {e}")
        return pd.DataFrame()

    if len(bars) < 20:
        print(f"⚠️ Not enough candles for RSI ({len(bars)} bars)")
        return pd.DataFrame()

    bars["RSI"] = compute_rsi(bars["close"])
    bars = bars.dropna()

    if bars.empty:
        print(f"⚠️ RSI calculation returned no usable rows")
    return bars




# -------------------------
# Trading Helpers
# -------------------------

def get_position(symbol):
    try:
        return api.get_position(symbol)
    except:
        return None

def short_market(symbol, qty):
    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="sell",
        type="market",
        time_in_force="day"
    )
    print(f"📉 SHORT {symbol} ({qty})")

def cover_market(symbol, qty):
    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="market",
        time_in_force="day"
    )
    print(f"📈 COVER {symbol} ({qty})")

# -------------------------
# Strategy Logic
# -------------------------

def should_short(bars):
    if bars.empty:
        return False  # never short if no data
    last = bars.iloc[-1]
    return 30 < last.RSI < 45


def manage_position(symbol):
    pos = get_position(symbol)
    if not pos:
        return

    entry = float(pos.avg_entry_price)
    price = float(api.get_latest_trade(symbol).price)
    profit_pct = (entry - price) / entry
    qty = abs(int(float(pos.qty)))

    if profit_pct >= TAKE_PROFIT_PCT:
        cover_market(symbol, qty)
        print("✅ Take profit hit")

    elif profit_pct <= -STOP_LOSS_PCT:
        cover_market(symbol, qty)
        print("🛑 Stop loss hit")

# -------------------------
# Main Loop
# -------------------------

def trade(symbol):
    bars = get_bars(symbol)

    if bars.empty:
        return

    position = get_position(symbol)

    if not position:
        if should_short(bars):
            qty = calculate_qty(symbol, MAX_DOLLARS_PER_TRADE)
            short_market(symbol, qty)
        else:
            print(f"{symbol}: No short signal")
    else:
        manage_position(symbol)




if __name__ == "__main__":
    while True:
        for symbol in SYMBOLS:
            trade(symbol)
        time.sleep(60 * 5)

