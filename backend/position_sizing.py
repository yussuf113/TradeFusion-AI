"""
TradeFusion AI - Position Sizing Engine
Asset-specific sizing supporting Crypto, Forex, Metals/Commodities, and Stocks.
Follows the formula:
  Risk Amount = Account Balance * (Risk % / 100)
  Position Size = Risk Amount / Stop Loss Distance (adjusted by contract / pip size)
"""

from typing import Dict, Optional


def get_symbol_category(symbol: str) -> str:
    sym = symbol.upper()
    if any(k in sym for k in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "USDT"]):
        return "crypto"
    if sym.endswith("=X") or any(k in sym for k in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]):
        return "forex"
    if sym in ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"] or "XAU" in sym or "XAG" in sym:
        return "commodity"
    return "stock"


def calculate_position_size(
    account_balance: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_loss_price: float,
    take_profit_price: Optional[float] = None,
    symbol: str = "BTC-USD",
    max_position_pct: float = 10.0
) -> Dict:
    """
    Risk-based position sizing with asset-specific conventions.

    Parameters
    ----------
    account_balance : Account equity in USD
    risk_per_trade_pct : Risk percentage per trade (e.g., 1.0% to 5.0%)
    entry_price : Planned trade entry price
    stop_loss_price : Planned trade stop loss price
    take_profit_price : Planned take profit price (optional)
    symbol : Asset ticker (used to determine asset category and sizing convention)
    max_position_pct : Maximum allowed portfolio exposure percentage

    Returns
    -------
    Dict with position sizing details, units, risk amount, and projected P/L.
    """
    if entry_price <= 0 or stop_loss_price <= 0 or account_balance <= 0:
        return {
            "quantity": 0.0,
            "position_size": 0.0,
            "unit": "Units",
            "risk_amount": 0.0,
            "error": "Invalid inputs (prices and balance must be positive)"
        }

    category = get_symbol_category(symbol)
    price_risk = abs(entry_price - stop_loss_price)

    if price_risk == 0:
        return {
            "quantity": 0.0,
            "position_size": 0.0,
            "unit": "Units",
            "risk_amount": 0.0,
            "error": "Stop loss equals entry price (zero risk distance)"
        }

    risk_amount = round(account_balance * (risk_per_trade_pct / 100.0), 2)
    max_capital_allocation = account_balance * (max_position_pct / 100.0)

    # 1. FOREX (Standard lot = 100,000 currency units)
    if category == "forex":
        is_jpy = "JPY" in symbol.upper()
        pip_size = 0.01 if is_jpy else 0.0001
        pips_at_risk = price_risk / pip_size
        
        # Approximate standard lot pip value = $10 for USD quote
        pip_value_std_lot = 10.0 if not is_jpy else (10.0 * 100.0 / entry_price if entry_price > 0 else 10.0)
        
        if pips_at_risk > 0 and pip_value_std_lot > 0:
            lots = risk_amount / (pips_at_risk * pip_value_std_lot)
        else:
            lots = 0.0

        # Exposure cap check: standard lot is 100,000 units
        max_lots = (max_capital_allocation * 20.0) / 100000.0  # Assumes typical 1:20 margin limit
        lots = min(lots, max(max_lots, 0.01))
        lots = round(lots, 2)
        quantity = lots
        unit = "Lots (Std 100k)"
        position_value = round(lots * 100000.0 * (1.0 if not is_jpy else 1.0 / entry_price), 2)

    # 2. STOCKS (Shares - integer or fractional)
    elif category == "stock":
        raw_shares = risk_amount / price_risk
        max_shares = max_capital_allocation / entry_price
        shares = min(raw_shares, max_shares)
        shares = round(shares, 2)
        quantity = shares
        unit = "Shares"
        position_value = round(shares * entry_price, 2)

    # 3. METALS / COMMODITIES (Futures / CFD)
    elif category == "commodity":
        # GC=F gold is 100 oz per contract, SI=F silver is 5000 oz
        contract_multiplier = 100.0 if "GC" in symbol.upper() or "XAU" in symbol.upper() else (5000.0 if "SI" in symbol.upper() else 1.0)
        contract_risk = price_risk * contract_multiplier
        if contract_risk > 0:
            contracts = risk_amount / contract_risk
        else:
            contracts = 0.0
        contracts = round(contracts, 3)
        quantity = contracts
        unit = "Contracts" if contract_multiplier > 1 else "Units"
        position_value = round(contracts * contract_multiplier * entry_price, 2)

    # 4. CRYPTO (Coins / Tokens)
    else:  # category == "crypto"
        raw_units = risk_amount / price_risk
        max_units = max_capital_allocation / entry_price
        units = min(raw_units, max_units)
        # Sizing precision depends on price
        decimals = 4 if entry_price > 100 else (2 if entry_price > 1 else 6)
        units = round(units, decimals)
        quantity = units
        unit = "Coins"
        position_value = round(units * entry_price, 2)

    # Calculate TP and projected profit if TP is supplied
    estimated_loss = round(risk_amount, 2)
    estimated_profit = None
    risk_reward_ratio = None

    if take_profit_price and take_profit_price > 0:
        profit_distance = abs(take_profit_price - entry_price)
        if price_risk > 0:
            rr = profit_distance / price_risk
            risk_reward_ratio = f"1:{rr:.2f}"
            estimated_profit = round(risk_amount * rr, 2)

    return {
        "quantity": quantity,
        "position_size": quantity,
        "unit": unit,
        "category": category.capitalize(),
        "position_value": position_value,
        "risk_amount": estimated_loss,
        "risk_pct": risk_per_trade_pct,
        "stop_distance": round(price_risk, 4),
        "estimated_loss_at_sl": estimated_loss,
        "estimated_profit_at_tp": estimated_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "max_position_pct": max_position_pct,
    }
