"""
TradeFusion AI - Live / Latest Bar Analyzer
"""

import pandas as pd
from typing import Dict

from backend.indicators.core import compute_all_indicators
from backend.confidence.engine import ConfidenceEngine
from backend.structure.analyzer import detect_structure
from backend.sentinel.explainer import generate_explanation


class TradeFusionAnalyzer:
    def __init__(self, risk_mode: str = "medium"):
        self.engine = ConfidenceEngine()
        self.risk_mode = risk_mode

    def analyze(self, df: pd.DataFrame, symbol: str = "ASSET") -> Dict:
        df = compute_all_indicators(df)
        df = df.dropna()

        if len(df) < 50:
            return {"error": "Not enough data after indicator calculation"}

        last = df.iloc[-1]
        result = self.engine.evaluate(last, risk_mode=self.risk_mode)
        structure = detect_structure(df)
        explanation = generate_explanation(result, structure, symbol=symbol)

        return {
            "symbol": symbol,
            "timestamp": str(df.index[-1]),
            "price": round(float(last["close"]), 4),
            "signal": result["signal"],
            "confidence": result["confidence"],
            "bullish_score": result["bullish_score"],
            "bearish_score": result["bearish_score"],
            "risk_mode": self.risk_mode,
            "structure": structure,
            "explanation": explanation,
            "raw": result
        }
