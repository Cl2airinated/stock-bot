import os
import time
from datetime import datetime, timedelta, UTC

import numpy as np
import pandas as pd

# --- TruthBrush (correct import) ---
from truthbrush.client import TruthSocialClient
truth_client = TruthSocialClient()
# --- Alpaca ---
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

# --- Sentiment ---
from nltk.sentiment import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()

# --- Config ---
API_KEY = os.environ["ALPACA_API_KEY"]
SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

STOCKLIST = ["AAPL", "MSFT", "TSLA"]
QTY = 1
SHORT_WINDOW = 5
LONG_WINDOW = 20

# --- Clients ---
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# --- Market Data ---
def get_bars(symbol, limit=50):
    end = datetime.now(UTC)
    start = end - timedelta(days=5)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start,
        end=end,
        limit=limit,
        feed=DataFeed.IEX,
    )

    bars = data_client.get_stock_bars(request)

    if bars.df.empty:
        raise ValueError(f"No data returned for {symbol}")

    return bars.df.xs(symbol, level="symbol")


def get_ma_signal(df):
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

# --- Truth Social Sentiment ---
def fetch_truths(symbol):
    try:
        posts = truth_client.search(symbol)
        texts = [p["content"] for p in posts]
        return " ".join(texts) if texts else ""
    except Exception as e:
        print("TruthBrush error:", e)
        return ""


def get_sentiment(text):
    return sia.polarity_scores(text)["compound"]


def truthbrush_filter(score):
    return abs(score) >= 0.2


def get_sentiment_signal(symbol):
    text = fetch_truths(symbol)
    score = get_sentiment(text)

    if not truthbrush_filter(score):
        return None

    if score >= 0.3:
        return "buy"
    if score <= -0.3:
        return "sell"

    return None

# --- Combine Signals ---
def combine_signals(ma_signal, sentiment_signal):
    return sentiment_signal or ma_signal

# --- Trading ---
def place_order(symbol, side):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=QTY,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    response = trading_client.submit_order(order)
    print(f"Placed {side} order for {symbol}: {response.id}")

# --- Main Loop ---
def main_loop():
    while True:
        try:
            for symbol in STOCKLIST:
                df = get_bars(symbol)
                ma_signal = get_ma_signal(df)
                sentiment_signal = get_sentiment_signal(symbol)
                final_signal = combine_signals(ma_signal, sentiment_signal)

                print(
                    f"{datetime.now(UTC)} | {symbol} | "
                    f"MA: {ma_signal} | Sentiment: {sentiment_signal} | Final: {final_signal}"
                )

                if final_signal in ("buy", "sell"):
                    place_order(symbol, final_signal)

        except Exception as e:
            print("Error:", e)

        time.sleep(60)


if __name__ == "__main__":
    main_loop()
