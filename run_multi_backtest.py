#!/usr/bin/env python3
"""TradeFusion AI - Multi-Asset Backtester"""

import backend.config  # auto-loads .env
import argparse
from backend.data.fetcher import get_data
from backend.backtester import Backtester, print_backtest_report

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "GC=F", "EURUSD=X"]


def main():
    parser = argparse.ArgumentParser(description="TradeFusion Multi-Asset Backtest")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--period", default="6mo")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    print("\n🚀 TradeFusion AI — Multi-Asset Backtest")
    print(f"   Assets : {', '.join(args.symbols)}")
    print(f"   Risk   : {args.risk}\n")

    summary = []
    for symbol in args.symbols:
        print(f"\n{'─'*50}\n Testing {symbol}...")
        try:
            df = get_data(symbol, args.period, args.interval, use_synthetic=args.synthetic)
            result = Backtester(risk_mode=args.risk).run(df, symbol=symbol)
            print_backtest_report(result, symbol=symbol)
            summary.append({"symbol": symbol, "trades": result.total_trades, "win_rate": result.win_rate,
                            "pnl": result.total_pnl_pct, "profit_factor": result.profit_factor, "max_dd": result.max_drawdown})
        except Exception as e:
            print(f"  Failed: {e}")

    if summary:
        print("\n" + "="*70)
        print(" MULTI-ASSET SUMMARY")
        print("="*70)
        print(f"{'Symbol':12} {'Trades':>8} {'WinRate':>10} {'PnL%':>10} {'PF':>8} {'MaxDD%':>10}")
        print("-"*70)
        for s in summary:
            print(f"{s['symbol']:12} {s['trades']:8} {s['win_rate']:9.1f}% {s['pnl']:+9.2f}% {s['profit_factor']:8.2f} {s['max_dd']:9.2f}%")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
