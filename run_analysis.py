#!/usr/bin/env python3
"""TradeFusion AI - Single Snapshot Analysis"""

import backend.config  # auto-loads .env
import argparse
from backend.data.fetcher import get_data
from backend.analyzer import TradeFusionAnalyzer


def main():
    parser = argparse.ArgumentParser(description="TradeFusion AI Live Analysis")
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    args = parser.parse_args()

    df = get_data(args.symbol, args.period, args.interval)
    if df is None:
        print(f"\n[SELL] DATA UNAVAILABLE -- all providers failed for {args.symbol} ({args.interval}).")
        print("Check your API keys in .env and network connectivity.\n")
        return

    analyzer = TradeFusionAnalyzer(risk_mode=args.risk)
    result = analyzer.analyze(df, symbol=args.symbol)

    if "error" in result:
        print(f"\n[!]   Analysis error: {result['error']}\n")
        return

    print("\n" + result["explanation"])
    print(f"\nCurrent Price : {result['price']}")
    print(f"Signal        : {result['signal']} ({result['confidence']}%)\n")


if __name__ == "__main__":
    main()
