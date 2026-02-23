import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
from stock import Stock


class Portfolio:
    """Manages a collection of stocks"""

    def __init__(self, filename="data/portfolio.json"):
        self.filename = filename
        self.stocks = []
        self.load_portfolio()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def add_stock(self, symbol, shares, purchase_price):
        symbol = symbol.upper().strip()
        for existing in self.stocks:
            if existing.symbol == symbol:
                print(f"⚠️  {symbol} already exists. Adding shares.")
                existing.shares += shares
                self.save_portfolio()
                return
        self.stocks.append(Stock(symbol, shares, purchase_price))
        self.save_portfolio()
        print(f"✅ Added {shares} shares of {symbol} at €{purchase_price}")

    def remove_stock(self, symbol):
        self.stocks = [s for s in self.stocks if s.symbol != symbol.upper().strip()]
        self.save_portfolio()
        print(f"🗑️  Removed {symbol.upper()} from portfolio")

    # ------------------------------------------------------------------
    # Display / Stats
    # ------------------------------------------------------------------

    def display_portfolio(self):
        if not self.stocks:
            print("📭 Your portfolio is empty!")
            return

        table_data = []
        total_value = 0
        total_invested = 0

        for stock in self.stocks:
            price = stock.get_current_price()
            value = stock.calculate_value()
            gain, pct = stock.calculate_gain_loss()
            invested = stock.purchase_price * stock.shares

            gl_str = f"€{gain:+.2f} ({pct:+.2f}%)"
            gl_str = f"🟢 {gl_str}" if gain > 0 else f"🔴 {gl_str}" if gain < 0 else f"⚪ {gl_str}"

            table_data.append([
                stock.symbol,
                stock.shares,
                f"€{stock.purchase_price:.2f}",
                f"€{price:.2f}" if price is not None else "N/A",
                f"€{invested:.2f}",
                f"€{value:.2f}",
                gl_str,
            ])
            total_value += value
            total_invested += invested

        headers = [
            "Symbol", "Shares", "Buy Price (€)", "Current Price (€)",
            "Invested (€)", "Current Value (€)", "Gain / Loss",
        ]
        print("\n" + "=" * 100)
        print("📊 YOUR PORTFOLIO (EUR)")
        print("=" * 100)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        total_gain = total_value - total_invested
        total_pct = (total_gain / total_invested * 100) if total_invested else 0
        print("\n" + "=" * 100)
        print("💰 PORTFOLIO SUMMARY (€)")
        print("=" * 100)
        print(f"Total Invested:    €{total_invested:,.2f}")
        print(f"Current Value:     €{total_value:,.2f}")
        print(f"Total Gain/Loss:   €{total_gain:+,.2f} ({total_pct:+.2f}%)")
        print("=" * 100)

    def get_portfolio_stats(self):
        if not self.stocks:
            return None

        total_value = sum(s.calculate_value() for s in self.stocks)
        total_invested = sum(s.purchase_price * s.shares for s in self.stocks)

        performers = sorted(
            [(s.symbol, s.calculate_gain_loss()[1]) for s in self.stocks],
            key=lambda x: x[1],
            reverse=True,
        )

        return {
            "total_stocks": len(self.stocks),
            "total_value": total_value,
            "total_invested": total_invested,
            "best_performer": performers[0] if performers else None,
            "worst_performer": performers[-1] if performers else None,
        }

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------

    def plot_stock_history(self, symbol, period="1y"):
        stock = next((s for s in self.stocks if s.symbol == symbol.upper()), None)
        if not stock:
            print("❌ Stock not found")
            return
        hist = stock.get_price_history(period)
        if hist is None:
            print("❌ No data available")
            return
        plt.figure()
        plt.plot(hist.index, hist["Close"])
        plt.title(f"{symbol.upper()} price history (€)")
        plt.xlabel("Date")
        plt.ylabel("Price (€)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def plot_portfolio_value(self, period="1y"):
        if not self.stocks:
            print("📭 Portfolio empty")
            return
        series = []
        for stock in self.stocks:
            hist = stock.get_price_history(period)
            if hist is None:
                continue
            s = hist["Close"] * stock.shares
            s.name = stock.symbol
            series.append(s)
        if not series:
            print("❌ No historical data")
            return
        df = pd.concat(series, axis=1).ffill().fillna(0)
        portfolio_value = df.sum(axis=1)
        plt.figure()
        plt.plot(portfolio_value.index, portfolio_value.values)
        plt.title("Portfolio Value (€)")
        plt.xlabel("Date")
        plt.ylabel("Value (€)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    # ------------------------------------------------------------------
    # Importers
    # ------------------------------------------------------------------

    def import_degiro_transactions_csv(self, csv_path, isin_to_ticker, overwrite=False):
        """
        Import DEGIRO Transactions.csv and rebuild positions.
        Expected columns: Datum, Čas, ISIN, Počet, Celkem EUR
        """
        if not os.path.exists(csv_path):
            print(f"❌ File not found: {csv_path}")
            return

        try:
            df = pd.read_csv(csv_path)

            required = {"Datum", "Čas", "ISIN", "Počet", "Celkem EUR"}
            missing = required - set(df.columns)
            if missing:
                print(f"❌ CSV missing columns: {missing}")
                return

            df["dt"] = pd.to_datetime(
                df["Datum"].astype(str) + " " + df["Čas"].astype(str),
                dayfirst=True,
                errors="coerce",
            )

            def to_float(series):
                return pd.to_numeric(
                    series.astype(str)
                    .str.replace("\u00A0", "")
                    .str.replace(" ", "")
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                )

            df["qty"] = to_float(df["Počet"])
            df["cash"] = to_float(df["Celkem EUR"])
            df = df.dropna(subset=["dt", "ISIN", "qty", "cash"]).sort_values("dt")

            if overwrite:
                self.stocks = []

            positions = {}
            for _, r in df.iterrows():
                isin = r["ISIN"]
                qty = r["qty"]
                cash = r["cash"]

                if isin not in isin_to_ticker:
                    continue

                if isin not in positions:
                    positions[isin] = {"shares": 0.0, "cost": 0.0}

                pos = positions[isin]
                if qty > 0:  # BUY
                    pos["shares"] += qty
                    pos["cost"] += -cash
                elif qty < 0 and pos["shares"] > 0:  # SELL
                    avg_cost = pos["cost"] / pos["shares"]
                    pos["cost"] -= avg_cost * (-qty)
                    pos["shares"] += qty

            for isin, pos in positions.items():
                if pos["shares"] <= 0:
                    continue
                ticker = isin_to_ticker[isin]
                avg_price = pos["cost"] / pos["shares"]
                self.add_stock(ticker, pos["shares"], avg_price)

            self.save_portfolio()
            print("✅ DEGIRO CSV imported successfully")

        except Exception as e:
            print(f"❌ Import failed: {e}")

    def import_xtb_positions_xlsx(self, xlsx_path, sheet_name=0, overwrite=False):
        """
        Import XTB 'Positions' XLSX.
        Expected columns: Symbol, Type, Volume, Open price
        Groups by Symbol; avg buy price = weighted average of Open price by Volume.
        """
        if not os.path.exists(xlsx_path):
            print(f"❌ File not found: {xlsx_path}")
            return

        try:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

            required = {"Symbol", "Type", "Volume", "Open price"}
            missing = required - set(df.columns)
            if missing:
                print(f"❌ XLSX missing columns: {missing}")
                print(f"Found columns: {list(df.columns)}")
                return

            df["Symbol"] = df["Symbol"].astype(str).str.strip()
            df = df[df["Symbol"].str.lower() != "total"]
            df = df[df["Symbol"] != ""]
            df["Type"] = df["Type"].astype(str).str.upper().str.strip()
            df = df[df["Type"] == "BUY"]

            def to_float(series):
                return pd.to_numeric(
                    series.astype(str)
                    .str.replace("\u00A0", "")
                    .str.replace(" ", "")
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                )

            df["Volume"] = to_float(df["Volume"])
            df["Open price"] = to_float(df["Open price"])
            df = df.dropna(subset=["Volume", "Open price"])

            if overwrite:
                self.stocks = []

            grouped = (
                df.groupby("Symbol", as_index=False)
                .apply(
                    lambda g: pd.Series({
                        "shares": g["Volume"].sum(),
                        "avg_buy": (
                            (g["Volume"] * g["Open price"]).sum() / g["Volume"].sum()
                            if g["Volume"].sum() != 0 else 0.0
                        ),
                    })
                )
                .reset_index(drop=True)
            )

            imported = 0
            for _, row in grouped.iterrows():
                self.add_stock(str(row["Symbol"]).strip().upper(), float(row["shares"]), float(row["avg_buy"]))
                imported += 1

            self.save_portfolio()
            print(f"✅ Imported {imported} symbols from XTB XLSX positions report")

        except Exception as e:
            print(f"❌ XTB XLSX import failed: {e}")

    def import_anycoin_trade_fills_csv(self, csv_path, overwrite=False, czk_per_eur=25.0):
        """
        Import Anycoin CSV (trade payment + trade fill) for BTC/ETH positions.
        Columns: Date, Type, Amount, Currency, Order ID, anycoin TX ID, Description
        CZK payments are converted to EUR using czk_per_eur.
        """
        if not os.path.exists(csv_path):
            print(f"❌ File not found: {csv_path}")
            return

        try:
            df = pd.read_csv(csv_path)

            required = {"Type", "Amount", "Currency", "Order ID"}
            missing = required - set(df.columns)
            if missing:
                print(f"❌ CSV missing columns: {missing}")
                print(f"Found columns: {list(df.columns)}")
                return

            df["Type"] = df["Type"].astype(str).str.strip().str.lower()
            df = df[df["Type"].isin(["trade payment", "trade fill"])].copy()

            def to_float(series):
                return pd.to_numeric(
                    series.astype(str)
                    .str.replace("\u00A0", "")
                    .str.replace(" ", "")
                    .str.replace(",", ".", regex=False),
                    errors="coerce",
                )

            df["Amount"] = to_float(df["Amount"])
            df["Currency"] = df["Currency"].astype(str).str.strip().str.upper()
            df["Order ID"] = df["Order ID"].astype(str).str.strip()
            df = df.dropna(subset=["Amount", "Currency", "Order ID"])

            payments = df[(df["Type"] == "trade payment") & (df["Currency"] == "CZK")].copy()
            fills = df[(df["Type"] == "trade fill") & (df["Currency"].isin(["BTC", "ETH"]))].copy()

            if payments.empty or fills.empty:
                print("❌ No usable trade payment / trade fill rows found.")
                return

            pay_by_order = payments.set_index("Order ID")["Amount"].to_dict()
            positions = {
                "BTC": {"qty": 0.0, "cost_eur": 0.0},
                "ETH": {"qty": 0.0, "cost_eur": 0.0},
            }
            skipped = 0

            for _, r in fills.iterrows():
                order_id = r["Order ID"]
                asset = r["Currency"]
                qty = float(r["Amount"])

                if order_id not in pay_by_order or qty <= 0:
                    skipped += 1
                    continue

                cost_eur = abs(float(pay_by_order[order_id])) / float(czk_per_eur)
                positions[asset]["qty"] += qty
                positions[asset]["cost_eur"] += cost_eur

            if overwrite:
                self.stocks = []

            imported = 0
            for asset, pos in positions.items():
                if pos["qty"] <= 0:
                    continue
                avg_buy = pos["cost_eur"] / pos["qty"]
                self.add_stock(f"{asset}-EUR", round(pos["qty"], 8), round(avg_buy, 2))
                imported += 1

            self.save_portfolio()
            print(f"✅ Imported Anycoin crypto positions: {imported} (BTC/ETH)")
            if skipped:
                print(f"ℹ️  Skipped {skipped} fill rows (missing payment or invalid qty).")
            print(f"ℹ️  FX used: 1 EUR = {czk_per_eur} CZK (adjust if needed).")

        except Exception as e:
            print(f"❌ Anycoin import failed: {e}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_portfolio(self):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        with open(self.filename, "w") as f:
            json.dump({"stocks": [s.to_dict() for s in self.stocks]}, f, indent=4)

    def load_portfolio(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename) as f:
                    data = json.load(f)
                    self.stocks = [Stock(**d) for d in data.get("stocks", [])]
                print(f"✅ Loaded {len(self.stocks)} stocks")
            except Exception as e:
                print(f"⚠️  Error loading portfolio: {e}")
                self.stocks = []
