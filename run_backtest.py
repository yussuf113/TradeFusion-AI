#!/usr/bin/env python3
"""
TradeFusion AI - Backtest Runner
Usage:
    python run_backtest.py
    python run_backtest.py --symbol BTC-USD --risk medium
    python run_backtest.py --synthetic
"""

import argparse
from backend.data.fetcher import get_data
from backend.backtester import Backtester, print_backtest_report
from backend.analyzer import TradeFusionAnalyzer


def main():
    parser = argparse.ArgumentParser(description="TradeFusion AI Backtester")
    parser.add_argument("--symbol", default="BTC-USD", help="Symbol (yfinance format, e.g. BTC-USD, ETH-USD, GC=F, EURUSD=X)")
    parser.add_argument("--period", default="6mo", help="Data period (e.g. 3mo, 6mo, 1y)")
    parser.add_argument("--interval", default="1h", help="Bar interval")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"], help="Risk mode")
    parser.add_argument("--synthetic", action="store_true", help="Force synthetic data")
    parser.add_argument("--tp", type=float, default=2.0, help="Take profit in ATR multiples")
    parser.add_argument("--sl", type=float, default=1.2, help="Stop loss in ATR multiples")
    args = parser.parse_args()

    print("\n🚀 TradeFusion AI — Starting Backtest")
    print(f"   Symbol     : {args.symbol}")
    print(f"   Risk Mode  : {args.risk}")
    print(f"   Period     : {args.period} @ {args.interval}")

    # Load data
    df = get_data(
        symbol=args.symbol,
        period=args.period,
        interval=args.interval,
        use_synthetic=args.synthetic
    )

    print(f"   Bars loaded: {len(df)}")

    # Run backtest
    bt = Backtester(
        risk_mode=args.risk,
        take_profit_atr=args.tp,
        stop_loss_atr=args.sl
    )
    result = bt.run(df, symbol=args.symbol)
    print_backtest_report(result, symbol=args.symbol)

    # Also show latest live-style analysis
    print("\n📊 Latest Market Snapshot (Sentinel)")
    analyzer = TradeFusionAnalyzer(risk_mode=args.risk)
    snapshot = analyzer.analyze(df, symbol=args.symbol)
    print(snapshot["explanation"])

    print("\n✅ Backtest complete.\n")


if __name__ == "__main__":
    main()
