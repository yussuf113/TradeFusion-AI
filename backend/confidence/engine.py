"""
TradeFusion AI - Confidence Engine (tightened for quality over quantity)
"""

from typing import Dict, Tuple
import pandas as pd

DEFAULT_WEIGHTS = {
    "macd": 0.20,
    "ema_trend": 0.22,
    "rsi": 0.14,
    "obv": 0.14,
    "bollinger": 0.10,
    "stochastic": 0.10,
    "atr_vol": 0.10,
}


class ConfidenceEngine:
    def __init__(self, weights: Dict[str, float] = None, threshold: float = 68.0):
        # Raised default threshold from 60 → 68 for fewer, higher-quality signals
        self.weights = weights or DEFAULT_WEIGHTS
        self.threshold = threshold

    def _score_rsi(self, rsi_val: float) -> Tuple[float, float]:
        if pd.isna(rsi_val):
            return 0.5, 0.5
        if rsi_val < 28:
            return 0.90, 0.10
        elif rsi_val < 40:
            return 0.72, 0.28
        elif rsi_val > 72:
            return 0.10, 0.90
        elif rsi_val > 60:
            return 0.28, 0.72
        return 0.50, 0.50

    def _score_macd(self, macd: float, signal: float, hist: float) -> Tuple[float, float]:
        if pd.isna(macd) or pd.isna(signal):
            return 0.5, 0.5
        if macd > signal and hist > 0:
            strength = min(abs(hist) * 40, 1.0)
            return 0.65 + 0.30 * strength, 0.35 - 0.30 * strength
        elif macd < signal and hist < 0:
            strength = min(abs(hist) * 40, 1.0)
            return 0.35 - 0.30 * strength, 0.65 + 0.30 * strength
        return 0.5, 0.5

    def _score_ema_trend(self, close: float, ema50: float, ema200: float) -> Tuple[float, float]:
        if pd.isna(ema50) or pd.isna(ema200):
            return 0.5, 0.5
        # Require clearer trend alignment
        if close > ema50 > ema200:
            return 0.90, 0.10
        elif close > ema50 and ema50 > ema200 * 0.998:
            return 0.70, 0.30
        elif close < ema50 < ema200:
            return 0.10, 0.90
        elif close < ema50 and ema50 < ema200 * 1.002:
            return 0.30, 0.70
        return 0.48, 0.52

    def _score_bollinger(self, close: float, lower: float, upper: float, position: float) -> Tuple[float, float]:
        if pd.isna(position):
            return 0.5, 0.5
        if position < 0.12:
            return 0.80, 0.20
        elif position > 0.88:
            return 0.20, 0.80
        return 0.5, 0.5

    def _score_stochastic(self, k: float, d: float) -> Tuple[float, float]:
        if pd.isna(k) or pd.isna(d):
            return 0.5, 0.5
        if k < 18 and k > d:
            return 0.85, 0.15
        elif k < 22:
            return 0.72, 0.28
        elif k > 82 and k < d:
            return 0.15, 0.85
        elif k > 78:
            return 0.28, 0.72
        return 0.5, 0.5

    def _score_obv(self, obv: float, obv_ema: float) -> Tuple[float, float]:
        if pd.isna(obv) or pd.isna(obv_ema):
            return 0.5, 0.5
        if obv > obv_ema:
            return 0.72, 0.28
        return 0.28, 0.72

    def _score_atr(self, atr_val: float, close: float) -> Tuple[float, float]:
        if pd.isna(atr_val) or close == 0:
            return 0.5, 0.5
        atr_pct = (atr_val / close) * 100
        if 0.4 < atr_pct < 2.8:
            return 0.62, 0.38
        if atr_pct >= 4.5:
            return 0.35, 0.35  # extreme vol → neutral / reduce
        return 0.50, 0.50

    def evaluate(self, row: pd.Series, risk_mode: str = "medium") -> Dict:
        scores = {
            "rsi": self._score_rsi(row.get("rsi")),
            "macd": self._score_macd(row.get("macd"), row.get("macd_signal"), row.get("macd_hist")),
            "ema_trend": self._score_ema_trend(row.get("close"), row.get("ema_50"), row.get("ema_200")),
            "bollinger": self._score_bollinger(row.get("close"), row.get("bb_lower"), row.get("bb_upper"), row.get("bb_position")),
            "stochastic": self._score_stochastic(row.get("stoch_k"), row.get("stoch_d")),
            "obv": self._score_obv(row.get("obv"), row.get("obv_ema")),
            "atr_vol": self._score_atr(row.get("atr"), row.get("close")),
        }

        bullish = bearish = 0.0
        for key, weight in self.weights.items():
            b, s = scores[key]
            bullish += b * weight
            bearish += s * weight

        total = bullish + bearish
        bullish_pct = (bullish / total) * 100 if total > 0 else 50.0
        bearish_pct = (bearish / total) * 100 if total > 0 else 50.0

        # Risk modes — tightened
        if risk_mode == "low":
            effective_threshold = self.threshold + 8   # ~76%
        elif risk_mode == "high":
            effective_threshold = max(60.0, self.threshold - 6)  # ~62%
        else:
            effective_threshold = self.threshold  # 68%

        # Require clear winner (margin)
        margin = 8.0 if risk_mode == "low" else 5.0

        if bullish_pct >= effective_threshold and (bullish_pct - bearish_pct) >= margin:
            signal = "BUY"
            confidence = bullish_pct
        elif bearish_pct >= effective_threshold and (bearish_pct - bullish_pct) >= margin:
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
            "breakdown": {k: {"bull": round(v[0]*100, 1), "bear": round(v[1]*100, 1)} for k, v in scores.items()},
        }
