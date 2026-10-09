#!/usr/bin/env python3
"""TradeFusion AI - Backtest Runner"""

import backend.config  # auto-loads .env
import argparse
from backend.data.fetcher import get_data
from backend.backtester import Backtester, print_backtest_report
from backend.analyzer import TradeFusionAnalyzer


def main():
    parser = argparse.ArgumentParser(description="TradeFusion AI Backtester")
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--period", default="6mo")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--tp", type=float, default=2.0)
    parser.add_argument("--sl", type=float, default=1.2)
    args = parser.parse_args()

    print("\n[*] TradeFusion AI -- Starting Backtest")
    print(f"   Symbol     : {args.symbol}")
    print(f"   Risk Mode  : {args.risk}")
    print(f"   Period     : {args.period} @ {args.interval}")
    print("   [!]   HISTORICAL SIMULATION -- Not real executed trades.\n")

    df = get_data(args.symbol, args.period, args.interval)
    if df is None:
        print(f"\n[SELL] DATA UNAVAILABLE -- all providers failed for {args.symbol} ({args.interval}).")
        print("Cannot run backtest without real historical data.\n")
        return

    data_source = df.attrs.get("data_source", "Unknown")
    print(f"   Data Source: {data_source} | Bars: {len(df)}")

    bt = Backtester(risk_mode=args.risk, take_profit_atr=args.tp, stop_loss_atr=args.sl)
    result = bt.run(df, symbol=args.symbol)
    print_backtest_report(result, symbol=args.symbol)

    print("\n[#] Latest Market Snapshot (Sentinel)")
    analyzer = TradeFusionAnalyzer(risk_mode=args.risk)
    snapshot = analyzer.analyze(df, symbol=args.symbol)
    if "error" not in snapshot:
        print(snapshot["explanation"])
    else:
        print(f"[!]   {snapshot['error']}")
    print("\n[OK] Backtest complete.\n")


if __name__ == "__main__":
    main()
