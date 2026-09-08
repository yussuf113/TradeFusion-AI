# TradeFusion AI

AI-assisted multi-indicator trading analysis platform with confidence scoring, backtesting, scanner, Telegram alerts, and optional Supabase storage.

## Features

- Multi-indicator engine (RSI, MACD, EMA, Bollinger, Stochastic, OBV, ATR)
- Weighted confidence + Low/Medium/High risk modes
- Market structure analysis + Sentinel explanations
- Backtester (single + multi-asset)
- Scheduled multi-asset scanner
- Performance tracker (local or Supabase)
- Telegram notifications
- Streamlit dashboard
- Data sources: **Twelve Data → Finnhub → yfinance → Synthetic**

## Setup

```bash
git clone https://github.com/yussuf113/TradeFusion-AI.git
cd TradeFusion-AI
pip install -r requirements.txt
```

### Configure API keys

Create a `.env` file in the project root:

```env
TWELVE_DATA_API_KEY=your_key
FINNHUB_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

Or export them in your shell.

Load `.env` automatically by adding this at the top of scripts (already supported if you use `python-dotenv`), or run:

```bash
export $(cat .env | xargs)
```

### Supabase table (optional)

If you want cloud storage, create a table named `tracked_signals` in Supabase with columns:

- id (int8, primary key, auto)
- timestamp (text/timestamptz)
- symbol (text)
- signal (text)
- confidence (float8)
- price (float8)
- risk_mode (text)
- structure (text)
- status (text)
- exit_price (float8)
- pnl_pct (float8)
- closed_at (text/timestamptz)
- notes (text)

## Run

```bash
# Dashboard
streamlit run dashboard.py

# Backtest
python run_backtest.py --symbol BTC-USD --risk medium

# Multi-asset backtest
python run_multi_backtest.py

# Scanner every 5 minutes + Telegram
python run_scanner.py --telegram

# One scan
python run_scanner.py --once
```

## Disclaimer

Educational / research use only. Trading involves risk of loss.
