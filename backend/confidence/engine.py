"""
TradeFusion AI - Confidence Engine
Weighted multi-indicator scoring with risk modes
"""

from typing import Dict, Tuple
import pandas as pd


# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "macd": 0.20,
    "ema_trend": 0.20,
    "rsi": 0.15,
    "obv": 0.15,
    "bollinger": 0.10,
    "stochastic": 0.10,
    "atr_vol": 0.10,
}


class ConfidenceEngine:
    def __init__(self, weights: Dict[str, float] = None, threshold: float = 60.0):
        self.weights = weights or DEFAULT_WEIGHTS
        self.threshold = threshold

    def _score_rsi(self, rsi_val: float) -> Tuple[float, float]:
        """Returns (bullish_score, bearish_score) 0-1"""
        if pd.isna(rsi_val):
            return 0.5, 0.5
        if rsi_val < 30:
            return 0.85, 0.15          # Oversold → bullish
        elif rsi_val < 45:
            return 0.65, 0.35
        elif rsi_val > 70:
            return 0.15, 0.85          # Overbought → bearish
        elif rsi_val > 55:
            return 0.35, 0.65
        return 0.50, 0.50

    def _score_macd(self, macd: float, signal: float, hist: float) -> Tuple[float, float]:
        if pd.isna(macd) or pd.isna(signal):
            return 0.5, 0.5
        if macd > signal and hist > 0:
            strength = min(abs(hist) * 50, 1.0)
            return 0.6 + 0.3 * strength, 0.4 - 0.3 * strength
        elif macd < signal and hist < 0:
            strength = min(abs(hist) * 50, 1.0)
            return 0.4 - 0.3 * strength, 0.6 + 0.3 * strength
        return 0.5, 0.5

    def _score_ema_trend(self, close: float, ema50: float, ema200: float) -> Tuple[float, float]:
        if pd.isna(ema50) or pd.isna(ema200):
            return 0.5, 0.5
        if close > ema50 > ema200:
            return 0.85, 0.15          # Strong bullish alignment
        elif close > ema50:
            return 0.65, 0.35
        elif close < ema50 < ema200:
            return 0.15, 0.85          # Strong bearish
        elif close < ema50:
            return 0.35, 0.65
        return 0.5, 0.5

    def _score_bollinger(self, close: float, lower: float, upper: float, position: float) -> Tuple[float, float]:
        if pd.isna(position):
            return 0.5, 0.5
        if position < 0.15:            # Near lower band
            return 0.75, 0.25
        elif position > 0.85:          # Near upper band
            return 0.25, 0.75
        return 0.5, 0.5

    def _score_stochastic(self, k: float, d: float) -> Tuple[float, float]:
        if pd.isna(k) or pd.isna(d):
            return 0.5, 0.5
        if k < 20 and k > d:
            return 0.80, 0.20          # Oversold + turning up
        elif k < 25:
            return 0.70, 0.30
        elif k > 80 and k < d:
            return 0.20, 0.80
        elif k > 75:
            return 0.30, 0.70
        return 0.5, 0.5

    def _score_obv(self, obv: float, obv_ema: float) -> Tuple[float, float]:
        if pd.isna(obv) or pd.isna(obv_ema):
            return 0.5, 0.5
        if obv > obv_ema:
            return 0.70, 0.30
        else:
            return 0.30, 0.70

    def _score_atr(self, atr_val: float, close: float) -> Tuple[float, float]:
        """ATR mainly acts as a filter (volatility regime)"""
        if pd.isna(atr_val) or close == 0:
            return 0.5, 0.5
        atr_pct = (atr_val / close) * 100
        # Prefer moderate volatility
        if 0.5 < atr_pct < 3.0:
            return 0.60, 0.40
        elif atr_pct >= 5.0:           # Extremely volatile → reduce confidence
            return 0.40, 0.40
        return 0.50, 0.50

    def evaluate(self, row: pd.Series, risk_mode: str = "medium") -> Dict:
        """
        Evaluate a single bar and return full confidence breakdown.
        """
        scores = {}

        scores["rsi"] = self._score_rsi(row.get("rsi"))
        scores["macd"] = self._score_macd(row.get("macd"), row.get("macd_signal"), row.get("macd_hist"))
        scores["ema_trend"] = self._score_ema_trend(row.get("close"), row.get("ema_50"), row.get("ema_200"))
        scores["bollinger"] = self._score_bollinger(
            row.get("close"), row.get("bb_lower"), row.get("bb_upper"), row.get("bb_position")
        )
        scores["stochastic"] = self._score_stochastic(row.get("stoch_k"), row.get("stoch_d"))
        scores["obv"] = self._score_obv(row.get("obv"), row.get("obv_ema"))
        scores["atr_vol"] = self._score_atr(row.get("atr"), row.get("close"))

        bullish = 0.0
        bearish = 0.0

        for key, weight in self.weights.items():
            b, s = scores[key]
            bullish += b * weight
            bearish += s * weight

        # Normalize to 0-100
        total = bullish + bearish
        if total > 0:
            bullish_pct = (bullish / total) * 100
            bearish_pct = (bearish / total) * 100
        else:
            bullish_pct = bearish_pct = 50.0

        # Risk mode adjustments
        if risk_mode == "low":
            effective_threshold = self.threshold + 10   # 70%
        elif risk_mode == "high":
            effective_threshold = self.threshold - 10   # 50%
        else:
            effective_threshold = self.threshold        # 60%

        if bullish_pct >= effective_threshold and bullish_pct > bearish_pct:
            signal = "BUY"
            confidence = bullish_pct
        elif bearish_pct >= effective_threshold and bearish_pct > bullish_pct:
            signal = "SELL"
            confidence = bearish_pct
        else:
            signal = "NO TRADE"
            confidence = max(bullish_pct, bearish_pct)

        return {
            "signal": signal,
            "confidence": round(confidence, 1),
            "bullish_score": round(bullish_pct, 1),
            "bearish_score": round(bearish_pct, 1),
            "threshold_used": effective_threshold,
            "risk_mode": risk_mode,
            "breakdown": {k: {"bull": round(v[0]*100, 1), "bear": round(v[1]*100, 1)} for k, v in scores.items()}
        }
