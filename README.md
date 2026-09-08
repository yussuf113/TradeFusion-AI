# TradeFusion AI

**AI-assisted multi-indicator trading analysis and signal platform**

Multi-indicator confirmation • Weighted confidence • Market structure • Sentinel explanations • Backtesting • Multi-asset scanner • Performance tracking • Telegram alerts • Web dashboard • **Twelve Data support**

---

## Features

- **Indicators**: RSI, MACD, EMA 50/200, Bollinger, Stochastic, OBV, ATR
- **Confidence Engine** (Low / Medium / High risk modes)
- **Market Structure** analysis
- **Sentinel AI** explanations
- **Backtester** (single + multi-asset)
- **Scheduled Multi-Asset Scanner**
- **Performance Tracker**
- **Position Sizing**
- **Telegram Notifications**
- **Streamlit Dashboard**
- **Twelve Data API** (preferred data source) + yfinance fallback

---

## Quick Start

```bash
git clone https://github.com/yussuf113/TradeFusion-AI.git
cd TradeFusion-AI
pip install -r requirements.txt
```

### Set your Twelve Data API key

```bash
# Linux / macOS
export TWELVE_DATA_API_KEY="your_key_here"

# Windows (PowerShell)
$env:TWELVE_DATA_API_KEY="your_key_here"
```

Or create a `.env` file (see `.env.example`).

### Run

```bash
# Web Dashboard (best experience)
streamlit run dashboard.py

# Single backtest
python run_backtest.py --symbol BTC-USD --risk medium

# Multi-asset backtest
python run_multi_backtest.py

# Live scanner (every 5 min)
python run_scanner.py --telegram

# One-shot analysis
python run_analysis.py --symbol ETH-USD
```

---

## Data Sources (priority order)

1. **Twelve Data** (if `TWELVE_DATA_API_KEY` is set) — best quality
2. **Yahoo Finance** (`yfinance`) — free fallback
3. **Synthetic data** — offline testing

---

## Supported Assets

**Crypto:** BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD  
**Metals:** GC=F (Gold), SI=F (Silver)  
**Forex:** EURUSD=X, GBPUSD=X, USDJPY=X  
**Stocks:** AAPL, TSLA

---

## Telegram Setup (Optional)

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

---

## Disclaimer

For **educational and research purposes only**. Trading involves substantial risk of loss. Past performance is not indicative of future results.

---

Built for systematic traders who want multi-confirmation instead of single-indicator noise.
