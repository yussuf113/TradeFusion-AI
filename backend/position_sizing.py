"""
TradeFusion AI - Position Sizing
"""

from typing import Dict


def calculate_position_size(
    account_balance: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_loss_price: float,
    max_position_pct: float = 10.0
) -> Dict:
    """
    Risk-based position sizing.

    Returns quantity and risk details.
    """
    if entry_price <= 0 or stop_loss_price <= 0 or account_balance <= 0:
        return {"quantity": 0, "risk_amount": 0, "error": "Invalid inputs"}

    risk_amount = account_balance * (risk_per_trade_pct / 100)
    price_risk = abs(entry_price - stop_loss_price)

    if price_risk == 0:
        return {"quantity": 0, "risk_amount": risk_amount, "error": "Stop loss equals entry"}

    quantity = risk_amount / price_risk

    # Cap by max position size
    max_qty = (account_balance * (max_position_pct / 100)) / entry_price
    quantity = min(quantity, max_qty)

    position_value = quantity * entry_price

    return {
        "quantity": round(quantity, 6),
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_pct": risk_per_trade_pct,
        "stop_distance": round(price_risk, 4),
        "max_position_pct": max_position_pct
    }
