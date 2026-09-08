#!/usr/bin/env python3
"""
TradeFusion AI - Multi-Asset Scanner
Optional: auto-place paper Binance orders on signals.
"""

import backend.config
import argparse
import time
from datetime import datetime

from backend.data.fetcher import get_data
from backend.analyzer import TradeFusionAnalyzer
from backend.notifications.telegram import TelegramNotifier
from backend.performance.tracker import PerformanceTracker
from backend.execution.binance_exec import BinanceExecutor

DEFAULT_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "GC=F", "SI=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X",
    "AAPL", "TSLA",
]


def scan_once(symbols, risk_mode, send_telegram=False, track=True, min_confidence=68.0,
              paper_trade=False, executor=None):
    analyzer = TradeFusionAnalyzer(risk_mode=risk_mode)
    notifier = TelegramNotifier()
    tracker = PerformanceTracker() if track else None
    results = []

    print(f"\n{'='*60}")
    print(f" TradeFusion Scanner — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f" Risk: {risk_mode.upper()} | Assets: {len(symbols)} | Paper: {paper_trade}")
    print(f"{'='*60}\n")

    for symbol in symbols:
        try:
            df = get_data(symbol, period="3mo", interval="1h", use_synthetic=False)
            analysis = analyzer.analyze(df, symbol=symbol)
            signal, conf, price = analysis["signal"], analysis["confidence"], analysis["price"]
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"{emoji} {symbol:12} | {signal:8} | Conf {conf:5.1f}% | Price {price}")
            results.append(analysis)

            if signal in ("BUY", "SELL") and conf >= min_confidence:
                if track and tracker:
                    tracker.add_signal(analysis)
                    print(f"   → Tracked")
                if send_telegram and notifier.is_configured:
                    notifier.send_signal(analysis)
                    print(f"   → Telegram sent")
                if paper_trade and executor:
                    order = executor.place_order(symbol, signal, conf, price=price)
                    print(f"   → Paper order: {order.get('status', order)}")
        except Exception as e:
            print(f"❌ {symbol:12} | Error: {e}")

    buys = sum(1 for r in results if r["signal"] == "BUY")
    sells = sum(1 for r in results if r["signal"] == "SELL")
    print(f"\n{'─'*60}")
    print(f" Summary: {buys} BUY | {sells} SELL | {len(results)-buys-sells} NO TRADE")
    if paper_trade and executor:
        print(f" Paper trades so far: {len(executor.get_paper_trades())}")
    print(f"{'─'*60}\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="TradeFusion Multi-Asset Scanner")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--telegram", action="store_true")
    parser.add_argument("--no-track", action="store_true")
    parser.add_argument("--min-conf", type=float, default=68.0)
    parser.add_argument("--paper", action="store_true", help="Auto-place paper Binance orders on signals")
    args = parser.parse_args()

    print("🚀 TradeFusion AI Scanner started")
    executor = BinanceExecutor(live=False) if args.paper else None
    if args.paper:
        print("   Paper Binance orders: ON")
    if args.telegram:
        print("   Telegram:", "ON" if TelegramNotifier().is_configured else "not configured")

    while True:
        scan_once(
            args.symbols, args.risk, args.telegram, not args.no_track,
            args.min_conf, paper_trade=args.paper, executor=executor,
        )
        if args.once:
            break
        print(f"Next scan in {args.interval}s... (Ctrl+C to stop)")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nScanner stopped.")
            if executor:
                print(f"Total paper trades: {len(executor.get_paper_trades())}")
            break


if __name__ == "__main__":
    main()
