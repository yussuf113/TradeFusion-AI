"""
TradeFusion AI - Market Data Fetcher
Supports:
- Twelve Data (preferred when API key is available)
- yfinance (fallback)
- Synthetic data (offline / testing)
"""

import os
import time
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Optional

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"


def generate_synthetic_data(
    symbol: str = "SYNTH",
    days: int = 180,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0003,
    seed: int = 42
) -> pd.DataFrame:
    """Generate realistic OHLCV data for testing."""
    np.random.seed(seed)
    periods = days * 24  # hourly bars

    returns = np.random.normal(loc=trend, scale=volatility, size=periods)
    price = start_price * np.exp(np.cumsum(returns))

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


def _map_symbol_twelve(symbol: str) -> str:
    """Convert common symbols to Twelve Data format."""
    mapping = {
        "BTC-USD": "BTC/USD",
        "ETH-USD": "ETH/USD",
        "SOL-USD": "SOL/USD",
        "BNB-USD": "BNB/USD",
        "XRP-USD": "XRP/USD",
        "GC=F": "XAU/USD",
        "SI=F": "XAG/USD",
        "EURUSD=X": "EUR/USD",
        "GBPUSD=X": "GBP/USD",
        "USDJPY=X": "USD/JPY",
    }
    return mapping.get(symbol, symbol.replace("-", "/").replace("=X", "").replace("=F", ""))


def fetch_twelve_data(
    symbol: str,
    interval: str = "1h",
    outputsize: int = 500,
    api_key: str = None
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data from Twelve Data."""
    key = api_key or TWELVE_DATA_KEY
    if not key:
        return None

    td_symbol = _map_symbol_twelve(symbol)

    # Twelve Data interval mapping
    interval_map = {
        "1m": "1min", "5m": "5min", "15m": "15min",
        "1h": "1h", "4h": "4h", "1d": "1day"
    }
    td_interval = interval_map.get(interval, interval)

    params = {
        "symbol": td_symbol,
        "interval": td_interval,
        "outputsize": outputsize,
        "apikey": key,
        "format": "JSON",
        "timezone": "UTC"
    }

    try:
        r = requests.get(TWELVE_DATA_URL, params=params, timeout=15)
        data = r.json()

        if "values" not in data:
            msg = data.get("message") or data.get("status") or str(data)[:120]
            print(f"[TwelveData] {td_symbol}: {msg}")
            return None

        df = pd.DataFrame(data["values"])
        df = df.rename(columns={
            "datetime": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume"
        })

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])
        if "volume" not in df.columns or df["volume"].isna().all():
            df["volume"] = 0.0

        print(f"[DATA] Twelve Data → {td_symbol} | {len(df)} bars")
        return df[["open", "high", "low", "close", "volume"]]

    except Exception as e:
        print(f"[TwelveData] Error fetching {symbol}: {e}")
        return None


def fetch_yfinance(symbol: str, period: str = "6mo", interval: str = "1h") -> Optional[pd.DataFrame]:
    """Fallback using yfinance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume"
        })
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df.index.name = "timestamp"
        print(f"[DATA] yfinance → {symbol} | {len(df)} bars")
        return df
    except Exception as e:
        print(f"[yfinance] Failed for {symbol}: {e}")
        return None


def get_data(
    symbol: str = "BTC-USD",
    period: str = "6mo",
    interval: str = "1h",
    use_synthetic: bool = False,
    api_key: str = None
) -> pd.DataFrame:
    """
    Main data entry point.
    Priority:
      1. Twelve Data (if API key available)
      2. yfinance
      3. Synthetic data
    """
    if use_synthetic:
        print(f"[DATA] Using synthetic data for {symbol}")
        return generate_synthetic_data(
            symbol=symbol,
            days=180,
            start_price=60000 if "BTC" in symbol.upper() else 100.0
        )

    # 1. Try Twelve Data first
    key = api_key or TWELVE_DATA_KEY
    if key:
        df = fetch_twelve_data(symbol, interval=interval, api_key=key)
        if df is not None and len(df) > 50:
            return df

    # 2. Fallback to yfinance
    df = fetch_yfinance(symbol, period=period, interval=interval)
    if df is not None and len(df) > 50:
        return df

    # 3. Last resort
    print(f"[DATA] Falling back to synthetic data for {symbol}")
    return generate_synthetic_data(
        symbol=symbol,
        days=180,
        start_price=60000 if "BTC" in symbol.upper() else 100.0
    )
