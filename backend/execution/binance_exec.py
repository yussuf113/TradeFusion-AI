"""
TradeFusion AI - Binance Execution
Paper mode by default. Live trading requires explicit enable + API keys.
"""

import os
import time
from typing import Dict, Optional
from datetime import datetime

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False


class BinanceExecutor:
    """
    Paper trading simulator by default.
    Set BINANCE_API_KEY + BINANCE_API_SECRET and live=True for real orders.
    """

    def __init__(self, live: bool = False, quote_budget: float = 100.0):
        self.live = live and os.getenv("BINANCE_LIVE", "false").lower() == "true"
        self.api_key = os.getenv("BINANCE_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_API_SECRET", "")
        self.quote_budget = quote_budget  # USDT per trade in paper mode
        self.paper_positions = {}
        self.paper_trades = []
        self.exchange = None

        if self.live and HAS_CCXT and self.api_key and self.api_secret:
            self.exchange = ccxt.binance({
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
            print("[Binance] LIVE mode enabled")
        else:
            if live:
                print("[Binance] Live requested but keys/ccxt missing → PAPER mode")
            else:
                print("[Binance] PAPER trading mode")

    def _symbol_to_binance(self, symbol: str) -> str:
        mapping = {
            "BTC-USD": "BTC/USDT",
            "ETH-USD": "ETH/USDT",
            "SOL-USD": "SOL/USDT",
            "BNB-USD": "BNB/USDT",
            "XRP-USD": "XRP/USDT",
        }
        return mapping.get(symbol, symbol.replace("-USD", "/USDT"))

    def place_order(self, symbol: str, side: str, confidence: float, price: float = None) -> Dict:
        """
        side: BUY or SELL
        Returns order result dict.
        """
        bn_symbol = self._symbol_to_binance(symbol)
        ts = datetime.utcnow().isoformat()

        if self.exchange and self.live:
            try:
                # Market order with small fixed quote amount for safety
                amount_usd = float(os.getenv("BINANCE_ORDER_USDT", "15"))
                if side == "BUY":
                    order = self.exchange.create_market_buy_order_with_cost(bn_symbol, amount_usd)
                else:
                    # For sell need base amount — simplify: skip if no position tracking
                    return {"status": "error", "message": "Live SELL requires position tracking — use paper first"}
                return {"status": "live", "order": order, "symbol": bn_symbol, "side": side, "time": ts}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # Paper trade
        trade = {
            "id": len(self.paper_trades) + 1,
            "symbol": bn_symbol,
            "side": side,
            "price": price,
            "confidence": confidence,
            "budget_usdt": self.quote_budget,
            "status": "paper_filled",
            "time": ts,
        }
        self.paper_trades.append(trade)
        self.paper_positions[bn_symbol] = trade
        print(f"[PAPER] {side} {bn_symbol} @ {price} | Conf {confidence}%")
        return trade

    def get_paper_trades(self):
        return self.paper_trades
