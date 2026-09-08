"""
TradeFusion AI - Performance Tracker
Stores signals and tracks win/loss outcomes
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

DATA_DIR = Path("data")
SIGNALS_FILE = DATA_DIR / "tracked_signals.json"


class PerformanceTracker:
    def __init__(self, filepath: Path = SIGNALS_FILE):
        self.filepath = filepath
        DATA_DIR.mkdir(exist_ok=True)
        self.signals: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if self.filepath.exists():
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.signals, f, indent=2, default=str)

    def add_signal(self, analysis: Dict) -> Dict:
        """Track a new signal."""
        signal = {
            "id": len(self.signals) + 1,
            "timestamp": analysis.get("timestamp") or datetime.utcnow().isoformat(),
            "symbol": analysis.get("symbol"),
            "signal": analysis.get("signal"),
            "confidence": analysis.get("confidence"),
            "price": analysis.get("price"),
            "risk_mode": analysis.get("risk_mode"),
            "structure": analysis.get("structure", {}).get("structure"),
            "status": "open",          # open | win | loss | expired
            "exit_price": None,
            "pnl_pct": None,
            "closed_at": None,
            "notes": ""
        }
        self.signals.append(signal)
        self._save()
        return signal

    def close_signal(self, signal_id: int, exit_price: float, status: str = None) -> Optional[Dict]:
        """Mark a signal as win/loss and calculate PnL."""
        for s in self.signals:
            if s["id"] == signal_id and s["status"] == "open":
                s["exit_price"] = exit_price
                s["closed_at"] = datetime.utcnow().isoformat()

                entry = s["price"]
                if s["signal"] == "BUY":
                    pnl = (exit_price - entry) / entry * 100
                else:
                    pnl = (entry - exit_price) / entry * 100

                s["pnl_pct"] = round(pnl, 2)

                if status:
                    s["status"] = status
                else:
                    s["status"] = "win" if pnl > 0 else "loss"

                self._save()
                return s
        return None

    def get_open_signals(self) -> List[Dict]:
        return [s for s in self.signals if s["status"] == "open"]

    def get_closed_signals(self) -> List[Dict]:
        return [s for s in self.signals if s["status"] in ("win", "loss")]

    def summary(self) -> Dict:
        closed = self.get_closed_signals()
        if not closed:
            return {
                "total_signals": len(self.signals),
                "open": len(self.get_open_signals()),
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "total_pnl": 0.0
            }

        wins = [s for s in closed if s["status"] == "win"]
        losses = [s for s in closed if s["status"] == "loss"]
        pnls = [s["pnl_pct"] for s in closed if s["pnl_pct"] is not None]

        return {
            "total_signals": len(self.signals),
            "open": len(self.get_open_signals()),
            "closed": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
            "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "total_pnl": round(sum(pnls), 2) if pnls else 0.0
        }

    def summary_by_symbol(self) -> Dict[str, Dict]:
        closed = self.get_closed_signals()
        by_sym = {}
        for s in closed:
            sym = s["symbol"]
            if sym not in by_sym:
                by_sym[sym] = {"wins": 0, "losses": 0, "pnls": []}
            if s["status"] == "win":
                by_sym[sym]["wins"] += 1
            else:
                by_sym[sym]["losses"] += 1
            if s["pnl_pct"] is not None:
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
