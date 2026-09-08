"""
TradeFusion AI - Market Data Fetcher
Supports yfinance (stocks, forex, gold, crypto) + synthetic data for testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


def generate_synthetic_data(
    symbol: str = "SYNTH",
    days: int = 365,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0003,
    seed: int = 42
) -> pd.DataFrame:
    """Generate realistic OHLCV data for backtesting when no internet / API is available."""
    np.random.seed(seed)
    periods = days * 24 * 12          # 5-minute bars approximation simplified to hourly for speed
    periods = days * 24              # hourly bars

    returns = np.random.normal(loc=trend, scale=volatility, size=periods)
    price = start_price * np.exp(np.cumsum(returns))

    # Create OHLC from close
    noise = np.random.uniform(0.001, 0.008, size=periods)
    high = price * (1 + noise)
    low = price * (1 - noise)
    open_ = np.roll(price, 1)
    open_[0] = start_price
    volume = np.random.randint(100, 10000, size=periods).astype(float)

    idx = pd.date_range(end=datetime.utcnow(), periods=periods, freq="1h")
    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": price,
        "volume": volume
    }, index=idx)

    df.index.name = "timestamp"
    return df


def fetch_yfinance(symbol: str, period: str = "1y", interval: str = "1h") -> Optional[pd.DataFrame]:
    """Fetch real data using yfinance. Returns None on failure."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df.index.name = "timestamp"
        return df
    except Exception as e:
        print(f"[WARN] yfinance fetch failed for {symbol}: {e}")
        return None


def get_data(symbol: str = "BTC-USD", period: str = "6mo", interval: str = "1h", use_synthetic: bool = False) -> pd.DataFrame:
    """
    Main entry point for data.
    Tries real data first, falls back to synthetic if requested or on failure.
    """
    if not use_synthetic:
        df = fetch_yfinance(symbol, period=period, interval=interval)
        if df is not None and len(df) > 100:
            print(f"[DATA] Loaded {len(df)} bars of real data for {symbol}")
            return df

    print(f"[DATA] Using synthetic data for {symbol}")
    return generate_synthetic_data(symbol=symbol, days=180, start_price=60000 if "BTC" in symbol.upper() else 100.0)
