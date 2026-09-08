# TradeFusion AI

**AI-assisted multi-indicator trading analysis and signal platform**

TradeFusion AI analyzes financial markets by combining multiple technical indicators, calculating a weighted confidence score, and generating high-quality BUY / SELL / NO TRADE signals. It includes **Sentinel AI** — an explanation engine that tells you *why* a signal was generated.

> This is **not** a magic predictor.  
> It is a systematic analysis system that looks for agreement between indicators + market structure before producing a signal.

---

## Supported Assets
- BTC/USDT
- ETH/USDT
- XAU/USD (Gold)
- EUR/USD
- GBP/USD
- USD/JPY
- (Easily expandable)

---

## Core Philosophy

Instead of relying on a single indicator, TradeFusion looks for **agreement** between multiple indicators and market structure before generating a signal.

A signal is only produced when confidence reaches **≥ 60%**.

---

## Key Components

### 1. Sentinel AI (The Brain)
The central AI assistant that evaluates all inputs and explains the reasoning behind every signal.

### 2. Technical Analysis Engine
Calculates:
- RSI
- MACD
- EMA / SMA (including 200 EMA)
- Bollinger Bands
- Stochastic
- OBV (On-Balance Volume)
- ATR (Average True Range)

### 3. Confidence Engine
Assigns weights to each indicator and produces a confidence score (0–100%).

Example weighting (configurable):
| Indicator       | Weight |
|-----------------|--------|
| MACD            | 20%    |
| EMA Trend       | 20%    |
| RSI             | 15%    |
| OBV             | 15%    |
| Bollinger       | 10%    |
| Stochastic      | 10%    |
| ATR/Volatility  | 10%    |

### 4. Market Structure Layer
Analyzes:
- Support & Resistance
- Higher Highs / Higher Lows
- Lower Highs / Lower Lows
- Breakouts / Breakdowns
- Trend direction

### 5. Risk Modes
- **Low Risk** → Very selective, higher quality signals
- **Medium Risk** → Balanced (default)
- **High Risk** → More signals, lower selectivity

### 6. Signal Tracking & Performance
- Track signals manually or automatically
- Win rate calculation
- Performance by asset, confidence level, and risk mode
- Historical analysis

---

## Project Structure

```
TradeFusion-AI/
├── backend/                 # Core analysis engine
│   ├── indicators/          # Individual indicator calculations
│   ├── confidence/          # Confidence scoring engine
│   ├── structure/           # Market structure analysis
│   ├── sentinel/            # AI explanation engine
│   └── data/                # Market data handling
├── frontend/                # Dashboard (to be built)
├── docs/                    # Documentation
├── tests/
└── README.md
```

---

## Current Status

🚧 **Early Development**

This repository currently contains the project foundation and architecture based on the full TradeFusion AI specification.

---

## Roadmap

- [x] Project architecture & documentation
- [ ] Core indicator engine
- [ ] Confidence scoring system
- [ ] Market structure analysis
- [ ] Sentinel AI explanations
- [ ] 5-minute analysis cycle
- [ ] Signal tracking & win-rate system
- [ ] Dashboard frontend
- [ ] Telegram / WhatsApp notifications
- [ ] Backtesting engine
- [ ] Live data integrations (Binance, Twelve Data, etc.)

---

## Disclaimer

This project is for **educational and research purposes only**.  
Trading involves significant risk of loss. Past performance is not indicative of future results. Always do your own research and never risk money you cannot afford to lose.

---

Built with ❤️ for systematic traders.