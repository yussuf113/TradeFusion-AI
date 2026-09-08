#!/usr/bin/env python3
"""
TradeFusion AI - Multi-Asset Scanner
Scans multiple assets and optionally sends Telegram alerts + tracks signals.

Usage:
    python run_scanner.py
    python run_scanner.py --once
    python run_scanner.py --interval 300 --risk medium
"""

import argparse
import time
from datetime import datetime

from backend.data.fetcher import get_data
from backend.analyzer import TradeFusionAnalyzer
from backend.notifications.telegram import TelegramNotifier
from backend.performance.tracker import PerformanceTracker

# Expanded default universe
DEFAULT_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "GC=F",        # Gold
    "SI=F",        # Silver
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AAPL",
    "TSLA",
]


def scan_once(symbols, risk_mode, send_telegram=False, track=True, min_confidence=60.0):
    analyzer = TradeFusionAnalyzer(risk_mode=risk_mode)
    notifier = TelegramNotifier()
    tracker = PerformanceTracker() if track else None

    results = []
    print(f"\n{'='*60}")
    print(f" TradeFusion Scanner — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f" Risk Mode: {risk_mode.upper()} | Assets: {len(symbols)}")
    print(f"{'='*60}\n")

    for symbol in symbols:
        try:
            df = get_data(symbol, period="3mo", interval="1h", use_synthetic=False)
            analysis = analyzer.analyze(df, symbol=symbol)

            signal = analysis["signal"]
            conf = analysis["confidence"]
            price = analysis["price"]

            # Display
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"{emoji} {symbol:12} | {signal:8} | Conf {conf:5.1f}% | Price {price}")

            results.append(analysis)

            # Only act on real signals above threshold
            if signal in ("BUY", "SELL") and conf >= min_confidence:
                if track and tracker:
                    tracker.add_signal(analysis)
                    print(f"   → Tracked signal #{len(tracker.signals)}")

                if send_telegram and notifier.is_configured:
                    notifier.send_signal(analysis)
                    print(f"   → Telegram alert sent")

        except Exception as e:
            print(f"❌ {symbol:12} | Error: {e}")

    # Summary
    buys = [r for r in results if r["signal"] == "BUY"]
    sells = [r for r in results if r["signal"] == "SELL"]
    print(f"\n{'─'*60}")
    print(f" Summary: {len(buys)} BUY | {len(sells)} SELL | {len(results)-len(buys)-len(sells)} NO TRADE")
    print(f"{'─'*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="TradeFusion Multi-Asset Scanner")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--interval", type=int, default=300, help="Seconds between scans (default 300 = 5 min)")
    parser.add_argument("--once", action="store_true", help="Run only one scan and exit")
    parser.add_argument("--telegram", action="store_true", help="Send Telegram alerts for signals")
    parser.add_argument("--no-track", action="store_true", help="Disable signal tracking")
    parser.add_argument("--min-conf", type=float, default=60.0, help="Minimum confidence to alert/track")
    args = parser.parse_args()

    print("🚀 TradeFusion AI Scanner started")
    if args.telegram:
        notifier = TelegramNotifier()
        if notifier.is_configured:
            print("   Telegram: enabled")
        else:
            print("   Telegram: NOT configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")

    while True:
        scan_once(
            symbols=args.symbols,
            risk_mode=args.risk,
            send_telegram=args.telegram,
            track=not args.no_track,
            min_confidence=args.min_conf
        )

        if args.once:
            break

        print(f"Next scan in {args.interval} seconds... (Ctrl+C to stop)")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nScanner stopped.")
            break


if __name__ == "__main__":
    main()
