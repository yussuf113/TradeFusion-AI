# TradeFusion AI

**AI-assisted multi-indicator trading analysis and signal platform**

Multi-indicator confirmation • Weighted confidence • Market structure • Sentinel explanations • Backtesting • Multi-asset scanner • Performance tracking • Telegram alerts • Web dashboard

---

## Features

- **Indicators**: RSI, MACD, EMA 50/200, Bollinger, Stochastic, OBV, ATR
- **Confidence Engine** (Low / Medium / High risk modes)
- **Market Structure** analysis
- **Sentinel AI** explanations
- **Backtester** (single + multi-asset)
- **Scheduled Multi-Asset Scanner** (every 5 minutes by default)
- **Performance Tracker** (track signals → record wins/losses → win rate)
- **Position Sizing**
- **Telegram Notifications**
- **Streamlit Dashboard**

---

## Quick Start

```bash
git clone https://github.com/yussuf113/TradeFusion-AI.git
cd TradeFusion-AI
pip install -r requirements.txt
```

### 1. Web Dashboard (recommended)
```bash
streamlit run dashboard.py
```

### 2. Single asset backtest
```bash
python run_backtest.py --symbol BTC-USD --risk medium
```

### 3. Multi-asset backtest
```bash
python run_multi_backtest.py --symbols BTC-USD ETH-USD GC=F
```

### 4. Live Scanner (runs every 5 min)
```bash
# One scan
python run_scanner.py --once

# Continuous scanning + Telegram alerts
python run_scanner.py --telegram --interval 300
```

### 5. Single snapshot
```bash
python run_analysis.py --symbol ETH-USD
```

---

## Supported Assets (default scanner list)

**Crypto:** BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD  
**Metals:** GC=F (Gold), SI=F (Silver)  
**Forex:** EURUSD=X, GBPUSD=X, USDJPY=X  
**Stocks:** AAPL, TSLA

---

## Telegram Setup

1. Talk to [@BotFather](https://t.me/BotFather) → create bot → copy token
2. Get your Chat ID (e.g. @userinfobot)
3. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```
Or enter them directly in the Dashboard.

---

## Performance Tracker

Signals can be tracked from the Dashboard or automatically by the Scanner.  
Later you mark them as Win/Loss and the system calculates win rate, average PnL, and performance by asset.

Data is stored locally in `data/tracked_signals.json`.

---

## Disclaimer

For **educational and research purposes only**. Trading involves substantial risk of loss. Backtests and past signals do not guarantee future results.

---

Built for systematic traders who want multi-confirmation instead of single-indicator noise.
