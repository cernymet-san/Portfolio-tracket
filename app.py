import json
import os
import tempfile
from datetime import date

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
        if st.form_submit_button("Login", width="stretch"):
            if pwd == st.secrets.get("password", ""):
                st.session_state.authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Wrong password. Try again.")
    st.stop()

check_password()


# ===== PERSISTENT SESSION STATE =====
def init_session_state():
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = Portfolio()
    return st.session_state.portfolio


ISIN_TO_TICKER = {
    "IE00BK5BQT80": "VWCE.DE",
    "IE00BKM4GZ66": "EMIM.AS",
    "IE00BSPLC298": "ZPRV.DE",
    "IE00BG0SKF03": "5MVL.DE",
}

# XTB Cash Operations: Instrument name → ticker symbol
XTB_INSTRUMENT_TO_TICKER = {
    "FTSE All-World": "VWCE.DE",
    "MSCI USA Small Cap V-Weighted": "ZPRV.DE",
    "Core MSCI EM IMI": "EMIM.AS",
    "Edge MSCI EM ValueFactor": "5MVL.DE",
}

AVATAR_COLORS = [
    "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444",
    "#06b6d4", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
]

CRYPTO_BASES = {"BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "XRP", "LTC", "BCH", "DOGE", "SHIB"}
CRYPTO_SUFFIXES = ("-EUR", "-USD", "-GBP", "-USDT", "-BTC")
ETF_BASES = {
    "VWCE", "VWRP", "EMIM", "ZPRV", "ZPRX", "5MVL", "IS3S", "AVWS",
    "VOO", "SPY", "QQQ", "VTI", "IWDA", "CSPX", "EUNL", "AGGH",
}


def get_asset_type(symbol: str) -> str:
    sym = symbol.upper()
    base = sym.split(".")[0].split("-")[0]
    if any(sym.endswith(s) for s in CRYPTO_SUFFIXES) or base in CRYPTO_BASES:
        return "crypto"
    if base in ETF_BASES:
        return "etf"
    return "stock"


def get_avatar_color(symbol: str) -> str:
    return AVATAR_COLORS[abs(hash(symbol)) % len(AVATAR_COLORS)]


def get_avatar_text(symbol: str) -> str:
    base = symbol.split(".")[0].split("-")[0]
    return base[:2].upper()


# ===== CUSTOM CSS =====
st.markdown("""
<style>
/* ── Global ── */
.stApp { background-color: #f4f6fa; }
.block-container { padding: 1.5rem 2rem 2rem 2rem !important; }

/* ── Sidebar dark theme ── */
[data-testid="stSidebar"] { background-color: #1e2139 !important; }
[data-testid="stSidebar"] > div { background-color: #1e2139 !important; }

/* Hide default radio label */
[data-testid="stSidebar"] .stRadio > label { display: none; }

/* Nav radio items */
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
    background: transparent;
    border-radius: 10px;
    padding: 10px 16px;
    cursor: pointer;
    color: #a0a8c0 !important;
    font-size: 0.9rem;
    transition: background 0.15s;
}
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:hover {
    background: rgba(255,255,255,0.07);
    color: #fff !important;
}
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"][aria-checked="true"] {
    background: rgba(255,255,255,0.12) !important;
    color: #fff !important;
    font-weight: 600;
}
/* Hide the radio circle dot */
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] > div:first-child { display: none; }

/* Sidebar text */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: #a0a8c0 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #fff !important; }

/* Sidebar logout button */
[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.07) !important;
    color: #a0a8c0 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.14) !important;
    color: #fff !important;
}

/* ── White cards (used by plotly & line charts automatically) ── */
[data-testid="stPlotlyChart"] {
    background: white;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}
[data-testid="stArrowVegaLiteChart"] {
    background: white;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
}

/* ── Metric cards ── */
.mc {
    background: white;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    margin-bottom: 4px;
}
.mc .lbl { color: #9e9e9e; font-size: 0.78rem; font-weight: 500; margin: 0 0 6px 0; }
.mc .val { font-size: 1.55rem; font-weight: 700; color: #1a1c2e; margin: 0; }
.mc .val-g { color: #22c55e; }
.mc .val-r { color: #ef4444; }

/* ── Holdings table ── */
.ht-wrap {
    background: white;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    margin-top: 8px;
}
.ht-title { font-size: 1rem; font-weight: 700; color: #1a1c2e; margin: 0 0 16px 0; }
.ht { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.ht th {
    color: #9e9e9e; font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em;
    padding: 0 16px 12px 16px; text-align: left;
    border-bottom: 1px solid #f0f0f0;
}
.ht td {
    padding: 13px 16px; border-bottom: 1px solid #f8f8f8;
    vertical-align: middle; color: #1a1c2e;
}
.ht tr:last-child td { border-bottom: none; }
.ht tr:hover td { background: #fafbfd; }

.av {
    width: 38px; height: 38px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.72rem; color: white; flex-shrink: 0;
}
.an { font-weight: 600; font-size: 0.88rem; color: #1a1c2e; margin: 0; }
.as { color: #9e9e9e; font-size: 0.75rem; margin: 0; }
.tag {
    display: inline-block; padding: 1px 7px;
    border-radius: 4px; font-size: 0.67rem; font-weight: 600;
}
.tag-crypto { background: #fff3e0; color: #f59e0b; }
.tag-stock  { background: #e8f5e9; color: #22c55e; }
.tag-etf    { background: #e3f2fd; color: #3b82f6; }
.gp { color: #22c55e; font-weight: 600; }
.gn { color: #ef4444; font-weight: 600; }
.ab-bg {
    background: #f0f0f0; border-radius: 4px; height: 6px;
    width: 70px; display: inline-block; vertical-align: middle;
    margin-right: 8px; overflow: hidden;
}
.ab-fill { background: #3b82f6; border-radius: 4px; height: 6px; }

/* ── Section title ── */
.sec-title {
    font-size: 1rem; font-weight: 700; color: #1a1c2e;
    margin: 0 0 14px 0; padding: 20px 24px 0 24px;
}
</style>
""", unsafe_allow_html=True)


# ===== CACHED FETCHERS =====
@st.cache_data(ttl=60)
def search_tickers(query: str) -> list[tuple[str, str]]:
    if not query:
        return []
    try:
        results = yf.Search(query, max_results=8).quotes
        return [
            (r.get("symbol", ""), r.get("longname") or r.get("shortname", ""))
            for r in results if r.get("symbol")
        ]
    except Exception:
        return []


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
def fetch_history_value(tickers: list[str], shares: list[float], period: str = "1y", start: str | None = None) -> pd.Series | None:
    if not tickers:
        return None
    try:
        kwargs = {"start": start} if start else {"period": period}
        data = yf.download(tickers, interval="1d", group_by="ticker",
                           auto_adjust=False, progress=False, **kwargs)
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
            "Purchased": getattr(s, "purchase_date", None) or "",
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Symbol", "Shares", "Buy Price (€)", "Current Price (€)",
            "Invested (€)", "Current Value (€)", "Gain (€)", "Gain (%)", "Purchased",
        ])
    return pd.DataFrame(rows).sort_values("Current Value (€)", ascending=False).reset_index(drop=True)


# ===== HOLDINGS TABLE HTML =====
def render_holdings_table(df: pd.DataFrame, total_value: float) -> str:
    if df.empty:
        return '<div class="ht-wrap"><p style="color:#9e9e9e;text-align:center;margin:0">No holdings yet.</p></div>'
    rows_html = ""
    for _, row in df.iterrows():
        symbol = row["Symbol"]
        color = get_avatar_color(symbol)
        abbr = get_avatar_text(symbol)
        asset_type = get_asset_type(symbol)

        price = row["Current Price (€)"]
        price_str = f"€{price:,.2f}" if price else "N/A"
        value = row["Current Value (€)"]
        gain_eur = row["Gain (€)"]
        gain_pct = row["Gain (%)"]
        alloc = (value / total_value * 100) if total_value else 0

        gain_cls = "gp" if gain_eur >= 0 else "gn"
        arrow = "↗" if gain_eur >= 0 else "↘"
        purchased = row.get("Purchased", "") or ""
        purchased_str = purchased if purchased else '<span style="color:#ccc">—</span>'

        rows_html += f"""
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:12px">
              <div class="av" style="background:{color}">{abbr}</div>
              <div>
                <p class="an">{symbol}</p>
                <div style="display:flex;align-items:center;gap:6px;margin-top:3px">
                  <span class="as">{symbol}</span>
                  <span class="tag tag-{asset_type}">{asset_type}</span>
                </div>
              </div>
            </div>
          </td>
          <td>{price_str}</td>
          <td>{row['Shares']:,.4f}</td>
          <td style="font-weight:600">€{value:,.2f}</td>
          <td>
            <div class="{gain_cls}">
              {arrow} €{gain_eur:+,.2f}
              <div style="font-size:0.78rem;font-weight:400">{gain_pct:+.2f}%</div>
            </div>
          </td>
          <td>
            <div style="display:flex;align-items:center">
              <div class="ab-bg"><div class="ab-fill" style="width:{min(alloc,100):.1f}%"></div></div>
              <span style="font-size:0.82rem">{alloc:.1f}%</span>
            </div>
          </td>
          <td style="color:#6b7280;font-size:0.82rem">{purchased_str}</td>
        </tr>"""

    return f"""
    <div class="ht-wrap">
      <p class="ht-title">Holdings</p>
      <table class="ht">
        <thead>
          <tr>
            <th>ASSET</th><th>PRICE</th><th>QUANTITY</th>
            <th>VALUE</th><th>GAIN/LOSS</th><th>ALLOCATION</th><th>PURCHASED</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>"""


# ===== LOAD STATE =====
p = init_session_state()


# ===== SIDEBAR NAV =====
with st.sidebar:
    st.markdown("""
    <div style="padding:24px 16px 20px 16px">
      <div style="font-size:1.1rem;font-weight:700;color:white">📈 Portfolio</div>
      <div style="font-size:0.75rem;color:#6b7280;margin-top:2px">Tracker</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", [
        "🗂  Portfolio",
        "➕  Add Asset",
        "📥  Import / Export",
        "📊  Analytics",
    ], key="nav_page", label_visibility="collapsed")

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.divider()
    if st.button("🚪 Logout", width="stretch"):
        st.session_state.authenticated = False
        st.rerun()


# ===========================
# PAGES
# ===========================

# ── PORTFOLIO ──
if page == "🗂  Portfolio":
    df = build_portfolio_table(p)

    if not df.empty:
        total_invested = float(df["Invested (€)"].sum())
        total_value = float(df["Current Value (€)"].sum())
        total_gain = total_value - total_invested
        total_pct = (total_gain / total_invested * 100) if total_invested else 0.0

        # Metric cards
        m1, m2, m3, m4 = st.columns(4)
        gvc = "val-g" if total_gain >= 0 else "val-r"
        gpc = "val-g" if total_pct >= 0 else "val-r"
        with m1:
            st.markdown(f'<div class="mc"><p class="lbl">Total Invested</p><p class="val">€{total_invested:,.2f}</p></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="mc"><p class="lbl">Current Value</p><p class="val">€{total_value:,.2f}</p></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="mc"><p class="lbl">Gain / Loss (€)</p><p class="val {gvc}">€{total_gain:+,.2f}</p></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="mc"><p class="lbl">Gain / Loss (%)</p><p class="val {gpc}">{total_pct:+.2f}%</p></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Two donut charts
        c1, c2 = st.columns(2)
        chart_layout = dict(
            showlegend=True,
            legend=dict(orientation="h", y=-0.18, font=dict(size=11)),
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="white", plot_bgcolor="white",
            font=dict(color="#1a1c2e"), height=300,
        )
        with c1:
            fig1 = px.pie(df, names="Symbol", values="Current Value (€)",
                          hole=0.58, color_discrete_sequence=px.colors.qualitative.Bold)
            fig1.update_traces(textposition="outside", textinfo="percent+label",
                               hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>")
            fig1.update_layout(**chart_layout)
            st.plotly_chart(fig1, width="stretch")

        with c2:
            df["Type"] = df["Symbol"].apply(get_asset_type)
            type_df = df.groupby("Type")["Current Value (€)"].sum().reset_index()
            type_colors = {"crypto": "#f59e0b", "stock": "#22c55e", "etf": "#3b82f6"}
            colors = [type_colors.get(t, "#9e9e9e") for t in type_df["Type"]]
            fig2 = px.pie(type_df, names="Type", values="Current Value (€)",
                          hole=0.58, color_discrete_sequence=colors)
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               hovertemplate="<b>%{label}</b><br>€%{value:,.2f}<br>%{percent}<extra></extra>")
            fig2.update_layout(**chart_layout)
            st.plotly_chart(fig2, width="stretch")

        # Holdings table
        st.markdown(render_holdings_table(df, total_value), unsafe_allow_html=True)

        # Per-row remove buttons
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("🗑️ Remove a holding"):
            for s in list(p.stocks):
                col_sym, col_btn = st.columns([4, 1])
                col_sym.markdown(f"**{s.symbol}** — {float(s.shares):,.4f} shares")
                if col_btn.button("Remove", key=f"rm_{s.symbol}"):
                    p.remove_stock(s.symbol)
                    fetch_last_close.clear()
                    st.rerun()

        # History chart
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        period_col, _ = st.columns([1, 5])
        with period_col:
            period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "Since first purchase"], index=3)
        tickers = df["Symbol"].tolist()
        shares_list = df["Shares"].tolist()

        start_date = None
        if period == "Since first purchase":
            dates = [row for row in df["Purchased"] if row]
            if dates:
                start_date = min(dates)
            else:
                st.caption("No purchase dates recorded — showing 1y instead.")
                period = "1y"

        series = fetch_history_value(tickers, shares_list, period=period, start=start_date)
        if series is None or series.empty:
            st.warning("⚠️ No history data available.")
        else:
            st.line_chart(pd.DataFrame({"Portfolio Value (€)": series}),
                          width="stretch", height=320)
    else:
        st.info("📭 Portfolio is empty. Go to **Add Asset** to get started.")


# ── ADD ASSET ──
elif page == "➕  Add Asset":
    st.markdown("## Add Asset")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Add / Update")
        query = st.text_input("Search symbol or name", placeholder="e.g. VWCE, Apple, Bitcoin...", key="add_sym_query")
        sym = ""
        if query:
            suggestions = search_tickers(query)
            if suggestions:
                options = [f"{s}  —  {n}" for s, n in suggestions]
                chosen = st.selectbox("Select", options, key="add_sym_select")
                sym = chosen.split("  —  ")[0].strip() if chosen else ""
            else:
                sym = query.strip().upper()
                st.caption(f"No suggestions — will use: **{sym}**")
        sh = st.number_input("Shares", min_value=0.0, value=0.0, step=0.01, format="%.6f", key="add_sh")
        buy = st.number_input("Buy price (€)", min_value=0.0, value=0.0, step=0.01, format="%.4f", key="add_buy")
        purchase_dt = st.date_input("Purchase date", value=date.today(), key="add_date")
        if st.button("Add / Update", width="stretch", type="primary"):
            if sym.strip() and sh > 0:
                p.add_stock(sym.strip(), float(sh), float(buy), purchase_date=str(purchase_dt))
                fetch_last_close.clear()
                st.success(f"✅ Added/updated {sym.strip()}")
                st.rerun()
            else:
                st.error("❌ Enter a valid symbol and shares > 0")

    with col2:
        st.subheader("Remove")
        remove_sym = st.text_input("Symbol to remove", key="rm_sym")
        if st.button("Remove", width="stretch"):
            if remove_sym.strip():
                p.remove_stock(remove_sym.strip())
                fetch_last_close.clear()
                st.success(f"✅ Removed {remove_sym.strip()}")
                st.rerun()
            else:
                st.error("❌ Enter a symbol")


# ── IMPORT / EXPORT ──
elif page == "📥  Import / Export":
    st.markdown("## Import / Export")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.expander("📥 Import Portfolio (.json)", expanded=True):
            json_file = st.file_uploader("Upload portfolio.json", type=["json"], key="json_upload")
            overwrite_json = st.checkbox("Overwrite existing portfolio", value=False, key="json_overwrite")
            if json_file and st.button("Import JSON", width="stretch"):
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
                        st.success(f"✅ Imported {len(stocks)} stocks")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")

        with st.expander("📥 Import XTB Cash Operations (.xlsx)"):
            st.caption("Export from XTB: History → Cash Operations → Download XLSX")
            xtb_cash_file = st.file_uploader("Upload XTB Cash Operations XLSX", type=["xlsx"], key="xtb_cash_upload")
            overwrite_xtb = st.checkbox("Overwrite existing portfolio", value=False, key="xtb_cash_overwrite")
            if xtb_cash_file and st.button("Import XTB Cash Operations", width="stretch"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(xtb_cash_file.getbuffer())
                    tmp_path = tmp.name
                try:
                    p.import_xtb_cash_operations_xlsx(tmp_path, XTB_INSTRUMENT_TO_TICKER, overwrite=overwrite_xtb)
                    fetch_last_close.clear()
                    fetch_history_value.clear()
                    st.success("✅ Imported XTB Cash Operations")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        with st.expander("📥 Import XTB Positions (.xlsx)"):
            st.caption("Export from XTB: Portfolio → Open Positions → Download XLSX")
            xtb_file = st.file_uploader("Upload XTB Positions XLSX", type=["xlsx"], key="xtb_upload")
            overwrite_xtb_pos = st.checkbox("Overwrite existing portfolio", value=False, key="xtb_pos_overwrite")
            if xtb_file and st.button("Import XTB Positions", width="stretch"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(xtb_file.getbuffer())
                    tmp_path = tmp.name
                try:
                    p.import_xtb_positions_xlsx(tmp_path, overwrite=overwrite_xtb_pos)
                    fetch_last_close.clear()
                    fetch_history_value.clear()
                    st.success("✅ Imported XTB Positions")
                    st.rerun()
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        with st.expander("📥 Import DEGIRO Transactions (.csv)"):
            degiro_file = st.file_uploader("Upload DEGIRO CSV", type=["csv"], key="degiro_upload")
            st.caption("Unknown ISINs are resolved automatically via Yahoo Finance.")
            overwrite_degiro = st.checkbox("Overwrite existing portfolio", value=False, key="degiro_overwrite")
            if degiro_file and st.button("Import DEGIRO CSV", width="stretch"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(degiro_file.getbuffer())
                    tmp_path = tmp.name
                try:
                    p.import_degiro_transactions_csv(tmp_path, ISIN_TO_TICKER, overwrite=overwrite_degiro)
                    fetch_last_close.clear()
                    fetch_history_value.clear()
                    st.success("✅ Imported DEGIRO CSV")
                    st.rerun()
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        with st.expander("📥 Import Anycoin Crypto (.csv)"):
            anycoin_file = st.file_uploader("Upload Anycoin CSV", type=["csv"], key="anycoin_upload")
            czk_rate = st.number_input("CZK per EUR", min_value=1.0, value=25.0, step=0.5, key="czk_rate")
            overwrite_anycoin = st.checkbox("Overwrite existing portfolio", value=False, key="anycoin_overwrite")
            if anycoin_file and st.button("Import Anycoin CSV", width="stretch"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    tmp.write(anycoin_file.getbuffer())
                    tmp_path = tmp.name
                try:
                    p.import_anycoin_trade_fills_csv(tmp_path, overwrite=overwrite_anycoin, czk_per_eur=czk_rate)
                    fetch_last_close.clear()
                    fetch_history_value.clear()
                    st.success("✅ Imported Anycoin CSV")
                    st.rerun()
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

    with col2:
        st.subheader("💾 Export")
        if p.stocks:
            export_data = json.dumps({"stocks": [s.to_dict() for s in p.stocks]}, indent=4)
            st.download_button(
                label="💾 Download portfolio.json",
                data=export_data,
                file_name="portfolio.json",
                mime="application/json",
                width="stretch",
            )
        else:
            st.info("No stocks to export.")


# ── ANALYTICS ──
elif page == "📊  Analytics":
    st.markdown("## Analytics")
    df = build_portfolio_table(p)

    if df.empty:
        st.info("📭 Portfolio is empty.")
    else:
        total_value = float(df["Current Value (€)"].sum())

        period_col, _ = st.columns([1, 5])
        with period_col:
            period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

        tickers = df["Symbol"].tolist()
        shares_list = df["Shares"].tolist()
        series = fetch_history_value(tickers, shares_list, period=period)
        if series is None or series.empty:
            st.warning("⚠️ No history data available.")
        else:
            st.line_chart(pd.DataFrame({"Portfolio Value (€)": series}),
                          width="stretch", height=350)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        def color_gain(val):
            if pd.isna(val):
                return ""
            if val > 0:
                return "color: #22c55e; font-weight: 600;"
            if val < 0:
                return "color: #ef4444; font-weight: 600;"
            return "color: #9e9e9e;"

        fmt = {
            "Shares": "{:,.6f}",
            "Buy Price (€)": "€{:,.2f}",
            "Current Price (€)": "€{:,.2f}",
            "Invested (€)": "€{:,.2f}",
            "Current Value (€)": "€{:,.2f}",
            "Gain (€)": "€{:+,.2f}",
            "Gain (%)": "{:+,.2f}%",
        }
        styled = (
            df.style
            .format(fmt, na_rep="N/A")
            .applymap(color_gain, subset=["Gain (€)", "Gain (%)"])
        )
        st.dataframe(styled, width="stretch", height=400)
