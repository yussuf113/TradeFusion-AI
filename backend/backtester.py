"""
TradeFusion AI - Backtesting Engine
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from backend.indicators.core import compute_all_indicators
from backend.confidence.engine import ConfidenceEngine
from backend.structure.analyzer import detect_structure


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    side: str                  # "BUY" or "SELL"
    entry_price: float
    exit_price: Optional[float]
    confidence: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exited: bool = False


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0


class Backtester:
    def __init__(
        self,
        risk_mode: str = "medium",
        take_profit_atr: float = 2.0,
        stop_loss_atr: float = 1.2,
        min_confidence: float = None
    ):
        self.engine = ConfidenceEngine()
        self.risk_mode = risk_mode
        self.tp_atr = take_profit_atr
        self.sl_atr = stop_loss_atr
        self.min_confidence = min_confidence

    def run(self, df: pd.DataFrame, symbol: str = "ASSET") -> BacktestResult:
        df = compute_all_indicators(df)
        df = df.dropna().copy()

        trades: List[Trade] = []
        open_trade: Optional[Trade] = None

        equity = [0.0]
        peak = 0.0
        max_dd = 0.0

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            ts = df.index[i]

            # Manage open trade
            if open_trade and not open_trade.exited:
                atr = row["atr"]
                if open_trade.side == "BUY":
                    tp = open_trade.entry_price + self.tp_atr * atr
                    sl = open_trade.entry_price - self.sl_atr * atr
                    if row["high"] >= tp:
                        open_trade.exit_price = tp
                        open_trade.exit_time = ts
                        open_trade.exited = True
                    elif row["low"] <= sl:
                        open_trade.exit_price = sl
                        open_trade.exit_time = ts
                        open_trade.exited = True
                else:  # SELL
                    tp = open_trade.entry_price - self.tp_atr * atr
                    sl = open_trade.entry_price + self.sl_atr * atr
                    if row["low"] <= tp:
                        open_trade.exit_price = tp
                        open_trade.exit_time = ts
                        open_trade.exited = True
                    elif row["high"] >= sl:
                        open_trade.exit_price = sl
                        open_trade.exit_time = ts
                        open_trade.exited = True

                if open_trade.exited:
                    if open_trade.side == "BUY":
                        open_trade.pnl_pct = (open_trade.exit_price - open_trade.entry_price) / open_trade.entry_price * 100
                    else:
                        open_trade.pnl_pct = (open_trade.entry_price - open_trade.exit_price) / open_trade.entry_price * 100
                    open_trade.pnl = open_trade.pnl_pct
                    trades.append(open_trade)
                    open_trade = None

            # Generate new signal only if flat
            if open_trade is None:
                result = self.engine.evaluate(row, risk_mode=self.risk_mode)

                if self.min_confidence and result["confidence"] < self.min_confidence:
                    continue

                if result["signal"] in ("BUY", "SELL"):
                    open_trade = Trade(
                        entry_time=ts,
                        exit_time=None,
                        side=result["signal"],
                        entry_price=row["close"],
                        exit_price=None,
                        confidence=result["confidence"]
                    )

            # Equity curve (simplified)
            current_pnl = sum(t.pnl_pct for t in trades)
            if open_trade and not open_trade.exited:
                # Mark-to-market
                if open_trade.side == "BUY":
                    current_pnl += (row["close"] - open_trade.entry_price) / open_trade.entry_price * 100
                else:
                    current_pnl += (open_trade.entry_price - row["close"]) / open_trade.entry_price * 100

            equity.append(current_pnl)
            peak = max(peak, current_pnl)
            dd = peak - current_pnl
            if dd > max_dd:
                max_dd = dd

        # Close any remaining trade at last price
        if open_trade and not open_trade.exited:
            last = df.iloc[-1]
            open_trade.exit_price = last["close"]
            open_trade.exit_time = df.index[-1]
            open_trade.exited = True
            if open_trade.side == "BUY":
                open_trade.pnl_pct = (open_trade.exit_price - open_trade.entry_price) / open_trade.entry_price * 100
            else:
                open_trade.pnl_pct = (open_trade.entry_price - open_trade.exit_price) / open_trade.entry_price * 100
            open_trade.pnl = open_trade.pnl_pct
            trades.append(open_trade)

        # Statistics
        result = BacktestResult(trades=trades)
        result.total_trades = len(trades)
        if result.total_trades > 0:
            pnls = [t.pnl_pct for t in trades]
            result.wins = sum(1 for p in pnls if p > 0)
            result.losses = sum(1 for p in pnls if p <= 0)
            result.win_rate = (result.wins / result.total_trades) * 100
            result.total_pnl_pct = sum(pnls)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            result.avg_win = np.mean(wins) if wins else 0.0
            result.avg_loss = np.mean(losses) if losses else 0.0
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            result.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
            result.max_drawdown = max_dd

        return result


def print_backtest_report(result: BacktestResult, symbol: str = "ASSET"):
    print("\n" + "="*55)
    print(f" BACKTEST REPORT — {symbol}")
    print("="*55)
    print(f"Total Trades     : {result.total_trades}")
    print(f"Wins / Losses    : {result.wins} / {result.losses}")
    print(f"Win Rate         : {result.win_rate:.1f}%")
    print(f"Total PnL        : {result.total_pnl_pct:+.2f}%")
    print(f"Average Win      : {result.avg_win:+.2f}%")
    print(f"Average Loss     : {result.avg_loss:+.2f}%")
    print(f"Profit Factor    : {result.profit_factor:.2f}")
    print(f"Max Drawdown     : {result.max_drawdown:.2f}%")
    print("="*55)

    if result.trades:
        print("\nLast 10 trades:")
        for t in result.trades[-10:]:
            print(f"  {t.side:4} | Entry {t.entry_price:.4f} → Exit {t.exit_price:.4f} | "
                  f"PnL {t.pnl_pct:+.2f}% | Conf {t.confidence:.0f}%")
