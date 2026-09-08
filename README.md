# TradeFusion AI

**AI-assisted multi-indicator trading analysis and signal platform**

Multi-indicator confirmation • Weighted confidence scoring • Market structure • Sentinel explanations • Full backtesting • Telegram alerts • Web dashboard

---

## Features

- **Indicators**: RSI, MACD, EMA 50/200, Bollinger Bands, Stochastic, OBV, ATR
- **Confidence Engine** with Low / Medium / High risk modes
- **Market Structure** (trend, support, resistance)
- **Sentinel AI** explanations
- **Backtester** (single + multi-asset)
- **Position Sizing** (risk-based)
- **Telegram Notifications**
- **Streamlit Dashboard** with live charts

---

## Quick Start

```bash
git clone https://github.com/yussuf113/TradeFusion-AI.git
cd TradeFusion-AI
pip install -r requirements.txt
```

### 1. Backtest (single asset)
```bash
python run_backtest.py --symbol BTC-USD --risk medium
python run_backtest.py --synthetic          # offline mode
```

### 2. Multi-asset backtest
```bash
python run_multi_backtest.py --symbols BTC-USD ETH-USD GC=F --risk medium
```

### 3. Web Dashboard
```bash
streamlit run dashboard.py
```

### 4. Single analysis
```bash
python run_analysis.py --symbol ETH-USD --risk low
```

---

## Telegram Setup (Optional)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token
2. Get your Chat ID (e.g. via @userinfobot)
3. Either:
   - Set environment variables:
     ```bash
     export TELEGRAM_BOT_TOKEN="your_token"
     export TELEGRAM_CHAT_ID="your_chat_id"
     ```
   - Or enter them in the Dashboard sidebar

---

## Project Structure

```
TradeFusion-AI/
├── backend/
│   ├── indicators/        # Technical indicators
│   ├── confidence/        # Weighted scoring engine
│   ├── structure/         # Market structure
│   ├── sentinel/          # Explanations
│   ├── data/              # Data fetching
│   ├── notifications/     # Telegram
│   ├── position_sizing.py
│   ├── analyzer.py
│   └── backtester.py
├── run_backtest.py
├── run_multi_backtest.py
├── run_analysis.py
├── dashboard.py           # Streamlit web UI
└── requirements.txt
```

---

## Disclaimer

For **educational and research purposes only**. Trading involves substantial risk of loss. Backtest results do not guarantee future performance.

---

Built for systematic traders who prefer multi-confirmation over single-indicator noise.
