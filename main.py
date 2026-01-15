import os
import time
from datetime import datetime, timedelta, UTC

import numpy as np
import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed


# --- Config / Environment ---

API_KEY = os.environ["ALPACA_API_KEY"]
SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

SYMBOL = "AAPL"
QTY = 1
SHORT_WINDOW = 5
LONG_WINDOW = 20

# --- Clients ---

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)


# --- Data + Strategy ---

def get_bars(symbol, limit=50):
    """Fetch recent minute bars using IEX (free) data."""
    end = datetime.now(UTC)
    start = end - timedelta(days=5)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        limit=limit,
        feed=DataFeed.IEX,  # feed goes here in new SDK
    )

    bars = data_client.get_stock_bars(request)

    if bars.df.empty:
        raise ValueError("No data returned from IEX feed.")

    df = bars.df.xs(symbol, level="symbol")
    return df


def get_signal(df):
    """Generate buy/sell signal using moving average crossover."""
    df["short_ma"] = df["close"].rolling(SHORT_WINDOW).mean()
    df["long_ma"] = df["close"].rolling(LONG_WINDOW).mean()

    if len(df) < LONG_WINDOW:
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    if prev["short_ma"] <= prev["long_ma"] and latest["short_ma"] > latest["long_ma"]:
        return "buy"
    if prev["short_ma"] >= prev["long_ma"] and latest["short_ma"] < latest["long_ma"]:
        return "sell"

    return None


# --- Trading ---

def place_order(side):
    """Submit a market order."""
    order = MarketOrderRequest(
        symbol=SYMBOL,
        qty=QTY,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    response = trading_client.submit_order(order)
    print(f"Placed {side} order: {response.id}")


# --- Main Loop ---

def main_loop():
    while True:
        try:
            df = get_bars(SYMBOL)
            signal = get_signal(df)
            print(f"{datetime.now(UTC)} - Signal: {signal}")

            if signal in ("buy", "sell"):
                place_order(signal)

        except Exception as e:
            print("Error:", e)

        time.sleep(60)


if __name__ == "__main__":
    main_loop()
