#!/usr/bin/env python3
"""Optimize parameters per asset."""

import backend.config
import argparse
import json
from pathlib import Path
from backend.optimize import optimize_many

DEFAULT = ["BTC-USD", "ETH-USD", "GC=F", "EURUSD=X"]


def main():
    parser = argparse.ArgumentParser(description="TradeFusion per-asset optimizer")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT)
    parser.add_argument("--period", default="6mo")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    print("🚀 TradeFusion Parameter Optimizer")
    results = optimize_many(args.symbols, period=args.period, use_synthetic=args.synthetic)

    # Save best params
    best_map = {}
    for sym, data in results.items():
        if data.get("best"):
            best_map[sym] = data["best"]

    out_path = Path("data/best_params.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(best_map, f, indent=2)
    print(f"\n✅ Saved best params → {out_path}")

    print("\n" + "=" * 60)
    print(" BEST PARAMETERS BY ASSET")
    print("=" * 60)
    for sym, b in best_map.items():
        print(f"{sym:12} | risk={b['risk_mode']:6} TP={b['take_profit_atr']} SL={b['stop_loss_atr']} "
              f"trail={str(b['use_trailing']):5} | PF={b['pf']} PnL={b['pnl']:+.1f}% WR={b['win_rate']}%")
    print()


if __name__ == "__main__":
    main()
