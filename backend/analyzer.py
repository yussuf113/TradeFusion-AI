"""
TradeFusion AI - Live / Latest Bar Analyzer
Analyzes real market candles and produces:
  - Technical indicators
  - Market structure
  - Weighted confidence evaluation
  - BUY / SELL / NO TRADE signal
  - Analytical trade setup (Entry, SL, TP, R:R, Review Time)
"""

import pandas as pd
from datetime import timedelta
from typing import Dict, Optional

from backend.indicators.core import compute_all_indicators
from backend.confidence.engine import ConfidenceEngine
from backend.structure.analyzer import detect_structure
from backend.sentinel.explainer import generate_explanation


# Timeframe duration mapping for trade review / expiry horizons
_TIMEFRAME_REVIEW_BARS = {
    "1m": 15,    # 15 minutes
    "5m": 12,    # 1 hour
    "15m": 8,    # 2 hours
    "30m": 6,    # 3 hours
    "1h": 4,     # 4 hours
    "4h": 6,     # 24 hours
    "1d": 3,     # 3 days
}

_TIMEFRAME_DELTAS = {
    "1m": timedelta(minutes=15),
    "5m": timedelta(hours=1),
    "15m": timedelta(hours=2),
    "30m": timedelta(hours=3),
    "1h": timedelta(hours=4),
    "4h": timedelta(hours=24),
    "1d": timedelta(days=3),
}


class TradeFusionAnalyzer:
    def __init__(self, risk_mode: str = "medium"):
        self.engine = ConfidenceEngine()
        self.risk_mode = risk_mode

    def analyze(self, df: pd.DataFrame, symbol: str = "ASSET", timeframe: str = "1h") -> Dict:
        """
        Run complete technical analysis on provided real market dataframe.
        Guarantees that empty or invalid data is rejected.
        """
        if df is None or len(df) == 0:
            return {"error": "DATA UNAVAILABLE: No market data provided to analyzer."}

        df_ind = compute_all_indicators(df)
        df_ind = df_ind.dropna()

        if len(df_ind) < 50:
            return {"error": "Not enough valid bars for indicator calculation (minimum 50 required)."}

        last = df_ind.iloc[-1]
        last_ts = df_ind.index[-1]
        result = self.engine.evaluate(last, risk_mode=self.risk_mode)
        structure = detect_structure(df_ind)
        explanation = generate_explanation(result, structure, symbol=symbol)

        entry = round(float(last["close"]), 4)
        atr_val = float(last["atr"]) if "atr" in last and not pd.isna(last["atr"]) else (entry * 0.015)
        
        # Consistent SL/TP calculation (1.2x ATR stop, 2.5x ATR target)
        trade_setup = None
        if result["signal"] in ("BUY", "SELL"):
            if result["signal"] == "BUY":
                stop_loss = round(entry - (1.2 * atr_val), 4)
                take_profit = round(entry + (2.5 * atr_val), 4)
            else:  # SELL
                stop_loss = round(entry + (1.2 * atr_val), 4)
                take_profit = round(entry - (2.5 * atr_val), 4)

            sl_dist = abs(entry - stop_loss)
            tp_dist = abs(take_profit - entry)
            rr_ratio = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 2.08

            delta = _TIMEFRAME_DELTAS.get(timeframe, timedelta(hours=4))
            try:
                review_dt = last_ts + delta
                review_str = review_dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                review_str = f"+{delta} from signal"

            trade_setup = {
                "direction": result["signal"],
                "confidence": result["confidence"],
                "timeframe": timeframe,
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward": f"1:{rr_ratio}",
                "signal_time": str(last_ts),
                "review_time": review_str,
                "review_horizon": f"{delta}",
                "atr": round(atr_val, 4),
                "risk_mode": self.risk_mode,
                "execution_type": "SIMULATED"
            }

        return {
            "symbol": symbol,
            "timestamp": str(last_ts),
            "price": entry,
            "signal": result["signal"],
            "confidence": result["confidence"],
            "bullish_score": result["bullish_score"],
            "bearish_score": result["bearish_score"],
            "risk_mode": self.risk_mode,
            "structure": structure,
            "explanation": explanation,
            "trade_setup": trade_setup,
            "timeframe": timeframe,
            "raw": result
        }
