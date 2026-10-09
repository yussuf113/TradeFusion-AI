"""
TradeFusion AI - Market Data Fetcher
Priority:
  1. Twelve Data
  2. Finnhub
  3. yfinance
  4. DATA UNAVAILABLE (returns None - never falls back to synthetic)

IMPORTANT: This module does NOT generate synthetic/fake data.
If all providers fail, get_data() returns None.
The caller is responsible for handling the unavailable state.
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"
FINNHUB_URL = "https://finnhub.io/api/v1"

# --------------------------------------------------
# Symbol mapping helpers
# --------------------------------------------------

def _map_symbol_twelve(symbol: str) -> str:
    mapping = {
        "BTC-USD": "BTC/USD", "ETH-USD": "ETH/USD", "SOL-USD": "SOL/USD",
        "BNB-USD": "BNB/USD", "XRP-USD": "XRP/USD",
        "GC=F": "XAU/USD", "SI=F": "XAG/USD",
        "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    }
    return mapping.get(symbol, symbol.replace("-", "/").replace("=X", "").replace("=F", ""))


def _map_symbol_finnhub(symbol: str) -> str:
    mapping = {
        "BTC-USD": "BINANCE:BTCUSDT", "ETH-USD": "BINANCE:ETHUSDT",
        "SOL-USD": "BINANCE:SOLUSDT", "BNB-USD": "BINANCE:BNBUSDT",
        "XRP-USD": "BINANCE:XRPUSDT",
        "GC=F": "FOREX:XAUUSD", "SI=F": "FOREX:XAGUSD",
        "EURUSD=X": "OANDA:EUR_USD", "GBPUSD=X": "OANDA:GBP_USD",
        "USDJPY=X": "OANDA:USD_JPY",
    }
    return mapping.get(symbol, symbol)


# --------------------------------------------------
# Interval/resolution translation helpers
# --------------------------------------------------

_TWELVE_INTERVAL_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min",
    "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1day",
}

_FINNHUB_RESOLUTION_MAP = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "4h": "60",   # Finnhub does not support 4h natively; use 60
    "1d": "D",
}

VALID_FINNHUB_RESOLUTIONS = {"1", "5", "15", "30", "60", "D", "W", "M"}


# --------------------------------------------------
# Provider 1: Twelve Data
# --------------------------------------------------

def fetch_twelve_data(
    symbol: str,
    interval: str = "1h",
    outputsize: int = 500,
    api_key: str = None,
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data from Twelve Data. Returns None on any failure."""
    key = api_key or TWELVE_DATA_KEY
    if not key:
        return None

    td_symbol = _map_symbol_twelve(symbol)
    td_interval = _TWELVE_INTERVAL_MAP.get(interval, interval)

    params = {
        "symbol": td_symbol,
        "interval": td_interval,
        "outputsize": outputsize,
        "apikey": key,
        "format": "JSON",
        "timezone": "UTC",
    }
    try:
        r = requests.get(TWELVE_DATA_URL, params=params, timeout=15)
        data = r.json()
        if "values" not in data:
            print(f"[TwelveData] {td_symbol}: {data.get('message') or data.get('status')}")
            return None

        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp").sort_index()

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])
        if "volume" not in df.columns:
            df["volume"] = 0.0

        if df.empty:
            print(f"[TwelveData] {td_symbol}: empty after cleaning")
            return None

        print(f"[DATA] REAL -- Twelve Data -> {td_symbol} | {len(df)} bars | latest: {df.index[-1]}")
        df.attrs["data_source"] = "Twelve Data"
        df.attrs["latest_candle"] = df.index[-1]
        return df[["open", "high", "low", "close", "volume"]]

    except Exception as e:
        print(f"[TwelveData] Error: {e}")
        return None


# --------------------------------------------------
# Provider 2: Finnhub
# --------------------------------------------------

def fetch_finnhub(
    symbol: str,
    resolution: str = "60",
    days: int = 180,
    api_key: str = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from Finnhub.

    Parameters
    ----------
    symbol     : asset symbol (will be mapped to Finnhub format internally)
    resolution : Finnhub resolution string: '1', '5', '15', '30', '60', 'D'
                 NOT the application interval string (e.g. '1h').
                 Translate before calling: _FINNHUB_RESOLUTION_MAP[interval]
    days       : how many days of history to request
    api_key    : override key (uses FINNHUB_API_KEY env var by default)

    Returns None on any failure.
    """
    key = api_key or FINNHUB_KEY
    if not key:
        return None

    fh_symbol = _map_symbol_finnhub(symbol)
    end = int(datetime.utcnow().timestamp())
    start = int((datetime.utcnow() - timedelta(days=days)).timestamp())

    # Normalise resolution to a valid Finnhub value
    res = resolution if resolution in VALID_FINNHUB_RESOLUTIONS else "60"

    params = {
        "symbol": fh_symbol,
        "resolution": res,
        "from": start,
        "to": end,
        "token": key,
    }

    try:
        # Try stock candle endpoint first
        r = requests.get(f"{FINNHUB_URL}/stock/candle", params=params, timeout=15)
        data = r.json()

        if data.get("s") != "ok" or "c" not in data:
            # Fall back to crypto candle endpoint
            r = requests.get(f"{FINNHUB_URL}/crypto/candle", params=params, timeout=15)
            data = r.json()
            if data.get("s") != "ok" or "c" not in data:
                print(f"[Finnhub] {fh_symbol}: {data.get('s') or data}")
                return None

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(data["t"], unit="s", utc=True),
            "open":      data["o"],
            "high":      data["h"],
            "low":       data["l"],
            "close":     data["c"],
            "volume":    data["v"],
        })
        df = df.set_index("timestamp").sort_index()
        df = df.dropna(subset=["open", "high", "low", "close"])

        if df.empty:
            print(f"[Finnhub] {fh_symbol}: empty after cleaning")
            return None

        print(f"[DATA] REAL -- Finnhub -> {fh_symbol} | {len(df)} bars | latest: {df.index[-1]}")
        df.attrs["data_source"] = "Finnhub"
        df.attrs["latest_candle"] = df.index[-1]
        return df

    except Exception as e:
        print(f"[Finnhub] Error: {e}")
        return None


# --------------------------------------------------
# Provider 3: yfinance
# --------------------------------------------------

# yfinance does not support 4h; map to closest supported interval
_YFINANCE_INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "1h", "1d": "1d",
}

def fetch_yfinance(
    symbol: str,
    period: str = "6mo",
    interval: str = "1h",
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data from yfinance. Returns None on any failure."""
    try:
        import yfinance as yf
        yf_interval = _YFINANCE_INTERVAL_MAP.get(interval, interval)
        df = yf.Ticker(symbol).history(period=period, interval=yf_interval)
        if df is None or df.empty:
            print(f"[yfinance] {symbol}: empty response")
            return None

        df = df.rename(columns={"Open": "open", "High": "high",
                                 "Low": "low", "Close": "close", "Volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df.index.name = "timestamp"

        # Ensure tz-aware index
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        if df.empty:
            return None

        print(f"[DATA] REAL -- yfinance -> {symbol} | {len(df)} bars | latest: {df.index[-1]}")
        df.attrs["data_source"] = "yfinance"
        df.attrs["latest_candle"] = df.index[-1]
        return df

    except Exception as e:
        print(f"[yfinance] Failed: {e}")
        return None


# --------------------------------------------------
# Unified entry point
# --------------------------------------------------

def get_data(
    symbol: str = "BTC-USD",
    period: str = "6mo",
    interval: str = "1h",
    api_key: str = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch real OHLCV market data.

    Provider priority:
        1. Twelve Data
        2. Finnhub
        3. yfinance
        4. Returns None (DATA UNAVAILABLE - never synthetic)

    Parameters
    ----------
    symbol   : asset symbol as used in the application (e.g. 'BTC-USD')
    period   : yfinance-style lookback period ('3mo', '6mo', '1y')
    interval : candle interval ('1m', '5m', '15m', '1h', '4h', '1d')
    api_key  : optional override for API key (used for Twelve Data)

    Returns
    -------
    pd.DataFrame with columns [open, high, low, close, volume] and a
    DatetimeIndex, or None if no real data could be obtained.
    The returned DataFrame carries:
        df.attrs['data_source']   - 'Twelve Data' | 'Finnhub' | 'yfinance'
        df.attrs['latest_candle'] - timestamp of the most recent bar
    """
    MIN_BARS = 50  # minimum bars required for indicator calculation

    # 1. Twelve Data
    df = fetch_twelve_data(symbol, interval=interval, api_key=api_key or TWELVE_DATA_KEY)
    if df is not None and len(df) >= MIN_BARS:
        return df

    # 2. Finnhub - translate interval to resolution before calling
    fh_resolution = _FINNHUB_RESOLUTION_MAP.get(interval, "60")
    df = fetch_finnhub(symbol, resolution=fh_resolution, api_key=api_key or FINNHUB_KEY)
    if df is not None and len(df) >= MIN_BARS:
        return df

    # 3. yfinance
    df = fetch_yfinance(symbol, period=period, interval=interval)
    if df is not None and len(df) >= MIN_BARS:
        return df

    # 4. All providers failed - DATA UNAVAILABLE
    print(f"[DATA] [!] DATA UNAVAILABLE -- all providers failed for {symbol} ({interval}). "
          f"No synthetic fallback. Returning None.")
    return None