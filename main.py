import os
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

API_KEY = os.environ["ALPACA_API_KEY"]
SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

SYMBOL = "AAPL"
QTY = 1
SHORT_WINDOW = 5
LONG_WINDOW = 20

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_bars(symbol, limit=50):
    end = datetime.utcnow()
    start = end - timedelta(days=5)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        limit=limit
    )
    bars = data_client.get_stock_bars(request)
    df = bars.df
    df = df.xs(symbol, level="symbol")
    return df

def get_signal(df):
    df["short_ma"] = df["close"].rolling(SHORT_WINDOW).mean()
    df["long_ma"] = df["close"].rolling(LONG_WINDOW).mean()
    if len(df) < LONG_WINDOW:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    if prev["short_ma"] <= prev["long_ma"] and latest["short_ma"] > latest["long_ma"]:
        return "buy"
    elif prev["short_ma"] >= prev["long_ma"] and latest["short_ma"] < latest["long_ma"]:
        return "sell"
    return None

def place_order(side):
    order = MarketOrderRequest(
        symbol=SYMBOL,
        qty=QTY,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    response = trading_client.submit_order(order)
    print(f"Placed {side} order: {response.id}")

def main_loop():
    while True:
        try:
            df = get_bars(SYMBOL)
            signal = get_signal(df)
            print(f"{datetime.utcnow()} - Signal: {signal}")
            if signal in ("buy", "sell"):
                place_order(signal)
        except Exception as e:
            print("Error:", e)
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
