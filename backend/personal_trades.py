"""
TradeFusion AI - Personal Paper Trade Manager
Handles user-initiated personal paper trades, lifecycle monitoring, and persistence.

Guarantees:
  - Only explicit ENTER TRADE user action creates a personal trade.
  - Zero automatic trade creation from signals, scanners, or backtests.
  - Idempotent creation prevents duplicate submissions.
  - Explicit SIMULATED / PAPER TRADE labeling.
  - Review time is a review reminder, distinct from trade expiry.
  - Real market data required for monitoring; zero fabricated prices.
"""

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path("data")
PERSONAL_TRADES_FILE = DATA_DIR / "personal_trades.json"


class PersonalTradeManager:
    """Manages explicit user-initiated personal paper trades."""

    def __init__(self, storage_file: Path = PERSONAL_TRADES_FILE):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._trades: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        """Safely load personal trades from JSON storage."""
        if not self.storage_file.exists():
            return []
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            # Handle corrupted file safely without crashing
            return []

    def _save(self) -> None:
        """Atomically persist personal trades to prevent corruption."""
        tmp_file = self.storage_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._trades, f, indent=2, default=str)
            # Atomic replace
            os.replace(tmp_file, self.storage_file)
        except Exception as e:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass
            raise IOError(f"Failed to persist personal trades: {e}")

    def create_personal_trade(
        self,
        analysis: Dict,
        position_sizing: Optional[Dict] = None,
        user_notes: str = "",
        client_request_id: Optional[str] = None,
        expiry_hours: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Create a personal paper trade from an active, verified BUY/SELL setup.

        Returns: (success: bool, message: str, trade: Optional[Dict])
        """
        if not analysis or not isinstance(analysis, dict):
            return False, "Cannot create trade: Invalid analysis data.", None

        if "error" in analysis:
            return False, f"Cannot create trade: Analysis error ({analysis['error']}).", None

        signal = analysis.get("signal")
        if signal not in ("BUY", "SELL"):
            return False, f"Cannot create trade: Signal is {signal}. Only BUY and SELL setups are eligible.", None

        setup = analysis.get("trade_setup")
        if not setup or not isinstance(setup, dict):
            return False, "Cannot create trade: No valid trade setup parameters found.", None

        entry_price = setup.get("entry")
        stop_loss = setup.get("stop_loss")
        take_profit = setup.get("take_profit")

        if not (entry_price and stop_loss and take_profit):
            return False, "Cannot create trade: Incomplete price levels (Entry, SL, TP required).", None

        try:
            entry_price = float(entry_price)
            stop_loss = float(stop_loss)
            take_profit = float(take_profit)
        except (ValueError, TypeError):
            return False, "Cannot create trade: Non-numeric price levels.", None

        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return False, "Cannot create trade: Price levels must be positive.", None

        symbol = str(analysis.get("symbol", "UNKNOWN")).upper()
        signal_time = str(setup.get("signal_time", ""))
        timeframe = str(setup.get("timeframe", analysis.get("timeframe", "1h")))
        confidence = float(analysis.get("confidence", 0.0))
        risk_mode = str(analysis.get("risk_mode", "medium"))
        risk_reward = str(setup.get("risk_reward", "N/A"))
        review_time = setup.get("review_time")

        now_utc = datetime.now(timezone.utc)
        req_id = client_request_id or f"{symbol}_{signal}_{entry_price}_{signal_time}"

        # Deduplication check: Prevent identical open trade or identical request ID
        for existing in self._trades:
            if existing.get("client_request_id") == req_id:
                return False, "Duplicate submission: Trade with this request ID already exists.", existing
            if (
                existing.get("status") == "OPEN"
                and existing.get("symbol") == symbol
                and existing.get("direction") == signal
                and abs(existing.get("entry_price", 0) - entry_price) < 1e-6
                and existing.get("signal_time") == signal_time
            ):
                return False, "Duplicate trade: An identical open paper trade is already active.", existing

        # Sizing extraction
        pos_size = 0.0
        unit = "Units"
        risk_amount = 0.0
        if position_sizing and isinstance(position_sizing, dict):
            pos_size = float(position_sizing.get("position_size", 0.0))
            unit = str(position_sizing.get("unit", "Units"))
            risk_amount = float(position_sizing.get("risk_amount", 0.0))

        # Calculate optional expiry timestamp (distinct from review time)
        expiry_time_str = None
        if expiry_hours and expiry_hours > 0:
            expiry_dt = now_utc + timedelta(hours=expiry_hours)
            expiry_time_str = expiry_dt.isoformat()

        # Generate readable unique Trade ID
        trade_num = len(self._trades) + 1
        trade_id = f"PT-{trade_num:04d}-{uuid.uuid4().hex[:4].upper()}"

        new_trade = {
            "trade_id": trade_id,
            "client_request_id": req_id,
            "symbol": symbol,
            "direction": signal,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": risk_reward,
            "confidence": confidence,
            "risk_mode": risk_mode,
            "timeframe": timeframe,
            "signal_time": signal_time,
            "entry_time": now_utc.isoformat(),
            "review_time": str(review_time) if review_time else None,
            "expiry_time": expiry_time_str,
            "status": "OPEN",
            "current_price": entry_price,
            "exit_price": None,
            "exit_time": None,
            "exit_reason": None,
            "outcome": None,
            "pnl_amount": None,
            "pnl_pct": None,
            "position_size": pos_size,
            "unit": unit,
            "risk_amount": risk_amount,
            "notes": user_notes.strip() if user_notes else "",
            "paper_trade": True,
            "execution_type": "PERSONAL_PAPER_TRADE",
            "created_at": now_utc.isoformat(),
        }

        self._trades.append(new_trade)
        self._save()
        return True, f"Paper trade {trade_id} created successfully.", new_trade

    def check_and_update_trades(
        self,
        symbol_prices: Dict[str, float],
        current_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Monitor OPEN personal paper trades against live/valid market prices.
        Detects TP hit, SL hit, or Expiry.
        Review time is tracked as a review reminder, NOT an auto-exit.
        Returns a list of trades that were closed during this update.
        """
        if not symbol_prices:
            return []

        now_utc = current_time or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        closed_events = []
        modified = False

        for trade in self._trades:
            if trade.get("status") != "OPEN":
                continue

            sym = trade.get("symbol")
            if sym not in symbol_prices:
                continue

            current_px = symbol_prices[sym]
            if current_px is None or current_px <= 0:
                continue  # Never invent or fabricate price updates

            trade["current_price"] = float(current_px)
            modified = True

            entry = float(trade["entry_price"])
            sl = float(trade["stop_loss"])
            tp = float(trade["take_profit"])
            direction = trade["direction"]

            # 1. Take-Profit Check
            tp_hit = False
            if direction == "BUY" and current_px >= tp:
                tp_hit = True
            elif direction == "SELL" and current_px <= tp:
                tp_hit = True

            if tp_hit:
                self._finalize_close(trade, exit_price=tp, exit_reason="TAKE_PROFIT", exit_time=now_utc)
                closed_events.append(trade)
                continue

            # 2. Stop-Loss Check
            sl_hit = False
            if direction == "BUY" and current_px <= sl:
                sl_hit = True
            elif direction == "SELL" and current_px >= sl:
                sl_hit = True

            if sl_hit:
                self._finalize_close(trade, exit_price=sl, exit_reason="STOP_LOSS", exit_time=now_utc)
                closed_events.append(trade)
                continue

            # 3. Expiry Check (Distinct from review time)
            expiry_str = trade.get("expiry_time")
            if expiry_str:
                try:
                    exp_dt = datetime.fromisoformat(expiry_str)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if now_utc >= exp_dt:
                        self._finalize_close(trade, exit_price=current_px, exit_reason="EXPIRED", exit_time=now_utc)
                        closed_events.append(trade)
                        continue
                except Exception:
                    pass

        if modified:
            self._save()

        return closed_events

    def close_trade_manually(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "Manual User Close",
        exit_time: Optional[datetime] = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Manually close an open paper trade with an explicit exit price.
        """
        if exit_price <= 0:
            return False, "Cannot close trade: Exit price must be greater than zero.", None

        now_utc = exit_time or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        target_trade = None
        for trade in self._trades:
            if trade.get("trade_id") == trade_id:
                target_trade = trade
                break

        if not target_trade:
            return False, f"Trade '{trade_id}' not found.", None

        if target_trade.get("status") != "OPEN":
            return False, f"Trade '{trade_id}' is already closed (Status: {target_trade.get('status')}).", target_trade

        self._finalize_close(
            target_trade,
            exit_price=float(exit_price),
            exit_reason=reason or "Manual User Close",
            exit_time=now_utc,
        )
        self._save()
        return True, f"Trade {trade_id} closed manually at ${exit_price:,.4f}.", target_trade

    def _finalize_close(
        self,
        trade: Dict,
        exit_price: float,
        exit_reason: str,
        exit_time: datetime,
    ) -> None:
        """Internal helper to calculate realized P/L and finalize closed state."""
        entry = float(trade["entry_price"])
        direction = trade["direction"]

        if direction == "BUY":
            pnl_pct = ((exit_price - entry) / entry) * 100.0
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100.0

        pnl_pct = round(pnl_pct, 2)

        # Calculate PnL dollar amount if position size exists
        pos_size = float(trade.get("position_size", 0.0))
        pnl_amount = None
        if pos_size > 0:
            pnl_amount = round((pnl_pct / 100.0) * (pos_size * entry), 2)

        if pnl_pct > 0.05:
            outcome = "WIN"
        elif pnl_pct < -0.05:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        status_mapping = {
            "TAKE_PROFIT": "CLOSED_TP",
            "STOP_LOSS": "CLOSED_SL",
            "EXPIRED": "CLOSED_EXPIRED",
        }
        status = status_mapping.get(exit_reason, "CLOSED_MANUAL")

        trade["status"] = status
        trade["current_price"] = exit_price
        trade["exit_price"] = exit_price
        trade["exit_time"] = exit_time.isoformat()
        trade["exit_reason"] = exit_reason
        trade["outcome"] = outcome
        trade["pnl_pct"] = pnl_pct
        trade["pnl_amount"] = pnl_amount

    def get_open_trades(self) -> List[Dict]:
        """Return all open personal paper trades."""
        return [t for t in self._trades if t.get("status") == "OPEN"]

    def get_closed_trades(self) -> List[Dict]:
        """Return all closed personal paper trades."""
        return [t for t in self._trades if t.get("status") != "OPEN"]

    def get_all_trades(self) -> List[Dict]:
        """Return all trades in history."""
        return list(self._trades)

    def summary(self) -> Dict:
        """Calculate aggregate performance metrics for personal paper trades."""
        closed = self.get_closed_trades()
        open_trades = self.get_open_trades()

        if not closed:
            return {
                "total_trades": len(self._trades),
                "open_count": len(open_trades),
                "closed_count": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate": 0.0,
                "total_pnl_pct": 0.0,
                "total_pnl_amount": 0.0,
                "avg_trade_pnl": 0.0,
                "profit_factor": 0.0,
                "disclaimer": "PERSONAL PAPER TRADES (SIMULATED)",
            }

        wins = [t for t in closed if t.get("outcome") == "WIN"]
        losses = [t for t in closed if t.get("outcome") == "LOSS"]
        bes = [t for t in closed if t.get("outcome") == "BREAKEVEN"]

        pnls = [t["pnl_pct"] for t in closed if t.get("pnl_pct") is not None]
        amounts = [t["pnl_amount"] for t in closed if t.get("pnl_amount") is not None]

        win_rate = round((len(wins) / len(closed)) * 100.0, 1) if closed else 0.0
        total_pnl_pct = round(sum(pnls), 2) if pnls else 0.0
        total_pnl_amount = round(sum(amounts), 2) if amounts else 0.0
        avg_trade_pnl = round(sum(pnls) / len(pnls), 2) if pnls else 0.0

        gross_win = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)

        return {
            "total_trades": len(self._trades),
            "open_count": len(open_trades),
            "closed_count": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(bes),
            "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct,
            "total_pnl_amount": total_pnl_amount,
            "avg_trade_pnl": avg_trade_pnl,
            "profit_factor": profit_factor,
            "disclaimer": "PERSONAL PAPER TRADES (SIMULATED)",
        }
