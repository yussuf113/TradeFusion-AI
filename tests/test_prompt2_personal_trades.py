"""
TradeFusion AI - Prompt 2 Test Suite: Personal Trade History & Persistent Selection
Covers all 14 specific Prompt 2 requirements:
  1. NO TRADE creates no personal trade
  2. An ignored signal creates no personal trade
  3. One ENTER TRADE action creates exactly one record
  4. Duplicate submission does not create duplicate trades
  5. Backtests and scanner signals never enter personal history
  6. Manual close records correct exit details and P/L
  7. TP/SL closure works and is not recorded twice
  8. Review time does not automatically close a trade
  9. Expiry handling is distinct from review time
  10. Unavailable/stale market data does not fabricate outcomes
  11. Existing records survive reload and are not silently erased
  12. Asset and timeframe selections persist across refresh/revisit
  13. Invalid saved selections fall back safely
  14. Refreshing or changing a selection does not create a trade
"""

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

from backend.personal_trades import PersonalTradeManager
from backend.user_settings import (
    load_user_settings,
    save_user_settings,
    DEFAULT_SETTINGS,
    VALID_SYMBOLS,
    VALID_INTERVALS,
)
from backend.backtester import Backtester
from backend.performance.tracker import PerformanceTracker


def make_sample_buy_analysis(symbol="BTC-USD", entry=60000.0, sl=59000.0, tp=62000.0):
    now_utc = datetime.now(timezone.utc)
    return {
        "symbol": symbol,
        "signal": "BUY",
        "confidence": 72.5,
        "price": entry,
        "risk_mode": "medium",
        "timeframe": "1h",
        "trade_setup": {
            "direction": "BUY",
            "entry": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_reward": "1:2.00",
            "signal_time": now_utc.isoformat(),
            "review_time": (now_utc + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M UTC"),
            "atr": 500.0,
            "execution_type": "SIMULATED",
        },
    }


def make_sample_no_trade_analysis(symbol="BTC-USD"):
    now_utc = datetime.now(timezone.utc)
    return {
        "symbol": symbol,
        "signal": "NO TRADE",
        "confidence": 56.0,
        "price": 60000.0,
        "risk_mode": "medium",
        "timeframe": "1h",
        "trade_setup": None,
    }


class TestPrompt2PersonalTradesAndSelection(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.trades_file = Path(self.tmp_dir.name) / "test_personal_trades.json"
        self.settings_file = Path(self.tmp_dir.name) / "test_user_settings.json"
        self.manager = PersonalTradeManager(storage_file=self.trades_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_no_trade_creates_no_personal_trade(self):
        """1. NO TRADE creates no personal trade."""
        no_trade_analysis = make_sample_no_trade_analysis()
        ok, msg, trade = self.manager.create_personal_trade(no_trade_analysis)
        self.assertFalse(ok)
        self.assertIn("NO TRADE", msg)
        self.assertIsNone(trade)
        self.assertEqual(len(self.manager.get_all_trades()), 0)

    def test_02_ignored_signal_creates_no_personal_trade(self):
        """2. An ignored signal creates no personal trade."""
        buy_analysis = make_sample_buy_analysis()
        # User receives analysis but never calls create_personal_trade()
        self.assertEqual(len(self.manager.get_all_trades()), 0)
        self.assertEqual(len(self.manager.get_open_trades()), 0)

    def test_03_enter_trade_creates_exactly_one_record(self):
        """3. One ENTER TRADE action creates exactly one record."""
        buy_analysis = make_sample_buy_analysis()
        pos_sizing = {
            "position_size": 0.1,
            "unit": "Coins",
            "risk_amount": 100.0,
        }
        ok, msg, trade = self.manager.create_personal_trade(
            analysis=buy_analysis,
            position_sizing=pos_sizing,
            user_notes="My test trade",
        )
        self.assertTrue(ok)
        self.assertIsNotNone(trade)
        self.assertEqual(len(self.manager.get_all_trades()), 1)
        self.assertEqual(trade["status"], "OPEN")
        self.assertEqual(trade["direction"], "BUY")
        self.assertEqual(trade["entry_price"], 60000.0)
        self.assertEqual(trade["notes"], "My test trade")
        self.assertEqual(trade["execution_type"], "PERSONAL_PAPER_TRADE")
        self.assertTrue(trade["paper_trade"])

    def test_04_duplicate_submission_prevented(self):
        """4. Duplicate submission does not create duplicate trades."""
        buy_analysis = make_sample_buy_analysis()
        ok1, msg1, t1 = self.manager.create_personal_trade(buy_analysis)
        self.assertTrue(ok1)

        # Immediate duplicate submission with identical parameters
        ok2, msg2, t2 = self.manager.create_personal_trade(buy_analysis)
        self.assertFalse(ok2)
        self.assertIn("Duplicate", msg2)
        self.assertEqual(len(self.manager.get_all_trades()), 1)

    def test_05_backtests_and_scanners_never_enter_personal_history(self):
        """5. Backtests and scanner signals never enter personal history."""
        # 1. Backtest run
        dates = pd.date_range("2026-01-01", periods=100, freq="1h")
        df_mock = pd.DataFrame({
            "open": 60000.0, "high": 60100.0, "low": 59900.0, "close": 60050.0, "volume": 1000.0,
        }, index=dates)
        bt = Backtester(risk_mode="medium")
        _ = bt.run(df_mock, symbol="BTC-USD")

        # 2. Performance Tracker run
        tracker = PerformanceTracker()
        tracker.add_signal(make_sample_buy_analysis())

        # Personal history must still be 0!
        self.assertEqual(len(self.manager.get_all_trades()), 0)

    def test_06_manual_close_records_correct_exit_details_and_pnl(self):
        """6. Manual close records correct exit details and P/L."""
        buy_analysis = make_sample_buy_analysis(entry=60000.0)
        pos_sizing = {"position_size": 0.1, "unit": "Coins", "risk_amount": 100.0}
        ok, _, trade = self.manager.create_personal_trade(buy_analysis, pos_sizing)
        self.assertTrue(ok)
        trade_id = trade["trade_id"]

        # Manual close at 63000 (+5% gain)
        ok_c, msg_c, closed = self.manager.close_trade_manually(
            trade_id=trade_id,
            exit_price=63000.0,
            reason="User take profit early",
        )
        self.assertTrue(ok_c)
        self.assertEqual(closed["status"], "CLOSED_MANUAL")
        self.assertEqual(closed["exit_price"], 63000.0)
        self.assertEqual(closed["pnl_pct"], 5.0)
        self.assertEqual(closed["outcome"], "WIN")
        self.assertEqual(closed["exit_reason"], "User take profit early")
        self.assertIsNotNone(closed["exit_time"])

    def test_07_tp_sl_closure_and_no_double_closure(self):
        """7. TP/SL closure works and is not recorded twice."""
        buy_analysis = make_sample_buy_analysis(entry=60000.0, sl=59000.0, tp=62000.0)
        ok, _, trade = self.manager.create_personal_trade(buy_analysis)
        self.assertTrue(ok)

        # Price reaches Take Profit
        closed_events = self.manager.check_and_update_trades({"BTC-USD": 62500.0})
        self.assertEqual(len(closed_events), 1)
        self.assertEqual(closed_events[0]["status"], "CLOSED_TP")
        self.assertEqual(closed_events[0]["outcome"], "WIN")

        # Second update with same high price: must NOT trigger closure again
        closed_again = self.manager.check_and_update_trades({"BTC-USD": 63000.0})
        self.assertEqual(len(closed_again), 0)
        self.assertEqual(len(self.manager.get_open_trades()), 0)
        self.assertEqual(len(self.manager.get_closed_trades()), 1)

    def test_08_review_time_does_not_close_trade(self):
        """8. Review time is a review reminder, NOT an automatic close."""
        buy_analysis = make_sample_buy_analysis(entry=60000.0, sl=59000.0, tp=62000.0)
        ok, _, trade = self.manager.create_personal_trade(buy_analysis)
        self.assertTrue(ok)

        # Simulate current time past review time (+5 hours), price still between SL and TP
        future_time = datetime.now(timezone.utc) + timedelta(hours=5)
        closed_events = self.manager.check_and_update_trades(
            symbol_prices={"BTC-USD": 60500.0},
            current_time=future_time,
        )
        self.assertEqual(len(closed_events), 0)
        self.assertEqual(trade["status"], "OPEN")
        self.assertEqual(len(self.manager.get_open_trades()), 1)

    def test_09_expiry_handling_is_distinct_from_review_time(self):
        """9. Expiry handling is distinct from review time."""
        buy_analysis = make_sample_buy_analysis(entry=60000.0, sl=59000.0, tp=62000.0)
        # Explicit expiry in 2 hours
        ok, _, trade = self.manager.create_personal_trade(buy_analysis, expiry_hours=2.0)
        self.assertTrue(ok)
        self.assertIsNotNone(trade["expiry_time"])

        # Check before expiry (+1 hour): remains OPEN
        t_plus_1h = datetime.now(timezone.utc) + timedelta(hours=1)
        res_1h = self.manager.check_and_update_trades({"BTC-USD": 60500.0}, current_time=t_plus_1h)
        self.assertEqual(len(res_1h), 0)
        self.assertEqual(trade["status"], "OPEN")

        # Check after expiry (+3 hours): closes with EXPIRED
        t_plus_3h = datetime.now(timezone.utc) + timedelta(hours=3)
        res_3h = self.manager.check_and_update_trades({"BTC-USD": 60500.0}, current_time=t_plus_3h)
        self.assertEqual(len(res_3h), 1)
        self.assertEqual(res_3h[0]["status"], "CLOSED_EXPIRED")
        self.assertEqual(res_3h[0]["exit_reason"], "EXPIRED")

    def test_10_unavailable_market_data_does_not_fabricate_outcome(self):
        """10. Unavailable/stale market data does not fabricate outcomes."""
        buy_analysis = make_sample_buy_analysis()
        ok, _, trade = self.manager.create_personal_trade(buy_analysis)
        self.assertTrue(ok)

        # Feed invalid/unavailable prices: None, 0.0, negative
        res = self.manager.check_and_update_trades({
            "BTC-USD": None,
            "ETH-USD": 0.0,
            "EURUSD=X": -1.0,
        })
        self.assertEqual(len(res), 0)
        self.assertEqual(trade["status"], "OPEN")
        self.assertIsNone(trade["exit_price"])

    def test_11_records_survive_reload_without_erasure(self):
        """11. Existing records survive reload and are not silently erased."""
        buy_analysis = make_sample_buy_analysis()
        ok, _, trade = self.manager.create_personal_trade(buy_analysis, user_notes="Persistent test")
        self.assertTrue(ok)

        # Create new manager pointing to same storage file
        reloaded_mgr = PersonalTradeManager(storage_file=self.trades_file)
        all_trades = reloaded_mgr.get_all_trades()
        self.assertEqual(len(all_trades), 1)
        self.assertEqual(all_trades[0]["trade_id"], trade["trade_id"])
        self.assertEqual(all_trades[0]["notes"], "Persistent test")

    def test_12_asset_and_timeframe_selections_persist(self):
        """12. Asset and timeframe selections persist across refresh/revisit."""
        save_user_settings({
            "symbol": "EURUSD=X",
            "interval": "15m",
            "period": "3mo",
            "risk_mode": "high",
        }, filepath=self.settings_file)

        loaded = load_user_settings(filepath=self.settings_file)
        self.assertEqual(loaded["symbol"], "EURUSD=X")
        self.assertEqual(loaded["interval"], "15m")
        self.assertEqual(loaded["period"], "3mo")
        self.assertEqual(loaded["risk_mode"], "high")

    def test_13_invalid_saved_selections_fall_back_safely(self):
        """13. Invalid saved selections fall back safely to defaults."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"symbol": "NONEXISTENT_COIN", "interval": "99hours"}))

        loaded = load_user_settings(filepath=self.settings_file)
        self.assertEqual(loaded["symbol"], "BTC-USD")
        self.assertEqual(loaded["interval"], "1h")

        # Test corrupted JSON
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write("CORRUPTED_JSON_DATA{{{")
        loaded_corrupt = load_user_settings(filepath=self.settings_file)
        self.assertEqual(loaded_corrupt["symbol"], "BTC-USD")
        self.assertEqual(loaded_corrupt["interval"], "1h")

    def test_14_refreshing_or_changing_selection_creates_no_trade(self):
        """14. Refreshing or changing a selection does not create a trade."""
        initial_count = len(self.manager.get_all_trades())

        # Change settings multiple times
        save_user_settings({"symbol": "GC=F", "interval": "4h"}, filepath=self.settings_file)
        save_user_settings({"symbol": "AAPL", "interval": "1d"}, filepath=self.settings_file)
        _ = load_user_settings(filepath=self.settings_file)

        self.assertEqual(len(self.manager.get_all_trades()), initial_count)


if __name__ == "__main__":
    unittest.main()
