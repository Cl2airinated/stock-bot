# pip install alpaca-trade-api

import alpaca_trade_api as tradeapi

API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_SECRET_KEY"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

# --- Basic helpers ---

def buy_market(symbol, qty):
    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="market",
        time_in_force="day"
    )
    print(f"Bought {qty} shares of {symbol}")

def sell_market(symbol, qty):
    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="sell",
        type="market",
        time_in_force="day"
    )
    print(f"Sold {qty} shares of {symbol}")

def get_position_qty(symbol):
    try:
        pos = api.get_position(symbol)
        return int(float(pos.qty))
    except:
        return 0

# --- Example trading logic ---

def trade_stocks():
    petro = "PTR"
    baba = "BABA"

    # Buy 10 shares of each
    buy_market(petro, 10)
    buy_market(baba, 10)

    # Example: sell later
    # sell_market(petro, get_position_qty(petro))
    # sell_market(baba, get_position_qty(baba))

if __name__ == "__main__":
    trade_stocks()
