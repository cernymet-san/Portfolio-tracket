import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
from stock import Stock

warnings.filterwarnings("ignore", message="Workbook contains no default style", category=UserWarning, module="openpyxl")


class Portfolio:
    """Manages a collection of stocks"""

    def __init__(self, filename="data/portfolio.json"):
        self.filename = filename
        self.stocks = []
        self.load_portfolio()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def add_stock(self, symbol, shares, purchase_price, purchase_date=None):
        symbol = symbol.upper().strip()
        for existing in self.stocks:
            if existing.symbol == symbol:
                print(f"⚠️  {symbol} already exists. Adding shares.")
                existing.shares += shares
                if purchase_date and not existing.purchase_date:
                    existing.purchase_date = purchase_date
                self.save_portfolio()
                return
        self.stocks.append(Stock(symbol, shares, purchase_price, purchase_date))
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

    def import_degiro_transactions_csv(self, csv_path, isin_to_ticker=None, overwrite=False):
        """
        Import DEGIRO Transactions.csv and rebuild positions.
        Expected columns: Datum, Čas, ISIN, Počet, Celkem EUR
        Unknown ISINs are resolved via yf.Search() automatically.
        """
        import yfinance as yf

        if isin_to_ticker is None:
            isin_to_ticker = {}

        def _resolve_isin(args: tuple) -> tuple[str, str | None]:
            isin, product_name = args
            if isin in isin_to_ticker:
                return isin, isin_to_ticker[isin]
            for query in [isin, product_name]:
                if not query:
                    continue
                try:
                    results = yf.Search(query, max_results=5).quotes
                    etfs = [r for r in results if r.get("quoteType", "").upper() == "ETF"]
                    best = etfs[0] if etfs else (results[0] if results else None)
                    if best and best.get("symbol"):
                        ticker = best["symbol"]
                        print(f"  🔍 Resolved ISIN '{isin}' → {ticker}")
                        return isin, ticker
                except Exception:
                    continue
            print(f"  ⚠️ Could not resolve ISIN '{isin}'")
            return isin, None

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

            # Grab product name column if present (helps with search)
            name_col = next((c for c in df.columns if "product" in c.lower() or "naam" in c.lower() or "název" in c.lower()), None)

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

            # Resolve all unique ISINs in parallel
            unique_isins = df["ISIN"].unique().tolist()
            isin_names = {
                r["ISIN"]: (str(r[name_col]) if name_col else "")
                for _, r in df.drop_duplicates("ISIN").iterrows()
            }
            with ThreadPoolExecutor(max_workers=8) as ex:
                ticker_map = dict(ex.map(_resolve_isin, [(i, isin_names.get(i, "")) for i in unique_isins]))

            if overwrite:
                self.stocks = []

            positions = {}
            for _, r in df.iterrows():
                isin = r["ISIN"]
                qty = r["qty"]
                cash = r["cash"]

                ticker = ticker_map.get(isin)
                if not ticker:
                    continue

                if isin not in positions:
                    positions[isin] = {"ticker": ticker, "shares": 0.0, "cost": 0.0, "dt": r["dt"]}

                pos = positions[isin]
                if qty > 0:  # BUY
                    pos["shares"] += qty
                    pos["cost"] += -cash
                elif qty < 0 and pos["shares"] > 0:  # SELL
                    avg_cost = pos["cost"] / pos["shares"]
                    pos["cost"] -= avg_cost * (-qty)
                    pos["shares"] += qty

            imported = 0
            for isin, pos in positions.items():
                if pos["shares"] <= 0:
                    continue
                avg_price = pos["cost"] / pos["shares"]
                purchase_date = pos["dt"].date().isoformat() if pd.notna(pos["dt"]) else None
                self.add_stock(ticker_map[isin], pos["shares"], avg_price, purchase_date=purchase_date)
                imported += 1

            self.save_portfolio()
            print(f"✅ DEGIRO CSV imported: {imported} positions")

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

            # Normalize column names: strip whitespace, lowercase for matching
            df.columns = df.columns.str.strip()
            col_map = {c.lower(): c for c in df.columns}
            print(f"  ℹ️ XTB Positions columns: {list(df.columns)}")

            # Flexible column name matching
            def find_col(*candidates):
                for c in candidates:
                    if c in col_map:
                        return col_map[c]
                return None

            sym_col   = find_col("symbol")
            type_col  = find_col("type", "direction")
            vol_col   = find_col("volume", "quantity", "shares")
            price_col = find_col("open price", "openprice", "open_price", "price")

            missing = [n for n, c in [("Symbol", sym_col), ("Type", type_col), ("Volume", vol_col), ("Open price", price_col)] if c is None]
            if missing:
                print(f"❌ Could not find columns: {missing}")
                print(f"   Available: {list(df.columns)}")
                return

            # Rename to standard names
            df = df.rename(columns={sym_col: "Symbol", type_col: "Type", vol_col: "Volume", price_col: "Open price"})

            df["Symbol"] = df["Symbol"].astype(str).str.strip()
            df = df[df["Symbol"].str.lower() != "total"]
            df = df[df["Symbol"].str.strip() != ""]
            df["Type"] = df["Type"].astype(str).str.upper().str.strip()

            print(f"  ℹ️ Unique Type values: {df['Type'].unique().tolist()}")

            # Accept BUY, LONG, or any positive direction
            df = df[df["Type"].isin(["BUY", "LONG", "B", "PURCHASE"])]

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
            print(f"  ℹ️ Rows after filtering: {len(df)}")

            if len(df) == 0:
                print("❌ No valid rows found after filtering. Check Type values and column names above.")
                return

            if overwrite:
                self.stocks = []

            grouped = df.groupby("Symbol").apply(
                lambda g: pd.Series({
                    "shares": g["Volume"].sum(),
                    "avg_buy": (
                        (g["Volume"] * g["Open price"]).sum() / g["Volume"].sum()
                        if g["Volume"].sum() != 0 else 0.0
                    ),
                }), include_groups=False
            ).reset_index()

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

    def import_xtb_cash_operations_xlsx(self, xlsx_path, instrument_to_ticker=None, overwrite=False):
        """
        Import XTB Cash Operations XLSX report.
        Expected columns: Type, Instrument, Time, Amount, ID, Comment
        Comment format: "OPEN BUY shares/total @ price" or "OPEN BUY shares @ price"
        instrument_to_ticker: optional dict of known mappings; unknown instruments are resolved via yf.Search()
        """
        import re
        import warnings
        import yfinance as yf

        if instrument_to_ticker is None:
            instrument_to_ticker = {}

        def _search_ticker(instrument_name: str) -> tuple[str, str | None]:
            if instrument_name in instrument_to_ticker:
                return instrument_name, instrument_to_ticker[instrument_name]
            try:
                results = yf.Search(instrument_name, max_results=5).quotes
                etfs = [r for r in results if r.get("quoteType", "").upper() == "ETF"]
                best = etfs[0] if etfs else (results[0] if results else None)
                if best and best.get("symbol"):
                    ticker = best["symbol"]
                    print(f"  🔍 Resolved '{instrument_name}' → {ticker}")
                    return instrument_name, ticker
            except Exception as e:
                print(f"  ⚠️ Could not resolve '{instrument_name}': {e}")
            return instrument_name, None

        def resolve_tickers_parallel(names: list) -> dict:
            # Already known — skip API calls
            unknown = [n for n in names if n not in instrument_to_ticker]
            result = {n: instrument_to_ticker[n] for n in names if n in instrument_to_ticker}
            if unknown:
                with ThreadPoolExecutor(max_workers=8) as ex:
                    for name, ticker in ex.map(_search_ticker, unknown):
                        result[name] = ticker
            return result

        if not os.path.exists(xlsx_path):
            print(f"❌ File not found: {xlsx_path}")
            return

        try:
            # Find the header row (contains "Type")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                raw = pd.read_excel(xlsx_path, header=None)
            header_row = None
            for i, row in raw.iterrows():
                if "Type" in row.values:
                    header_row = i
                    break
            if header_row is None:
                print("❌ Could not find header row with 'Type' column")
                return

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df = pd.read_excel(xlsx_path, header=header_row)
            df.columns = df.columns.str.strip()

            required = {"Type", "Instrument", "Time", "Comment"}
            missing = required - set(df.columns)
            if missing:
                print(f"❌ Missing columns: {missing}")
                return

            df = df[df["Type"].astype(str).str.strip() == "Stock purchase"].copy()
            if df.empty:
                print("❌ No 'Stock purchase' rows found")
                return

            def parse_comment(comment):
                """Extract (shares, price) from 'OPEN BUY x/y @ p' or 'OPEN BUY x @ p'"""
                m = re.search(r"OPEN BUY\s+([\d.]+)(?:/[\d.]+)?\s*@\s*([\d.]+)", str(comment))
                if m:
                    return float(m.group(1)), float(m.group(2))
                return None, None

            df["_shares"], df["_price"] = zip(*df["Comment"].map(parse_comment))
            df = df.dropna(subset=["_shares", "_price"])
            df["_shares"] = df["_shares"].astype(float)
            df["_price"] = df["_price"].astype(float)
            df["Instrument"] = df["Instrument"].astype(str).str.strip()

            df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

            if overwrite:
                self.stocks = []

            instruments = df["Instrument"].unique().tolist()
            ticker_map = resolve_tickers_parallel(instruments)

            imported = 0
            skipped = []
            for instrument, group in df.groupby("Instrument"):
                ticker = ticker_map.get(instrument)
                if not ticker:
                    skipped.append(instrument)
                    continue
                total_shares = group["_shares"].sum()
                avg_price = (group["_shares"] * group["_price"]).sum() / total_shares
                earliest_date = group["Time"].min().date().isoformat() if not group["Time"].isna().all() else None
                self.add_stock(ticker, round(total_shares, 6), round(avg_price, 4), purchase_date=earliest_date)
                imported += 1

            self.save_portfolio()
            print(f"✅ Imported XTB Cash Operations: {imported} instruments")
            if skipped:
                print(f"⚠️  Could not resolve tickers for: {skipped}")

        except Exception as e:
            print(f"❌ XTB Cash Operations import failed: {e}")

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
