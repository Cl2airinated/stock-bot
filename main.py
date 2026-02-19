# pip install alpaca-trade-api pandas numpy

import alpaca_trade_api as tradeapi
import pandas as pd
import time
from alpaca_trade_api.rest import TimeFrame
import os

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

if not API_KEY or not API_SECRET or not BASE_URL: raise Exception("Missing API credentials")
import time
import random

def safe_api_call(func, *args, **kwargs):
    for attempt in range(5):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            wait = 1 + attempt + random.random()
            print(f"API error: {e} — retrying in {wait:.2f}s")
            time.sleep(wait)
    print("API failed after 5 retries")
    return None





api = tradeapi.REST(
    API_KEY,
    API_SECRET,
    BASE_URL,
    api_version="v2"
)




SYMBOLS = [
"AAPL","MSFT","AMZN","GOOGL","GOOG","NVDA","META","TSLA","BRK.B","UNH",
"JNJ","XOM","V","JPM","PG","MA","HD","CVX","MRK","BAC","ABBV","KO","PEP",
"AVGO","LLY","NFLX","COST","TMO","ADBE","CRM","CMCSA","PFE","ABT","ACN","WMT",
"ORCL","NKE","T","MDT","DHR","MCD","C","NEE","TXN","LIN","AMGN","UNP","HON",
"PM","LOW","BMY","UPS","QCOM","RTX","INTC","MS","AXP","IBM","SCHW","GE","SBUX",
"CAT","BLK","LMT","ISRG","DE","CVS","PLD","ADI","AMAT","SYK","COP","ANTM","CB",
"ZM","GS","AMT","MO","NOW","TJX","MDLZ","GILD","BDX","SPGI","CME","BK","CI",
"CCI","PNC","FIS","BSX","EXC","SO","DUK","LRCX","FISV","AON","ZTS","GM","CL",
"REGN","TGT","PPG","MCO","ICE","ELV","ITW","ALL","KMB","MMC","VRTX","HUM","TFC",
"ADP","WM","EOG","HCA","SHW","EW","D","EBAY","ETN","KMI","PSX","AKAM","ETSY",
"ROP","CXO","AES","SLB","AIG","FTNT","ABMD","ROST","VLO","MSCI","HES","NOC",
"KEYS","BLL","AEE","NTRS","IFF","MPC","TFX","PNR","PNW","OXY","WBA","CARR",
"VRSK","CMS","PXD","DAL","KHC","DD","TRV","EL","APD","ADM","HPE","MTB","TRP",
"FFIV","UDR","CLX","GPN","ESS","PRU","HSY","YUM","NEM","EQR","AFL","HIG","EXR",
"DOW","TEX","BAX","MLM","SRE","SYF","AVB","FTV","WY","GL","EIX","PGR","HST",
"MLPE","EFX","LH","CNP","RYAAY","WLTW","PH","WRB"
]
LOOKBACK = 40
MAX_DOLLARS_PER_TRADE = 100000
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
        bars_resp = safe_api_call(api.get_bars, symbol, TimeFrame.Minute, limit=LOOKBACK)
        if bars_resp is None:
            return pd.DataFrame()
        bars = bars_resp.df

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

def performance_pct(bars):
    if bars.empty:
        return None
    start = bars.iloc[0].close
    end = bars.iloc[-1].close
    return (end - start) / start

def get_worst_performers(symbols, top_n=10):
    perf = []

    for symbol in symbols:
        bars = get_bars(symbol)
        if bars.empty:
            continue

        pct = performance_pct(bars)
        if pct is not None:
            perf.append((symbol, pct))

    perf.sort(key=lambda x: x[1])  # worst first
    return [s for s, _ in perf[:top_n]]

def get_position(symbol):
    try:
        return api.get_position(symbol)
    except:
        return None

def short_market(symbol, qty):
    safe_api_call(api.submit_order, symbol=symbol, qty=qty, side="sell", type="market", time_in_force="day")

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
        return False
    last = bars.iloc[-1]
    return 30 < last.RSI < 45



def manage_position(symbol):
    pos = get_position(symbol)
    if not pos:
        return

    entry = float(pos.avg_entry_price)
    trade = safe_api_call(api.get_latest_trade, symbol)
    if trade is None:
        return 0
    price = float(trade.price)

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
        print(f"{symbol}: Skipping — no data available")
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


def run_strategy():
    worst = get_worst_performers(SYMBOLS, top_n=10)

    
    for symbol in worst:
        trade(symbol)
        time.sleep(0.5)  # prevents rate-limit bursts



if __name__ == "__main__":
    while True:
        run_strategy()
        time.sleep(60 * 5)


