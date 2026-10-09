"""
TradeFusion AI - Market Schedule & Session Detection
Handles asset-specific trading sessions:
  - Crypto: 24/7 continuous trading
  - US Stocks (AAPL, TSLA, etc.): Mon-Fri 09:30 - 16:00 US Eastern Time (ET)
  - Forex (EURUSD=X, GBPUSD=X, USDJPY=X, etc.): Sun 17:00 ET - Fri 17:00 ET
  - Metals/Futures (GC=F, SI=F): Sun 18:00 ET - Fri 17:00 ET with daily 17:00-18:00 ET break
"""

from datetime import datetime, time, timezone, timedelta
from typing import Dict
import zoneinfo

def get_asset_category(symbol: str) -> str:
    sym = symbol.upper()
    if any(k in sym for k in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "USDT"]):
        return "crypto"
    if sym.endswith("=X") or any(k in sym for k in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]):
        return "forex"
    if sym in ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"] or "XAU" in sym or "XAG" in sym:
        return "commodity"
    return "stock"


def get_market_status(symbol: str, current_time: datetime = None) -> Dict:
    """
    Determine if the market for a given symbol is currently OPEN or CLOSED.
    Uses US/Eastern timezone for market exchange hours.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    try:
        et_tz = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        # Fallback if tzdata is missing on minimal environments
        et_tz = timezone(timedelta(hours=-4))

    et_time = current_time.astimezone(et_tz)
    weekday = et_time.weekday()  # 0=Monday, ..., 6=Sunday
    current_et_time = et_time.time()
    category = get_asset_category(symbol)

    # 1. Crypto (24/7)
    if category == "crypto":
        return {
            "is_open": True,
            "status": "OPEN",
            "session": "Crypto 24/7 Continuous Market",
            "category": "Crypto",
            "detail": "Market trades 24 hours a day, 7 days a week.",
            "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
        }

    # 2. US Equities (Stocks: Mon-Fri 09:30 - 16:00 ET)
    if category == "stock":
        if weekday in (5, 6):  # Saturday, Sunday
            return {
                "is_open": False,
                "status": "CLOSED",
                "session": "Weekend (US Equities Closed)",
                "category": "Stock",
                "detail": "US stock markets are closed on weekends.",
                "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
            }
        
        market_open = time(9, 30)
        market_close = time(16, 0)
        if market_open <= current_et_time < market_close:
            return {
                "is_open": True,
                "status": "OPEN",
                "session": "Regular US Market Hours (09:30 - 16:00 ET)",
                "category": "Stock",
                "detail": "Active NYSE / NASDAQ trading session.",
                "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
            }
        elif current_et_time < market_open:
            return {
                "is_open": False,
                "status": "CLOSED",
                "session": "Pre-Market / Closed",
                "category": "Stock",
                "detail": f"Market opens at 09:30 ET (Current: {et_time.strftime('%H:%M ET')}).",
                "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
            }
        else:
            return {
                "is_open": False,
                "status": "CLOSED",
                "session": "After Hours / Closed",
                "category": "Stock",
                "detail": "Market closed at 16:00 ET.",
                "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
            }

    # 3. Forex (Sun 17:00 ET to Fri 17:00 ET)
    if category == "forex":
        if weekday == 5:  # Saturday
            is_open = False
            session = "Weekend (Forex Closed)"
            detail = "Forex markets closed for the weekend until Sunday 17:00 ET."
        elif weekday == 6:  # Sunday
            if current_et_time >= time(17, 0):
                is_open = True
                session = "Sydney / Asian Session Open"
                detail = "Forex market opened Sunday 17:00 ET."
            else:
                is_open = False
                session = "Weekend (Forex Closed)"
                detail = "Forex opens Sunday at 17:00 ET."
        elif weekday == 4:  # Friday
            if current_et_time >= time(17, 0):
                is_open = False
                session = "Weekend Close"
                detail = "Forex market closed for the weekend at 17:00 ET Friday."
            else:
                is_open = True
                session = "Global Forex Session (Active)"
                detail = "Forex trading active."
        else:  # Mon, Tue, Wed, Thu
            is_open = True
            session = "Global Forex Session (Active)"
            detail = "Forex trading active 24h during the week."

        return {
            "is_open": is_open,
            "status": "OPEN" if is_open else "CLOSED",
            "session": session,
            "category": "Forex",
            "detail": detail,
            "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
        }

    # 4. Commodities / Metals (Futures: Sun 18:00 ET to Fri 17:00 ET, daily pause 17:00 - 18:00 ET)
    if category == "commodity":
        if weekday == 5:  # Saturday
            is_open = False
            session = "Weekend (Metals Closed)"
            detail = "Futures market closed for the weekend."
        elif weekday == 6:  # Sunday
            if current_et_time >= time(18, 0):
                is_open = True
                session = "CME Futures Open"
                detail = "Metals futures trading active."
            else:
                is_open = False
                session = "Weekend (Metals Closed)"
                detail = "Metals futures open Sunday at 18:00 ET."
        elif weekday == 4 and current_et_time >= time(17, 0):  # Friday after 17:00 ET
            is_open = False
            session = "Weekend Close"
            detail = "Metals closed for the weekend at 17:00 ET."
        else:  # Weekday
            if time(17, 0) <= current_et_time < time(18, 0):
                is_open = False
                session = "Daily Maintenance Pause (17:00 - 18:00 ET)"
                detail = "Daily trading halt on CME futures."
            else:
                is_open = True
                session = "CME Globex Session (Active)"
                detail = "Metals trading active."

        return {
            "is_open": is_open,
            "status": "OPEN" if is_open else "CLOSED",
            "session": session,
            "category": "Commodity / Metals",
            "detail": detail,
            "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
        }

    # Default fallback
    return {
        "is_open": True,
        "status": "OPEN",
        "session": "Active",
        "category": "General",
        "detail": "Market status assumed active.",
        "current_time_et": et_time.strftime("%Y-%m-%d %H:%M ET")
    }
