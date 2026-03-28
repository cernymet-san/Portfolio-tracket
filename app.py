import json
import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

from portfolio import Portfolio


# ===== PAGE CONFIG =====
st.set_page_config(page_title="Portfolio Tracker", layout="wide", page_icon="📈")

# ===== PASSWORD PROTECTION =====
def check_password():
    if st.session_state.get("authenticated"):
        return
    st.title("🔒 Login to Your Portfolio")
    with st.form("login_form"):
        pwd = st.text_input("Password:", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if pwd == st.secrets.get("password", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Wrong password. Try again.")
    st.stop()

check_password()


# ===== PERSISTENT SESSION STATE =====
def init_session_state():
    """Initialize portfolio in session state to persist during the session."""
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = Portfolio()
    return st.session_state.portfolio


ISIN_TO_TICKER = {
    "IE00BK5BQT80": "VWCE.DE",
    "IE00BKM4GZ66": "EMIM.AS",
    "IE00BSPLC298": "ZPRV.DE",
    "IE00BG0SKF03": "5MVL.DE",
}

# Symbol → emoji icon mapping
SYMBOL_ICONS = {
    "VWCE": "🌍", "VWCE.DE": "🌍",
    "VWRP": "🌍", "VWRP.DE": "🌍",
    "AVWS": "🌱", "AVWS.DE": "🌱",
    "5MVL": "📊", "5MVL.DE": "📊",
    "IS3S": "📈", "IS3S.DE": "📈",
    "EMIM": "🌏", "EMIM.AS": "🌏",
    "ZPRV": "🏦", "ZPRV.DE": "🏦",
    "ZPRX": "🏦", "ZPRX.DE": "🏦",
    "AAPL": "🍎", "MSFT": "💻", "GOOGL": "🔍",
    "AMZN": "📦", "TSLA": "⚡", "NVDA": "🎮",
    "BTC-EUR": "₿", "ETH-EUR": "⟠",
}

def get_icon(symbol: str) -> str:
    symbol_up = symbol.upper()
    if symbol_up in SYMBOL_ICONS:
        return SYMBOL_ICONS[symbol_up]
    base = symbol_up.split(".")[0]
    if base in SYMBOL_ICONS:
        return SYMBOL_ICONS[base]
    return "📌"

# ===== CUSTOM CSS =====
st.markdown("""
<style>
.metric-green { color: #00c853 !important; font-size: 2rem; font-weight: 700; margin: 0; }
.metric-red   { color: #ff1744 !important; font-size: 2rem; font-weight: 700; margin: 0; }
.metric-neutral { font-size: 2rem; font-weight: 700; margin: 0; }
.metric-label { color: #9e9e9e; font-size: 0.85rem; margin-bottom: 4px; margin-top: 0; }
.metric-box {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #2e2e3e;
    height: 100%;
}

/* Holding cards */
.holding-card {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 16px 18px;
    border: 1px solid #2e2e3e;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.holding-card-green { border-left: 4px solid #00c853 !important; }
.holding-card-red   { border-left: 4px solid #ff1744 !important; }
.holding-card-neutral { border-left: 4px solid #444 !important; }
.holding-icon { font-size: 2rem; margin-bottom: 4px; }
.holding-symbol { font-size: 1.1rem; font-weight: 700; margin: 0; }
.holding-shares { color: #9e9e9e; font-size: 0.8rem; margin: 0; }
.holding-value { font-size: 1.15rem; font-weight: 700; margin: 4px 0 0 0; }
.holding-gain-green { color: #00c853; font-size: 0.9rem; font-weight: 600; }
.holding-gain-red   { color: #ff1744; font-size: 0.9rem; font-weight: 600; }
.holding-alloc { color: #9e9e9e; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)


# ===== CACHED FETCHERS =====
@st.cache_data(ttl=300)
def fetch_last_close(ticker: str) -> float | None:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=3600)
def fetch_history_value(tickers: list[str], shares: list[float], period: str) -> pd.Series | None:
    if not tickers:
        return None
    try:
        data = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                           auto_adjust=False, progress=False)
        if data is None or data.empty:
            return None
        series_list = []
        if len(tickers) == 1:
            close = data.get("Close")
            if close is None or (hasattr(close, "empty") and close.empty):
                return None
            series_list.append(close * shares[0])
        else:
            for t, sh in zip(tickers, shares):
                lvl0 = data.columns.get_level_values(0)
                if t in lvl0 and "Close" in data[t].columns:
                    series_list.append(data[t]["Close"].ffill().fillna(0) * sh)
        if not series_list:
            return None
        return pd.concat(series_list, axis=1).ffill().fillna(0).sum(axis=1)
    except Exception:
        return None


# ===== PORTFOLIO TABLE BUILDER =====
def build_portfolio_table(p: Portfolio) -> pd.DataFrame:
    rows = []
    for s in p.stocks:
        current_price = fetch_last_close(s.symbol)
        invested = float(s.purchase_price) * float(s.shares)
        if current_price is None:
            current_value = gain_loss = pct = 0.0
        else:
            current_value = float(current_price) * float(s.shares)
            gain_loss = current_value - invested
            pct = (gain_loss / invested * 100) if invested else 0.0
        rows.append({
            "Symbol": s.symbol,
            "Shares": float(s.shares),
            "Buy Price (€)": float(s.purchase_price),
            "Current Price (€)": None if current_price is None else float(current_price),
            "Invested (€)": invested,
            "Current Value (€)": current_value,
            "Gain (€)": gain_loss,
            "Gain (%)": pct,
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Symbol", "Shares", "Buy Price (€)", "Current Price (€)",
            "Invested (€)", "Current Value (€)", "Gain (€)", "Gain (%)",
        ])
    return pd.DataFrame(rows).sort_values("Current Value (€)", ascending=False).reset_index(drop=True)


def style_portfolio(df: pd.DataFrame):
    def color_gain(val):
        if pd.isna(val): return ""
        if val > 0: return "color: #00c853; font-weight: 600;"
        if val < 0: return "color: #ff1744; font-weight: 600;"
        return "color: #9e9e9e;"
    def bg_gain(val):
        if pd.isna(val): return ""
        if val > 0: return "background-color: rgba(0,200,83,0.08);"
        if val < 0: return "background-color: rgba(255,23,68,0.08);"
        return ""
    fmt = {
        "Shares": "{:,.6f}",
        "Buy Price (€)": "€{:,.2f}",
        "Current Price (€)": "€{:,.2f}",
        "Invested (€)": "€{:,.2f}",
        "Current Value (€)": "€{:,.2f}",
        "Gain (€)": "€{:+,.2f}",
        "Gain (%)": "{:+,.2f}%",
    }
    return (
        df.style
        .format(fmt, na_rep="N/A")
        .applymap(color_gain, subset=["Gain (€)", "Gain (%)"])
        .applymap(bg_gain, subset=["Gain (€)", "Gain (%)"])
    )


# ===== LOAD PORTFOLIO WITH SESSION STATE =====
p = init_session_state()


# ===== SIDEBAR =====
st.sidebar.header("⚙️ Actions")

with st.sidebar.expander("➕ Add stock", expanded=True):
    sym = st.text_input("Symbol (e.g. VWCE.DE, BTC-EUR)", key="add_sym")
    sh = st.number_input("Shares", min_value=0.0, value=0.0, step=0.01, format="%.6f", key="add_sh")
    buy = st.number_input("Buy price (€)", min_value=0.0, value=0.0, step=0.01, format="%.4f", key="add_buy")
    if st.button("Add / Update", use_container_width=True):
        if sym.strip() and sh > 0:
            p.add_stock(sym.strip(), float(sh), float(buy))
            fetch_last_close.clear()
            st.success(f"✅ Added/updated {sym.strip()}")
            st.rerun()
        else:
            st.error("❌ Enter a valid symbol and shares > 0")

with st.sidebar.expander("➖ Remove stock", expanded=False):
    remove_sym = st.text_input("Symbol to remove", key="rm_sym")
    if st.button("Remove", use_container_width=True):
        if remove_sym.strip():
            p.remove_stock(remove_sym.strip())
            fetch_last_close.clear()
            st.success(f"✅ Removed {remove_sym.strip()}")
            st.rerun()
        else:
            st.error("❌ Enter a symbol to remove")

with st.sidebar.expander("📥 Import Portfolio (.json)", expanded=False):
    json_file = st.file_uploader("Upload portfolio.json", type=["json"], key="json_upload")
    overwrite_json = st.checkbox("Overwrite existing portfolio", value=False, key="json_overwrite")
    if json_file and st.button("Import JSON", use_container_width=True):
        try:
            data = json.load(json_file)
            stocks = data.get("stocks", [])
            if not stocks:
                st.error("❌ No stocks found in JSON file.")
            else:
                if overwrite_json:
                    p.stocks = []
                for s in stocks:
                    p.add_stock(s["symbol"], float(s["shares"]), float(s["purchase_price"]))
                p.save_portfolio()
                fetch_last_close.clear()
                fetch_history_value.clear()
                st.success(f"✅ Imported {len(stocks)} stocks from JSON")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to import JSON: {e}")

with st.sidebar.expander("📥 Import XTB Positions (.xlsx)", expanded=False):
    xtb_file = st.file_uploader("Upload XTB XLSX", type=["xlsx"], key="xtb_upload")
    if xtb_file and st.button("Import XTB XLSX", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(xtb_file.getbuffer())
            tmp_path = tmp.name
        try:
            p.import_xtb_positions_xlsx(tmp_path)
            fetch_last_close.clear()
            fetch_history_value.clear()
            st.success("✅ Imported XTB XLSX into portfolio")
            st.rerun()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

with st.sidebar.expander("📥 Import DEGIRO Transactions (.csv)", expanded=False):
    degiro_file = st.file_uploader("Upload DEGIRO Transactions CSV", type=["csv"], key="degiro_upload")
    st.caption("Requires ISIN_TO_TICKER mapping in app.py.")
    if degiro_file and st.button("Import DEGIRO CSV", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(degiro_file.getbuffer())
            tmp_path = tmp.name
        try:
            p.import_degiro_transactions_csv(tmp_path, ISIN_TO_TICKER, overwrite=False)
            fetch_last_close.clear()
            fetch_history_value.clear()
            st.success("✅ Imported DEGIRO CSV into portfolio")
            st.rerun()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

with st.sidebar.expander("📥 Import Anycoin Crypto (.csv)", expanded=False):
    anycoin_file = st.file_uploader("Upload Anycoin CSV", type=["csv"], key="anycoin_upload")
    czk_rate = st.number_input("CZK per EUR", min_value=1.0, value=25.0, step=0.5, key="czk_rate")
    if anycoin_file and st.button("Import Anycoin CSV", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(anycoin_file.getbuffer())
            tmp_path = tmp.name
        try:
            p.import_anycoin_trade_fills_csv(tmp_path, overwrite=False, czk_per_eur=czk_rate)
            fetch_last_close.clear()
            fetch_history_value.clear()
            st.success("✅ Imported Anycoin crypto positions")
            st.rerun()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

st.sidebar.divider()
if p.stocks:
    export_data = json.dumps({"stocks": [s.to_dict() for s in p.stocks]}, indent=4)
    st.sidebar.download_button(
        label="💾 Export Portfolio as JSON",
        data=export_data,
        file_name="portfolio.json",
        mime="application/json",
        use_container_width=True,
    )

st.sidebar.divider()
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()


# ==============================
# MAIN LAYOUT
# ==============================
st.title("📈 Portfolio Tracker")

df = build_portfolio_table(p)

# ===== SUMMARY METRIC CARDS =====
if not df.empty:
    total_invested = float(df["Invested (€)"].sum())
    total_value = float(df["Current Value (€)"].sum())
    total_gain = total_value - total_invested
    total_pct = (total_gain / total_invested * 100) if total_invested else 0.0

    gain_color = "metric-green" if total_gain >= 0 else "metric-red"
    pct_color  = "metric-green" if total_pct  >= 0 else "metric-red"

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><p class="metric-label">Total Invested</p><p class="metric-neutral">€{total_invested:,.2f}</p></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><p class="metric-label">Current Value</p><p class="metric-neutral">€{total_value:,.2f}</p></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><p class="metric-label">Gain / Loss (€)</p><p class="{gain_color}">€{total_gain:+,.2f}</p></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><p class="metric-label">Gain / Loss (%)</p><p class="{pct_color}">{total_pct:+.2f}%</p></div>', unsafe_allow_html=True)

    st.divider()

    # ===== DONUT CHART + HOLDINGS GRID =====
    chart_col, grid_col = st.columns([1, 2], gap="large")

    with chart_col:
        st.subheader("🥧 Allocation")
        fig = px.pie(
            df,
            names="Symbol",
            values="Current Value (€)",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_traces(
            textposition="outside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>",
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with grid_col:
        st.subheader("📦 Holdings")
        cols_per_row = 3
        rows = [df.iloc[i:i+cols_per_row] for i in range(0, len(df), cols_per_row)]
        for row in rows:
            cols = st.columns(cols_per_row)
            for col, (_, holding) in zip(cols, row.iterrows()):
                symbol = holding["Symbol"]
                icon = get_icon(symbol)
                value = holding["Current Value (€)"]
                gain_eur = holding["Gain (€)"]
                gain_pct = holding["Gain (%)"]
                alloc = (value / total_value * 100) if total_value else 0

                if gain_pct > 0:
                    card_class = "holding-card holding-card-green"
                    gain_class = "holding-gain-green"
                    gain_arrow = "▲"
                elif gain_pct < 0:
                    card_class = "holding-card holding-card-red"
                    gain_class = "holding-gain-red"
                    gain_arrow = "▼"
                else:
                    card_class = "holding-card holding-card-neutral"
                    gain_class = "holding-gain-green"
                    gain_arrow = "—"

                with col:
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div class="holding-icon">{icon}</div>
                        <p class="holding-symbol">{symbol}</p>
                        <p class="holding-shares">{holding['Shares']:,.4f} shares</p>
                        <p class="holding-value">€{value:,.2f}</p>
                        <span class="{gain_class}">{gain_arrow} {gain_pct:+.2f}% (€{gain_eur:+,.2f})</span><br>
                        <span class="holding-alloc">{alloc:.1f}% of portfolio</span>
                    </div>
                    """, unsafe_allow_html=True)

    st.divider()

    # ===== PORTFOLIO VALUE HISTORY =====
    st.subheader("📊 Portfolio Value History")
    period_col, _ = st.columns([1, 5])
    with period_col:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

    tickers = df["Symbol"].tolist()
    shares_list = df["Shares"].tolist()
    series = fetch_history_value(tickers, shares_list, period=period)
    if series is None or series.empty:
        st.warning("⚠️ No history data available for chart.")
    else:
        st.line_chart(
            pd.DataFrame({"Portfolio Value (€)": series}),
            use_container_width=True,
            height=400,
        )

    st.divider()

    # ===== FULL TABLE =====
    st.subheader("📋 Full Holdings Table")
    st.dataframe(style_portfolio(df), use_container_width=True, height=400)

else:
    st.info("📭 Portfolio is empty. Add a stock or import a file from the sidebar.")
    