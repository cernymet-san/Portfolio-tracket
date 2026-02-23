import yfinance as yf
import pandas as pd


class Stock:
    """Handles individual stock data and operations"""

    def __init__(self, symbol, shares, purchase_price):
        self.symbol = symbol.upper()
        self.shares = shares
        self.purchase_price = purchase_price  # assumed EUR

    def get_current_price(self):
        """Fetch current stock price (native currency, assumed EUR for EU tickers)"""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period="5d")
            if not data.empty:
                return round(float(data["Close"].dropna().iloc[-1]), 2)
            return None
        except Exception as e:
            print(f"Error fetching price for {self.symbol}: {e}")
            return None

    def get_price_history(self, period="1y", interval="1d"):
        """Fetch historical price data"""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=period, interval=interval)
            if data is None or data.empty:
                return None
            return data
        except Exception as e:
            print(f"Error fetching history for {self.symbol}: {e}")
            return None

    def calculate_value(self):
        """Calculate current value of holdings in EUR"""
        current_price = self.get_current_price()
        if current_price is not None:
            return round(current_price * self.shares, 2)
        return 0

    def calculate_gain_loss(self):
        """Calculate profit/loss in EUR"""
        current_price = self.get_current_price()
        if current_price is not None:
            invested = self.purchase_price * self.shares
            current_value = current_price * self.shares
            gain_loss = current_value - invested
            percentage = (gain_loss / invested * 100) if invested != 0 else 0
            return round(gain_loss, 2), round(percentage, 2)
        return 0, 0

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "purchase_price": self.purchase_price,
        }
