#!/usr/bin/env python3
"""
TradeFusion AI - Single Snapshot Analysis
Usage:
    python run_analysis.py
    python run_analysis.py --symbol ETH-USD --risk low
"""

import argparse
from backend.data.fetcher import get_data
from backend.analyzer import TradeFusionAnalyzer


def main():
    parser = argparse.ArgumentParser(description="TradeFusion AI Live Analysis")
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--period", default="3mo")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    df = get_data(args.symbol, args.period, args.interval, use_synthetic=args.synthetic)
    analyzer = TradeFusionAnalyzer(risk_mode=args.risk)
    result = analyzer.analyze(df, symbol=args.symbol)

    print("\n" + result["explanation"])
    print(f"\nCurrent Price : {result['price']}")
    print(f"Signal        : {result['signal']} ({result['confidence']}%)")
    print()


if __name__ == "__main__":
    main()
