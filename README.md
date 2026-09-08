# TradeFusion AI

**AI-assisted multi-indicator trading analysis and signal platform with confidence scoring, market structure, Sentinel explanations, and full backtesting.**

> Not a magic predictor. A systematic engine that looks for agreement between multiple indicators + market structure before producing a signal.

---

## Features

- Multi-indicator engine: RSI, MACD, EMA 50/200, Bollinger Bands, Stochastic, OBV, ATR
- Weighted Confidence Engine with configurable threshold (default 60%)
- Three Risk Modes: Low / Medium / High
- Market Structure analysis (trend, support, resistance)
- **Sentinel AI** — human-readable explanation of every signal
- Full Backtesting engine with win rate, profit factor, drawdown, etc.
- Real data via Yahoo Finance + high-quality synthetic data fallback

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yussuf113/TradeFusion-AI.git
cd TradeFusion-AI

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run a backtest (real data if possible)
python run_backtest.py --symbol BTC-USD --risk medium

# Force synthetic data (no internet needed)
python run_backtest.py --synthetic --symbol BTC-USD

# Single snapshot analysis
python run_analysis.py --symbol ETH-USD --risk low
```

### Useful flags

| Flag | Description | Default |
|------|-------------|--------|
| `--symbol` | Asset (BTC-USD, ETH-USD, GC=F, EURUSD=X...) | BTC-USD |
| `--risk` | low / medium / high | medium |
| `--period` | 3mo, 6mo, 1y... | 6mo |
| `--interval` | 1h, 4h, 1d... | 1h |
| `--synthetic` | Force synthetic data | off |
| `--tp` | Take profit (ATR multiples) | 2.0 |
| `--sl` | Stop loss (ATR multiples) | 1.2 |

---

## Project Structure

```
TradeFusion-AI/
├── backend/
│   ├── indicators/core.py      # All technical indicators
│   ├── confidence/engine.py    # Weighted confidence scoring
│   ├── structure/analyzer.py   # Market structure
│   ├── sentinel/explainer.py   # Human explanations
│   ├── data/fetcher.py         # Real + synthetic data
│   ├── analyzer.py             # Live snapshot analyzer
│   └── backtester.py           # Full backtesting engine
├── run_backtest.py             # Main backtest CLI
├── run_analysis.py             # Single analysis CLI
├── requirements.txt
└── README.md
```

---

## How the Confidence Engine Works

Each indicator votes bullish or bearish with a strength score. Votes are weighted:

| Indicator      | Weight |
|----------------|--------|
| MACD           | 20%    |
| EMA Trend      | 20%    |
| RSI            | 15%    |
| OBV            | 15%    |
| Bollinger      | 10%    |
| Stochastic     | 10%    |
| ATR / Vol      | 10%    |

Only when the winning side reaches the threshold (60% medium, 70% low, 50% high) is a BUY or SELL signal generated. Otherwise → **NO TRADE**.

---

## Example Output

```
=======================================================
 BACKTEST REPORT — BTC-USD
=======================================================
Total Trades     : 47
Wins / Losses    : 29 / 18
Win Rate         : 61.7%
Total PnL        : +34.28%
Average Win      : +2.41%
Average Loss     : -1.38%
Profit Factor    : 2.12
Max Drawdown     : 8.74%
=======================================================
```

---

## Disclaimer

This software is for **educational and research purposes only**.  
Trading involves substantial risk of loss. Past performance (including backtests) is not indicative of future results. Use at your own risk.

---

Built for systematic traders who want multi-confirmation instead of single-indicator noise.
