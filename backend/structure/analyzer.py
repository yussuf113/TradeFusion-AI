"""
TradeFusion AI - Market Structure Analyzer
Basic support/resistance + trend structure
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


def find_swing_points(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    """Identify simple swing highs and lows"""
    df = df.copy()
    df['swing_high'] = False
    df['swing_low'] = False

    for i in range(left, len(df) - right):
        window_high = df['high'].iloc[i-left:i+right+1]
        window_low = df['low'].iloc[i-left:i+right+1]
        if df['high'].iloc[i] == window_high.max():
            df.loc[df.index[i], 'swing_high'] = True
        if df['low'].iloc[i] == window_low.min():
            df.loc[df.index[i], 'swing_low'] = True
    return df


def detect_structure(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    Analyze recent market structure.
    Returns trend bias and nearest support/resistance.
    """
    if len(df) < lookback:
        lookback = len(df)

    recent = df.iloc[-lookback:].copy()
    recent = find_swing_points(recent)

    swing_highs = recent[recent['swing_high']]['high']
    swing_lows = recent[recent['swing_low']]['low']

    # Simple HH/HL vs LH/LL detection
    structure = "ranging"
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        last_two_highs = swing_highs.tail(2).values
        last_two_lows = swing_lows.tail(2).values

        higher_highs = last_two_highs[-1] > last_two_highs[-2]
        higher_lows = last_two_lows[-1] > last_two_lows[-2]
        lower_highs = last_two_highs[-1] < last_two_highs[-2]
        lower_lows = last_two_lows[-1] < last_two_lows[-2]

        if higher_highs and higher_lows:
            structure = "bullish"
        elif lower_highs and lower_lows:
            structure = "bearish"

    # Nearest levels
    current_price = df['close'].iloc[-1]
    resistance = swing_highs[swing_highs > current_price].min() if len(swing_highs[swing_highs > current_price]) > 0 else None
    support = swing_lows[swing_lows < current_price].max() if len(swing_lows[swing_lows < current_price]) > 0 else None

    return {
        "structure": structure,
        "support": round(support, 4) if support else None,
        "resistance": round(resistance, 4) if resistance else None,
        "current_price": round(current_price, 4)
    }
