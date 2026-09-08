"""
TradeFusion AI - Supabase storage for tracked signals
Falls back to local JSON if Supabase is not configured.
"""

import os
from typing import Dict, List, Optional
from datetime import datetime

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
TABLE = "tracked_signals"


class SupabaseStore:
    def __init__(self):
        self.client: Optional["Client"] = None
        if HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                print("[Supabase] Connected")
            except Exception as e:
                print(f"[Supabase] Connection failed: {e}")
                self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def add_signal(self, analysis: Dict) -> Optional[Dict]:
        if not self.client:
            return None
        row = {
            "timestamp": analysis.get("timestamp") or datetime.utcnow().isoformat(),
            "symbol": analysis.get("symbol"),
            "signal": analysis.get("signal"),
            "confidence": analysis.get("confidence"),
            "price": analysis.get("price"),
            "risk_mode": analysis.get("risk_mode"),
            "structure": analysis.get("structure", {}).get("structure") if isinstance(analysis.get("structure"), dict) else analysis.get("structure"),
            "status": "open",
            "exit_price": None,
            "pnl_pct": None,
            "closed_at": None,
            "notes": ""
        }
        try:
            res = self.client.table(TABLE).insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[Supabase] Insert error: {e}")
        return None

    def close_signal(self, signal_id: int, exit_price: float, status: str = None) -> Optional[Dict]:
        if not self.client:
            return None
        try:
            # Fetch current
            res = self.client.table(TABLE).select("*").eq("id", signal_id).single().execute()
            s = res.data
            if not s or s.get("status") != "open":
                return None
            entry = float(s["price"])
            if s["signal"] == "BUY":
                pnl = (exit_price - entry) / entry * 100
            else:
                pnl = (entry - exit_price) / entry * 100
            update = {
                "exit_price": exit_price,
                "pnl_pct": round(pnl, 2),
                "closed_at": datetime.utcnow().isoformat(),
                "status": status or ("win" if pnl > 0 else "loss")
            }
            res2 = self.client.table(TABLE).update(update).eq("id", signal_id).execute()
            return res2.data[0] if res2.data else None
        except Exception as e:
            print(f"[Supabase] Close error: {e}")
            return None

    def list_signals(self, status: str = None) -> List[Dict]:
        if not self.client:
            return []
        try:
            q = self.client.table(TABLE).select("*").order("id", desc=True)
            if status:
                q = q.eq("status", status)
            res = q.execute()
            return res.data or []
        except Exception as e:
            print(f"[Supabase] List error: {e}")
            return []
