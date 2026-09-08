"""
TradeFusion AI - Market Data Fetcher
Priority:
  1. Twelve Data
  2. Finnhub
  3. yfinance
  4. Synthetic
"""

import os
import time
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Optional

TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"
FINNHUB_URL = "https://finnhub.io/api/v1"


def generate_synthetic_data(
    symbol: str = "SYNTH",
    days: int = 180,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0003,
    seed: int = 42
) -> pd.DataFrame:
    np.random.seed(seed)
    periods = days * 24
    returns = np.random.normal(loc=trend, scale=volatility, size=periods)
    price = start_price * np.exp(np.cumsum(returns))
    noise = np.random.uniform(0.001, 0.008, size=periods)
    high = price * (1 + noise)
    low = price * (1 - noise)
    open_ = np.roll(price, 1)
    open_[0] = start_price
    volume = np.random.randint(100, 10000, size=periods).astype(float)
    idx = pd.date_range(end=datetime.utcnow(), periods=periods, freq="1h")
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": price, "volume": volume}, index=idx)
    df.index.name = "timestamp"
    return df


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


def fetch_twelve_data(symbol: str, interval: str = "1h", outputsize: int = 500, api_key: str = None) -> Optional[pd.DataFrame]:
    key = api_key or TWELVE_DATA_KEY
    if not key:
        return None
    td_symbol = _map_symbol_twelve(symbol)
    interval_map = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1day"}
    td_interval = interval_map.get(interval, interval)
    params = {"symbol": td_symbol, "interval": td_interval, "outputsize": outputsize, "apikey": key, "format": "JSON", "timezone": "UTC"}
    try:
        r = requests.get(TWELVE_DATA_URL, params=params, timeout=15)
        data = r.json()
        if "values" not in data:
            print(f"[TwelveData] {td_symbol}: {data.get('message') or data.get('status')}")
            return None
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        if "volume" not in df.columns:
            df["volume"] = 0.0
        print(f"[DATA] Twelve Data → {td_symbol} | {len(df)} bars")
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"[TwelveData] Error: {e}")
        return None


def fetch_finnhub(symbol: str, resolution: str = "60", days: int = 180, api_key: str = None) -> Optional[pd.DataFrame]:
    key = api_key or FINNHUB_KEY
    if not key:
        return None
    fh_symbol = _map_symbol_finnhub(symbol)
    end = int(datetime.utcnow().timestamp())
    start = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    # resolution: 1, 5, 15, 30, 60, D, W, M
    res_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
    res = res_map.get(resolution, resolution if resolution in ["1", "5", "15", "30", "60", "D"] else "60")
    url = f"{FINNHUB_URL}/stock/candle"
    params = {"symbol": fh_symbol, "resolution": res, "from": start, "to": end, "token": key}
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get("s") != "ok" or "c" not in data:
            # Try crypto candle endpoint as fallback
            url = f"{FINNHUB_URL}/crypto/candle"
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            if data.get("s") != "ok" or "c" not in data:
                print(f"[Finnhub] {fh_symbol}: {data.get('s') or data}")
                return None
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(data["t"], unit="s"),
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data["v"],
        })
        df = df.set_index("timestamp").sort_index()
        print(f"[DATA] Finnhub → {fh_symbol} | {len(df)} bars")
        return df
    except Exception as e:
        print(f"[Finnhub] Error: {e}")
        return None


def fetch_yfinance(symbol: str, period: str = "6mo", interval: str = "1h") -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df.empty:
            return None
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df.index.name = "timestamp"
        print(f"[DATA] yfinance → {symbol} | {len(df)} bars")
        return df
    except Exception as e:
        print(f"[yfinance] Failed: {e}")
        return None


def get_data(symbol: str = "BTC-USD", period: str = "6mo", interval: str = "1h",
             use_synthetic: bool = False, api_key: str = None) -> pd.DataFrame:
    if use_synthetic:
        print(f"[DATA] Synthetic → {symbol}")
        return generate_synthetic_data(symbol=symbol, days=180,
                                       start_price=60000 if "BTC" in symbol.upper() else 100.0)

    # 1. Twelve Data
    df = fetch_twelve_data(symbol, interval=interval, api_key=api_key or TWELVE_DATA_KEY)
    if df is not None and len(df) > 50:
        return df

    # 2. Finnhub
    df = fetch_finnhub(symbol, resolution=interval, api_key=FINNHUB_KEY)
    if df is not None and len(df) > 50:
        return df

    # 3. yfinance
    df = fetch_yfinance(symbol, period=period, interval=interval)
    if df is not None and len(df) > 50:
        return df

    # 4. Synthetic
    print(f"[DATA] Fallback synthetic → {symbol}")
    return generate_synthetic_data(symbol=symbol, days=180,
                                   start_price=60000 if "BTC" in symbol.upper() else 100.0)
