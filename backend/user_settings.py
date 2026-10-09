"""
TradeFusion AI - User Settings & Selection Persistence
Persists the last selected asset, timeframe, and preferences to data/user_settings.json.

Guarantees:
  - Restores last valid selection across browser refreshes / app restarts.
  - Falls back safely to BTC-USD and 1h interval if settings are missing or corrupted.
  - Strict validation against supported assets and intervals.
  - Changing selections never creates a trade.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

DATA_DIR = Path("data")
SETTINGS_FILE = DATA_DIR / "user_settings.json"

VALID_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "GC=F", "SI=F",
    "EURUSD=X", "GBPUSD=X", "USDJPY=X",
    "AAPL", "TSLA",
]

VALID_INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"]
VALID_PERIODS = ["3mo", "6mo", "1y"]
VALID_RISK_MODES = ["low", "medium", "high"]

DEFAULT_SETTINGS = {
    "symbol": "BTC-USD",
    "interval": "1h",
    "period": "6mo",
    "risk_mode": "medium",
    "account_balance": 10000.0,
    "risk_pct": 1.0,
    "max_pos_pct": 10.0,
}


def load_user_settings(filepath: Path = SETTINGS_FILE) -> Dict[str, Any]:
    """
    Safely load user settings from JSON.
    Returns validated settings, falling back to defaults for any missing/invalid keys.
    """
    path = Path(filepath)
    settings = dict(DEFAULT_SETTINGS)

    if not path.exists():
        return settings

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return settings
            data = json.loads(content)

        if not isinstance(data, dict):
            return settings

        # Validate symbol
        saved_sym = data.get("symbol")
        if saved_sym in VALID_SYMBOLS:
            settings["symbol"] = saved_sym

        # Validate interval
        saved_interval = data.get("interval")
        if saved_interval in VALID_INTERVALS:
            settings["interval"] = saved_interval

        # Validate period
        saved_period = data.get("period")
        if saved_period in VALID_PERIODS:
            settings["period"] = saved_period

        # Validate risk_mode
        saved_risk = data.get("risk_mode")
        if saved_risk in VALID_RISK_MODES:
            settings["risk_mode"] = saved_risk

        # Numeric fields
        if "account_balance" in data and isinstance(data["account_balance"], (int, float)) and data["account_balance"] > 0:
            settings["account_balance"] = float(data["account_balance"])

        if "risk_pct" in data and isinstance(data["risk_pct"], (int, float)) and 0.1 <= data["risk_pct"] <= 10.0:
            settings["risk_pct"] = float(data["risk_pct"])

        if "max_pos_pct" in data and isinstance(data["max_pos_pct"], (int, float)) and 1.0 <= data["max_pos_pct"] <= 100.0:
            settings["max_pos_pct"] = float(data["max_pos_pct"])

        return settings

    except Exception:
        # Corrupted JSON -> fall back cleanly to defaults
        return settings


def save_user_settings(
    settings: Dict[str, Any],
    filepath: Path = SETTINGS_FILE,
) -> bool:
    """
    Safely and atomically persist updated user settings.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Clean and validate prior to saving
    to_save = dict(DEFAULT_SETTINGS)
    current = load_user_settings(filepath=path)
    to_save.update(current)

    for k, v in settings.items():
        if k == "symbol" and v in VALID_SYMBOLS:
            to_save["symbol"] = v
        elif k == "interval" and v in VALID_INTERVALS:
            to_save["interval"] = v
        elif k == "period" and v in VALID_PERIODS:
            to_save["period"] = v
        elif k == "risk_mode" and v in VALID_RISK_MODES:
            to_save["risk_mode"] = v
        elif k in ("account_balance", "risk_pct", "max_pos_pct") and isinstance(v, (int, float)) and v > 0:
            to_save[k] = float(v)

    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return False
