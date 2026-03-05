# CLAUDE.md — AI Assistant Guide for Portfolio-tracket

## Project Overview

**Portfolio-tracket** is a Streamlit-based web application for tracking investment portfolios. It supports manual stock entry and multi-broker import (DEGIRO, XTB, Anycoin), displays real-time prices via Yahoo Finance, and visualizes allocation and historical performance.

The repository also contains archival data analysis scripts and Excel datasets related to energy certification work (aFRR, mRRR power allocation) — these are unrelated to the portfolio tracker and should be treated as read-only artifacts.

---

## Repository Structure

```
Portfolio-tracket/
├── app.py                    # Streamlit app — main entry point (466 lines)
├── portfolio.py              # Portfolio class — core business logic (408 lines)
├── stock.py                  # Stock class — individual holding model (61 lines)
├── persistence.py            # SQLite wrapper — NOT currently used (27 lines)
├── requirements.txt          # Python dependencies
├── .streamlit/
│   └── secrets.toml          # App password (gitignored in production)
├── Data/                     # Archival energy certification data (Excel)
├── Delta/                    # Power allocation simulation data
├── Certifikacni_zprava_ceps/ # Certification reports (read-only)
├── Technical reports/        # Technical documentation (read-only)
├── Data generator.py         # Utility: generate Excel date sequences
└── PDF Convertor.py          # Utility: PDF to Word conversion
```

### Core Application Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI, session state, authentication, dashboard layout |
| `portfolio.py` | Portfolio CRUD, import adapters, persistence (JSON), charting |
| `stock.py` | Stock data model, yfinance price fetching, gain/loss calculation |
| `persistence.py` | Unused SQLite class — kept for reference, not wired into app |

---

## Architecture

### Data Flow

```
User Input / CSV/XLSX Import
        ↓
   portfolio.py (Portfolio class)
        ↓
   stock.py (Stock class)
        ↓
   yfinance API (live prices)
        ↓
   JSON file (data/portfolio.json)
        ↓
   app.py (Streamlit UI rendering)
```

### State Management

- Portfolio state is stored in `st.session_state["portfolio"]` as a `Portfolio` instance
- Persistence is JSON-based: saved to/loaded from `data/portfolio.json`
- `persistence.py` (SQLite) exists but is **not integrated** — do not use it without explicit instruction
- Streamlit `@st.cache_data` decorators cache price fetches (TTL: 5 min for current price, 1 hr for history)

### Authentication

- Password-protected via `st.secrets["password"]` from `.streamlit/secrets.toml`
- Session variable `st.session_state["authenticated"]` gates all dashboard content
- The secrets file contains a placeholder; real deployments use Streamlit Cloud secrets management

---

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

The app runs on `http://localhost:8501` by default.

**Authentication:** Set the password in `.streamlit/secrets.toml`:
```toml
password = "your_password_here"
```

---

## Dependencies

```
streamlit       # Web UI framework
pandas          # Data manipulation and CSV/XLSX parsing
yfinance        # Yahoo Finance API for live and historical prices
matplotlib      # Static chart generation
plotly          # Interactive charts (donut chart, historical value)
tabulate        # Table formatting (CLI utilities)
openpyxl        # Excel file reading (XTB import, data utilities)
```

No build step required — pure Python with pip.

---

## Key Classes and Methods

### `Stock` (stock.py)

Represents a single holding.

| Method | Description |
|--------|-------------|
| `__init__(symbol, shares, purchase_price)` | Create stock; auto-fetches current price |
| `get_current_price()` | Fetch latest price via yfinance |
| `get_price_history(period)` | Fetch OHLCV history via yfinance |
| `calculate_value()` | `shares * current_price` |
| `calculate_gain_loss()` | `(current_price - purchase_price) * shares` |
| `to_dict()` | Serialize to JSON-compatible dict |

### `Portfolio` (portfolio.py)

Manages a collection of `Stock` objects.

| Method | Description |
|--------|-------------|
| `add_stock(symbol, shares, purchase_price)` | Add or update a position |
| `remove_stock(symbol)` | Remove a holding |
| `get_portfolio_stats()` | Aggregate value, cost, gain/loss |
| `display_portfolio()` | Print formatted table (CLI) |
| `plot_stock_history(symbol, period)` | Matplotlib line chart |
| `plot_portfolio_value(period)` | Plotly historical value chart |
| `save_portfolio(filepath)` | Serialize to JSON |
| `load_portfolio(filepath)` | Deserialize from JSON |
| `import_from_degiro(csv_path)` | Parse DEGIRO transaction CSV |
| `import_from_xtb(xlsx_path)` | Parse XTB positions XLSX |
| `import_from_anycoin(csv_path)` | Parse Anycoin crypto CSV |

### `PortfolioDatabase` (persistence.py — unused)

SQLite wrapper. Schema:
```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    value REAL NOT NULL
)
```
Not currently used by the app. Do not integrate without explicit instruction.

---

## Hardcoded Configuration

### ISIN to Ticker Mapping (`app.py`)

Used when importing DEGIRO CSV (which uses ISINs instead of tickers):

```python
ISIN_TO_TICKER = {
    "IE00BK5BQT80": "VWCE.DE",   # Vanguard FTSE All-World
    "IE00BKM4GZ66": "EMIM.AS",   # iShares MSCI EM
    "IE00BSPLC298": "ZPRV.DE",   # Invesco Global IG Corporate Bond
    "IE00BG0SKF03": "5MVL.DE",   # Lyxor DJ Global Select Dividend
}
```

To support new instruments, extend this dict.

### Ticker Emoji Map

Maps 20+ ticker symbols to display icons (e.g. `"VWCE.DE": "🌍"`). Extend to add visual branding for new tickers.

---

## Code Conventions

- **Classes:** PascalCase (`Stock`, `Portfolio`)
- **Methods/functions:** snake_case
- **Constants:** UPPERCASE (`ISIN_TO_TICKER`)
- **No private prefixes** — all methods are public
- **Error handling:** try/except blocks with `st.error()` or `st.warning()` messages for user feedback
- **Numeric parsing:** Use `pd.to_numeric(..., errors='coerce')` for European-format numbers (comma decimals)
- **Currency:** EUR assumed throughout; no multi-currency conversion

### UI Conventions

- Dark theme: background `#1e1e2e`, text white
- Gains: green `#00c853`, Losses: red `#ff1744`
- Summary metrics use `st.metric()` with delta
- Holdings displayed in 3-column grid with inline HTML cards
- Emojis used liberally in labels and status messages (✅ ❌ 🟢 🔴 📈 💾 etc.)

---

## Data Formats

### JSON Portfolio File (`data/portfolio.json`)

```json
{
    "stocks": [
        {
            "symbol": "VWCE.DE",
            "shares": 10.5,
            "purchase_price": 85.50
        }
    ]
}
```

### DEGIRO CSV Import

- Has columns: `Datum`, `Tijd`, `Product`, `ISIN`, `Aantal`, `Koers`, `Wisselkoers`, `Totaal`
- ISINs are mapped to tickers via `ISIN_TO_TICKER`
- Aggregates multiple transactions for the same ISIN

### XTB XLSX Import

- Has columns: `Symbol`, `Volume`, `Average open price`
- Direct ticker symbols (no ISIN mapping needed)

### Anycoin CSV Import

- Has columns: `Currency pair`, `Trade size`, `Price`
- Splits currency pair (e.g. `BTC/EUR`) to derive ticker

---

## Testing

There are **no automated tests** in this project. All validation is manual through the Streamlit UI or ad hoc script runs.

When adding features:
- Test imports manually with sample CSV/XLSX files
- Verify price fetching works with valid ticker symbols
- Check that JSON save/load round-trips correctly

---

## Known Issues / Technical Debt

1. **`persistence.py` is unused** — SQLite class was created but never wired in; app uses JSON
2. **No test suite** — no pytest or unittest setup
3. **No CI/CD** — no GitHub Actions or equivalent
4. **Hardcoded ISIN map** — only 4 ISINs mapped; unsupported ISINs are silently skipped
5. **EUR-only** — no multi-currency support; foreign exchange not handled
6. **No logging** — errors surface only via Streamlit UI messages

---

## Git Workflow

- Main development branch: `master`
- Feature work: create descriptive branches off `master`
- Commit messages: imperative mood, concise summary (see existing history for style)
- No enforced PR process or review requirements currently

---

## What NOT to Modify

- `Data/` — archival energy certification datasets, read-only
- `Delta/` — power allocation simulation data, read-only
- `Certifikacni_zprava_ceps/` — certification reports, read-only
- `Technical reports/` — documentation artifacts, read-only
- `Data generator.py`, `PDF Convertor.py` — standalone utility scripts unrelated to the portfolio app
