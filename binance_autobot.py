import os
import json
from binance.client import Client
from binance.enums import *

# Binance API credentials
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"

# Create a Binance client
client = Client(API_KEY, API_SECRET)

# Define a function to handle trading signals
def handle_signal(signal):
    try:
        # Extract signal data
        action = signal["action"]
        ticker = signal["ticker"]
        quantity = float(signal["position_pct"]) / 100 * client.get_asset_balance(asset="USDT")["free"]

        # Execute trade
        if action == "buy":
            order = client.order_market_buy(
                symbol=ticker,
                quantity=quantity
            )
            print(f"Buy order executed: {order}")
        elif action == "sell":
            order = client.order_market_sell(
                symbol=ticker,
                quantity=quantity
            )
            print(f"Sell order executed: {order}")
    except Exception as e:
        print(f"Error handling signal: {e}")

# Define a Flask server to receive webhook signals
from flask import Flask, request
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    signal = request.get_json()
    handle_signal(signal)
    return "Signal received!"

if __name__ == "__main__":
    app.run()