"""
TradeFusion AI - Performance Tracker
Tracks SIMULATED analytical trades with TP/SL monitoring and review time auditing.
Uses Supabase when configured, otherwise local JSON file.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

from backend.performance.supabase_store import SupabaseStore

DATA_DIR = Path("data")
SIGNALS_FILE = DATA_DIR / "tracked_signals.json"


class PerformanceTracker:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self.supabase = SupabaseStore()
        self.use_supabase = self.supabase.is_configured
        self.signals: List[Dict] = [] if self.use_supabase else self._load_local()

    def _load_local(self) -> List[Dict]:
        if SIGNALS_FILE.exists():
            try:
                with open(SIGNALS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_local(self):
        with open(SIGNALS_FILE, "w") as f:
            json.dump(self.signals, f, indent=2, default=str)

    def add_signal(self, analysis: Dict) -> Dict:
        """Track a new simulated signal."""
        setup = analysis.get("trade_setup") or {}

        if self.use_supabase:
            row = self.supabase.add_signal(analysis)
            if row:
                return row

        # Local JSON storage
        signal = {
            "id": len(self.signals) + 1,
            "timestamp": analysis.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "symbol": analysis.get("symbol"),
            "signal": analysis.get("signal"),
            "confidence": analysis.get("confidence"),
            "price": analysis.get("price"),
            "stop_loss": setup.get("stop_loss"),
            "take_profit": setup.get("take_profit"),
            "risk_reward": setup.get("risk_reward"),
            "timeframe": analysis.get("timeframe", "1h"),
            "review_time": setup.get("review_time"),
            "risk_mode": analysis.get("risk_mode"),
            "structure": analysis.get("structure", {}).get("structure") if isinstance(analysis.get("structure"), dict) else None,
            "status": "open",
            "exit_price": None,
            "pnl_pct": None,
            "closed_at": None,
            "notes": "SIMULATED TRADE",
            "execution_type": "SIMULATED"
        }
        self.signals.append(signal)
        self._save_local()
        return signal

    def check_open_positions(self, symbol_prices: Dict[str, float]) -> List[Dict]:
        """
        Check open simulated trades against latest prices to detect TP/SL triggers.
        Returns a list of updated/closed trade events.
        """
        events = []
        for s in self.get_open_signals():
            sym = s.get("symbol")
            if sym not in symbol_prices:
                continue

            current_price = symbol_prices[sym]
            entry = s.get("price")
            sl = s.get("stop_loss")
            tp = s.get("take_profit")
            direction = s.get("signal")

            if not (entry and sl and tp):
                continue

            closed = None
            if direction == "BUY":
                if current_price >= tp:
                    closed = self.close_signal(s["id"], tp, status="win (TP Hit)")
                elif current_price <= sl:
                    closed = self.close_signal(s["id"], sl, status="loss (SL Hit)")
            elif direction == "SELL":
                if current_price <= tp:
                    closed = self.close_signal(s["id"], tp, status="win (TP Hit)")
                elif current_price >= sl:
                    closed = self.close_signal(s["id"], sl, status="loss (SL Hit)")

            if closed:
                events.append(closed)

        return events

    def close_signal(self, signal_id: int, exit_price: float, status: str = None) -> Optional[Dict]:
        if self.use_supabase:
            return self.supabase.close_signal(signal_id, exit_price, status)

        for s in self.signals:
            if s["id"] == signal_id and s["status"] == "open":
                s["exit_price"] = exit_price
                s["closed_at"] = datetime.now(timezone.utc).isoformat()
                entry = s["price"]
                if s["signal"] == "BUY":
                    pnl = (exit_price - entry) / entry * 100
                else:
                    pnl = (entry - exit_price) / entry * 100
                s["pnl_pct"] = round(pnl, 2)
                s["status"] = status or ("win" if pnl > 0 else "loss")
                self._save_local()
                return s
        return None

    def get_open_signals(self) -> List[Dict]:
        if self.use_supabase:
            return self.supabase.list_signals(status="open")
        return [s for s in self.signals if s.get("status") == "open"]

    def get_closed_signals(self) -> List[Dict]:
        if self.use_supabase:
            all_s = self.supabase.list_signals()
            return [s for s in all_s if s.get("status") in ("win", "loss") or "win" in str(s.get("status")) or "loss" in str(s.get("status"))]
        return [s for s in self.signals if s.get("status") != "open"]

    def summary(self) -> Dict:
        closed = self.get_closed_signals()
        open_s = self.get_open_signals()
        if not closed:
            return {
                "total_signals": len(closed) + len(open_s),
                "open": len(open_s),
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "total_pnl": 0.0,
                "disclaimer": "SIMULATED PERFORMANCE"
            }
        wins = [s for s in closed if "win" in str(s.get("status", "")).lower()]
        losses = [s for s in closed if "loss" in str(s.get("status", "")).lower()]
        pnls = [s["pnl_pct"] for s in closed if s.get("pnl_pct") is not None]
        return {
            "total_signals": len(closed) + len(open_s),
            "open": len(open_s),
            "closed": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "total_pnl": round(sum(pnls), 2) if pnls else 0.0,
            "disclaimer": "SIMULATED PERFORMANCE"
        }

    def summary_by_symbol(self) -> Dict[str, Dict]:
        closed = self.get_closed_signals()
        by_sym = {}
        for s in closed:
            sym = s.get("symbol", "?")
            if sym not in by_sym:
                by_sym[sym] = {"wins": 0, "losses": 0, "pnls": []}
            if "win" in str(s.get("status", "")).lower():
                by_sym[sym]["wins"] += 1
            else:
                by_sym[sym]["losses"] += 1
            if s.get("pnl_pct") is not None:
                by_sym[sym]["pnls"].append(s["pnl_pct"])
        result = {}
        for sym, data in by_sym.items():
            total = data["wins"] + data["losses"]
            result[sym] = {
                "trades": total,
                "wins": data["wins"],
                "losses": data["losses"],
                "win_rate": round(data["wins"] / total * 100, 1) if total else 0,
                "avg_pnl": round(sum(data["pnls"]) / len(data["pnls"]), 2) if data["pnls"] else 0
            }
        return result
