"""
TradeFusion AI - Per-asset parameter optimizer
Grid-searches a small set of parameters and picks the best by profit factor / PnL.
"""

from typing import Dict, List, Tuple
import itertools
import pandas as pd

from backend.data.fetcher import get_data
from backend.backtester import Backtester, BacktestResult


# Small focused grid (keeps runtime reasonable)
PARAM_GRID = {
    "risk_mode": ["medium", "low"],
    "take_profit_atr": [2.0, 2.5, 3.0],
    "stop_loss_atr": [1.0, 1.2, 1.5],
    "cooldown_bars": [4, 6, 10],
    "use_trailing": [True, False],
}


def _score(result: BacktestResult) -> float:
    """Higher is better. Prefer profit factor, then PnL, penalize low trade count."""
    if result.total_trades < 8:
        return -999.0
    pf = result.profit_factor if result.profit_factor != float("inf") else 3.0
    # Composite score
    return (pf * 40.0) + (result.total_pnl_pct * 0.5) - (result.max_drawdown * 0.3) + (result.win_rate * 0.2)


def optimize_symbol(
    symbol: str,
    period: str = "6mo",
    interval: str = "1h",
    use_synthetic: bool = False,
    max_combos: int = 80,
) -> Dict:
    df = get_data(symbol, period=period, interval=interval, use_synthetic=use_synthetic)
    keys = list(PARAM_GRID.keys())
    values = [PARAM_GRID[k] for k in keys]
    combos = list(itertools.product(*values))
    # Limit combos for speed
    if len(combos) > max_combos:
        step = max(1, len(combos) // max_combos)
        combos = combos[::step][:max_combos]

    best = None
    best_score = -1e9
    results = []

    for combo in combos:
        params = dict(zip(keys, combo))
        bt = Backtester(
            risk_mode=params["risk_mode"],
            take_profit_atr=params["take_profit_atr"],
            stop_loss_atr=params["stop_loss_atr"],
            cooldown_bars=params["cooldown_bars"],
            use_trailing=params["use_trailing"],
        )
        res = bt.run(df, symbol=symbol)
        sc = _score(res)
        row = {**params, "trades": res.total_trades, "win_rate": round(res.win_rate, 1),
               "pnl": round(res.total_pnl_pct, 2), "pf": round(res.profit_factor, 2),
               "max_dd": round(res.max_drawdown, 2), "score": round(sc, 2)}
        results.append(row)
        if sc > best_score:
            best_score = sc
            best = row

    return {
        "symbol": symbol,
        "best": best,
        "tested": len(results),
        "top5": sorted(results, key=lambda x: x["score"], reverse=True)[:5],
    }


def optimize_many(symbols: List[str], **kwargs) -> Dict[str, Dict]:
    out = {}
    for sym in symbols:
        print(f"\n🔧 Optimizing {sym}...")
        try:
            out[sym] = optimize_symbol(sym, **kwargs)
            b = out[sym]["best"]
            if b:
                print(f"   Best: PF={b['pf']} PnL={b['pnl']:+.1f}% WR={b['win_rate']}% "
                      f"trail={b['use_trailing']} risk={b['risk_mode']} "
                      f"TP={b['take_profit_atr']} SL={b['stop_loss_atr']}")
            else:
                print("   No valid result")
        except Exception as e:
            print(f"   Failed: {e}")
            out[sym] = {"error": str(e)}
    return out
