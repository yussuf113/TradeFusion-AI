"""
TradeFusion AI - Core Test Suite
Validates:
  1. No synthetic data, real data fallback, returns None on failure
  2. Distinction between DATA UNAVAILABLE and NO TRADE
  3. Technical engine integrity & trade setup generation (Entry, SL, TP, R:R, Review Time)
  4. Asset-specific market schedule detection
  5. Position sizing for all asset classes
  6. Performance tracker simulated monitoring & TP/SL detection
  7. Backtest execution & reporting
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from backend.data.fetcher import get_data, _FINNHUB_RESOLUTION_MAP, _TWELVE_INTERVAL_MAP
from backend.indicators.core import compute_all_indicators
from backend.confidence.engine import ConfidenceEngine
from backend.analyzer import TradeFusionAnalyzer
from backend.backtester import Backtester
from backend.market_schedule import get_market_status, get_asset_category
from backend.position_sizing import calculate_position_size, get_symbol_category
from backend.performance.tracker import PerformanceTracker


def create_mock_real_candles(n_bars: int = 100, trend: str = "bullish") -> pd.DataFrame:
    """Helper to generate deterministic candle structures for testing analysis pipelines."""
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=n_bars, freq="1h")
    base_price = 50000.0
    
    if trend == "bullish":
        drift = np.linspace(0, 5000, n_bars)
    elif trend == "bearish":
        drift = np.linspace(0, -5000, n_bars)
    else:
        drift = np.sin(np.linspace(0, 10, n_bars)) * 100

    close = base_price + drift
    high = close + 100.0
    low = close - 100.0
    open_ = close - 20.0
    volume = np.full(n_bars, 1000.0)

    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)
    df.index.name = "timestamp"
    df.attrs["data_source"] = "Test Harness"
    df.attrs["latest_candle"] = dates[-1]
    return df


class TestTradeFusionCore(unittest.TestCase):

    def test_01_no_synthetic_data(self):
        """P0 Rule: Ensure synthetic generators are eliminated."""
        import backend.data.fetcher as fetcher
        self.assertFalse(hasattr(fetcher, "generate_synthetic_data"), "generate_synthetic_data must not exist")
        
        import inspect
        sig = inspect.signature(fetcher.get_data)
        self.assertNotIn("use_synthetic", sig.parameters, "use_synthetic param must not be in get_data")

    def test_02_resolution_mapping(self):
        """Ensure interval-to-resolution mapping is correct for Twelve Data & Finnhub."""
        self.assertEqual(_FINNHUB_RESOLUTION_MAP["1h"], "60")
        self.assertEqual(_FINNHUB_RESOLUTION_MAP["1d"], "D")
        self.assertEqual(_TWELVE_INTERVAL_MAP["1h"], "1h")
        self.assertEqual(_TWELVE_INTERVAL_MAP["15m"], "15min")

    def test_03_invalid_empty_data_rejected(self):
        """P0 Rule: Empty or invalid data must never be analyzed."""
        analyzer = TradeFusionAnalyzer()
        res_none = analyzer.analyze(None)
        self.assertIn("error", res_none)
        self.assertIn("DATA UNAVAILABLE", res_none["error"])

        empty_df = pd.DataFrame()
        res_empty = analyzer.analyze(empty_df)
        self.assertIn("error", res_empty)

        small_df = create_mock_real_candles(n_bars=20)
        res_small = analyzer.analyze(small_df)
        self.assertIn("error", res_small)

    def test_04_data_unavailable_vs_no_trade(self):
        """P0 Rule: DATA UNAVAILABLE is distinct from NO TRADE."""
        analyzer = TradeFusionAnalyzer(risk_mode="high")
        # Ranging data with conflicting indicators produces NO TRADE
        ranging_df = create_mock_real_candles(n_bars=100, trend="ranging")
        res = analyzer.analyze(ranging_df, symbol="BTC-USD")
        
        self.assertNotIn("error", res)
        # Should complete analysis and produce signal (either NO TRADE or valid setup)
        self.assertIn("signal", res)
        self.assertIn("confidence", res)
        self.assertIn("price", res)
        self.assertIn("explanation", res)

    def test_05_trade_setup_levels(self):
        """P1 Rule: When BUY/SELL is generated, Entry, SL, TP, R:R and Review Time exist."""
        analyzer = TradeFusionAnalyzer(risk_mode="low")
        df = create_mock_real_candles(n_bars=250, trend="bullish")
        res = analyzer.analyze(df, symbol="BTC-USD", timeframe="1h")

        if res["signal"] in ("BUY", "SELL"):
            setup = res.get("trade_setup")
            self.assertIsNotNone(setup, "trade_setup must exist for BUY/SELL")
            self.assertIn("entry", setup)
            self.assertIn("stop_loss", setup)
            self.assertIn("take_profit", setup)
            self.assertIn("risk_reward", setup)
            self.assertIn("review_time", setup)
            self.assertEqual(setup["execution_type"], "SIMULATED")
            if res["signal"] == "BUY":
                self.assertGreater(setup["take_profit"], setup["entry"])
                self.assertLess(setup["stop_loss"], setup["entry"])

    def test_06_market_schedule_detection(self):
        """P1 Rule: Asset-specific schedules for Crypto, Stocks, Forex, Metals."""
        # Crypto is always 24/7 open
        crypto_status = get_market_status("BTC-USD")
        self.assertTrue(crypto_status["is_open"])
        self.assertEqual(crypto_status["category"], "Crypto")

        # Category mapping
        self.assertEqual(get_asset_category("AAPL"), "stock")
        self.assertEqual(get_asset_category("EURUSD=X"), "forex")
        self.assertEqual(get_asset_category("GC=F"), "commodity")

        # Saturday check (Weekend)
        saturday_utc = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)  # Saturday
        stock_sat = get_market_status("AAPL", current_time=saturday_utc)
        self.assertFalse(stock_sat["is_open"])
        self.assertEqual(stock_sat["status"], "CLOSED")

        forex_sat = get_market_status("EURUSD=X", current_time=saturday_utc)
        self.assertFalse(forex_sat["is_open"])
        self.assertEqual(forex_sat["status"], "CLOSED")

        # Crypto is still open on Saturday
        crypto_sat = get_market_status("ETH-USD", current_time=saturday_utc)
        self.assertTrue(crypto_sat["is_open"])

    def test_07_position_sizing_asset_specific(self):
        """P2 Rule: Asset-specific position sizing."""
        # 1. Crypto Sizing (coins)
        btc_pos = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=1.0,  # $100 risk
            entry_price=60000.0,
            stop_loss_price=59000.0, # $1,000 stop distance
            take_profit_price=62000.0,
            symbol="BTC-USD",
            max_position_pct=100.0   # Unconstrained allocation
        )
        self.assertEqual(btc_pos["unit"], "Coins")
        self.assertEqual(btc_pos["risk_amount"], 100.0)
        self.assertEqual(btc_pos["quantity"], 0.1)  # 100 / 1000 = 0.1 BTC
        self.assertEqual(btc_pos["risk_reward_ratio"], "1:2.00")
        self.assertEqual(btc_pos["estimated_profit_at_tp"], 200.0)

        # Verify portfolio exposure cap
        btc_capped = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            entry_price=60000.0,
            stop_loss_price=59000.0,
            symbol="BTC-USD",
            max_position_pct=10.0   # Max $1,000 allocated -> 1000/60000 = 0.0167
        )
        self.assertEqual(btc_capped["quantity"], 0.0167)

        # 2. Forex Sizing (standard lots)
        fx_pos = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=1.0,  # $100 risk
            entry_price=1.1000,
            stop_loss_price=1.0950, # 50 pips risk
            take_profit_price=1.1100,
            symbol="EURUSD=X"
        )
        self.assertIn("Lots", fx_pos["unit"])
        self.assertGreater(fx_pos["quantity"], 0.0)

        # 3. Stock Sizing (shares)
        stock_pos = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=1.0,  # $100 risk
            entry_price=200.0,
            stop_loss_price=195.0,  # $5 risk
            take_profit_price=210.0,
            symbol="AAPL",
            max_position_pct=100.0  # Unconstrained: 100 / 5 = 20 shares
        )
        self.assertEqual(stock_pos["unit"], "Shares")
        self.assertEqual(stock_pos["quantity"], 20.0)

        # Capped stock sizing
        stock_capped = calculate_position_size(
            account_balance=10000.0,
            risk_per_trade_pct=1.0,
            entry_price=200.0,
            stop_loss_price=195.0,
            symbol="AAPL",
            max_position_pct=10.0   # $1,000 cap -> 1000 / 200 = 5 shares
        )
        self.assertEqual(stock_capped["quantity"], 5.0)

    def test_08_simulated_trade_monitoring(self):
        """P2 Rule: PerformanceTracker tracks simulated signals and detects TP/SL."""
        tracker = PerformanceTracker()
        mock_analysis = {
            "symbol": "BTC-USD",
            "signal": "BUY",
            "confidence": 75.0,
            "price": 60000.0,
            "risk_mode": "medium",
            "trade_setup": {
                "entry": 60000.0,
                "stop_loss": 59000.0,
                "take_profit": 62000.0,
                "risk_reward": "1:2.00",
                "review_time": "2026-10-08 22:00 UTC",
                "execution_type": "SIMULATED"
            }
        }
        sig = tracker.add_signal(mock_analysis)
        self.assertEqual(sig["status"], "open")
        self.assertEqual(sig["execution_type"], "SIMULATED")

        # Test TP Detection
        events = tracker.check_open_positions({"BTC-USD": 62500.0})
        self.assertTrue(any(e["id"] == sig["id"] for e in events), "TP should be triggered at 62500")

    def test_09_backtester_simulation(self):
        """P3 Rule: Backtester executes cleanly and returns simulated performance metrics."""
        df = create_mock_real_candles(n_bars=200, trend="bullish")
        bt = Backtester(risk_mode="medium", take_profit_atr=2.5, stop_loss_atr=1.2)
        res = bt.run(df, symbol="BTC-USD")
        self.assertIsNotNone(res)
        self.assertIsInstance(res.total_trades, int)
        self.assertIsInstance(res.win_rate, float)
        self.assertIsInstance(res.total_pnl_pct, float)


if __name__ == "__main__":
    unittest.main()
