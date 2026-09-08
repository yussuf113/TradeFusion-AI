# TradeFusion AI - System Architecture

## High-Level Flow

```
MARKET DATA
    ↓
DATA PROCESSOR
    ↓
INDICATOR ENGINE (RSI, MACD, EMA, BB, Stochastic, OBV, ATR)
    ↓
MARKET STRUCTURE ANALYSIS
    ↓
CONFIDENCE ENGINE (Weighted scoring)
    ↓
Confidence ≥ 60% ?
   /          \
 YES           NO
  ↓             ↓
BUY/SELL     NO TRADE
  ↓
SENTINEL AI (Explanation)
  ↓
Dashboard + Notifications + Signal Tracking
```

## Design Principles

1. **Multi-confirmation** over single indicators
2. **Confidence threshold** (minimum 60%) to reduce noise
3. **Explainability** via Sentinel AI
4. **Risk modes** for different user preferences
5. **Performance tracking** so the system can be measured and improved
6. **Separation** between analysis engine and execution layer
