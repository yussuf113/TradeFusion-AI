"""
TradeFusion AI - Backtesting Engine
Features: cooldown, trailing stops, configurable TP/SL
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from dataclasses import dataclass, field

from backend.indicators.core import compute_all_indicators
from backend.confidence.engine import ConfidenceEngine


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    side: str
    entry_price: float
    exit_price: Optional[float]
    confidence: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exited: bool = False
    # trailing state
    peak_price: float = 0.0
    current_sl: float = 0.0


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
        take_profit_atr: float = 2.5,
        stop_loss_atr: float = 1.2,
        min_confidence: float = None,
        cooldown_bars: int = 6,
        use_trailing: bool = True,
        trailing_atr: float = 1.0,
        trailing_activate_atr: float = 1.0,
    ):
        self.engine = ConfidenceEngine()
        self.risk_mode = risk_mode
        self.tp_atr = take_profit_atr
        self.sl_atr = stop_loss_atr
        self.min_confidence = min_confidence
        self.cooldown_bars = cooldown_bars
        self.use_trailing = use_trailing
        self.trailing_atr = trailing_atr
        self.trailing_activate_atr = trailing_activate_atr

    def run(self, df: pd.DataFrame, symbol: str = "ASSET") -> BacktestResult:
        df = compute_all_indicators(df).dropna().copy()
        trades: List[Trade] = []
        open_trade: Optional[Trade] = None
        cooldown_until = -1
        peak = 0.0
        max_dd = 0.0
        equity_pnl = 0.0

        for i in range(1, len(df)):
            row = df.iloc[i]
            ts = df.index[i]
            atr = float(row["atr"]) if not pd.isna(row["atr"]) else 0.0

            if open_trade and not open_trade.exited:
                price_high = float(row["high"])
                price_low = float(row["low"])
                close = float(row["close"])

                if open_trade.side == "BUY":
                    # Update peak for trailing
                    if price_high > open_trade.peak_price:
                        open_trade.peak_price = price_high

                    # Fixed TP
                    tp = open_trade.entry_price + self.tp_atr * atr
                    # Initial SL
                    initial_sl = open_trade.entry_price - self.sl_atr * atr

                    # Trailing stop: activate after price moves in favor by trailing_activate_atr
                    if self.use_trailing and atr > 0:
                        favor = open_trade.peak_price - open_trade.entry_price
                        if favor >= self.trailing_activate_atr * atr:
                            trail_sl = open_trade.peak_price - self.trailing_atr * atr
                            open_trade.current_sl = max(open_trade.current_sl, trail_sl, initial_sl)
                        else:
                            open_trade.current_sl = max(open_trade.current_sl, initial_sl)
                    else:
                        open_trade.current_sl = initial_sl

                    if price_high >= tp:
                        open_trade.exit_price = tp
                        open_trade.exit_time = ts
                        open_trade.exited = True
                    elif price_low <= open_trade.current_sl:
                        open_trade.exit_price = open_trade.current_sl
                        open_trade.exit_time = ts
                        open_trade.exited = True

                else:  # SELL
                    if open_trade.peak_price == 0 or price_low < open_trade.peak_price:
                        open_trade.peak_price = price_low if open_trade.peak_price == 0 else min(open_trade.peak_price, price_low)

                    tp = open_trade.entry_price - self.tp_atr * atr
                    initial_sl = open_trade.entry_price + self.sl_atr * atr

                    if self.use_trailing and atr > 0:
                        favor = open_trade.entry_price - open_trade.peak_price
                        if favor >= self.trailing_activate_atr * atr:
                            trail_sl = open_trade.peak_price + self.trailing_atr * atr
                            open_trade.current_sl = min(open_trade.current_sl or initial_sl, trail_sl, initial_sl)
                        else:
                            open_trade.current_sl = initial_sl
                    else:
                        open_trade.current_sl = initial_sl

                    if price_low <= tp:
                        open_trade.exit_price = tp
                        open_trade.exit_time = ts
                        open_trade.exited = True
                    elif price_high >= open_trade.current_sl:
                        open_trade.exit_price = open_trade.current_sl
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
                    cooldown_until = i + self.cooldown_bars

            if open_trade is None and i >= cooldown_until:
                result = self.engine.evaluate(row, risk_mode=self.risk_mode)
                conf_ok = (self.min_confidence is None) or (result["confidence"] >= self.min_confidence)
                if conf_ok and result["signal"] in ("BUY", "SELL"):
                    entry = float(row["close"])
                    open_trade = Trade(
                        entry_time=ts,
                        exit_time=None,
                        side=result["signal"],
                        entry_price=entry,
                        exit_price=None,
                        confidence=result["confidence"],
                        peak_price=entry,
                        current_sl=0.0,
                    )

            # Equity for drawdown
            closed_pnl = sum(t.pnl_pct for t in trades)
            unrealized = 0.0
            if open_trade and not open_trade.exited:
                if open_trade.side == "BUY":
                    unrealized = (float(row["close"]) - open_trade.entry_price) / open_trade.entry_price * 100
                else:
                    unrealized = (open_trade.entry_price - float(row["close"])) / open_trade.entry_price * 100
            equity_pnl = closed_pnl + unrealized
            peak = max(peak, equity_pnl)
            max_dd = max(max_dd, peak - equity_pnl)

        if open_trade and not open_trade.exited:
            last = df.iloc[-1]
            open_trade.exit_price = float(last["close"])
            open_trade.exit_time = df.index[-1]
            open_trade.exited = True
            if open_trade.side == "BUY":
                open_trade.pnl_pct = (open_trade.exit_price - open_trade.entry_price) / open_trade.entry_price * 100
            else:
                open_trade.pnl_pct = (open_trade.entry_price - open_trade.exit_price) / open_trade.entry_price * 100
            open_trade.pnl = open_trade.pnl_pct
            trades.append(open_trade)

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
            result.avg_win = float(np.mean(wins)) if wins else 0.0
            result.avg_loss = float(np.mean(losses)) if losses else 0.0
            gp = sum(wins) if wins else 0.0
            gl = abs(sum(losses)) if losses else 0.0
            result.profit_factor = (gp / gl) if gl > 0 else float("inf")
            result.max_drawdown = max_dd
        return result


def print_backtest_report(result: BacktestResult, symbol: str = "ASSET"):
    print("\n" + "=" * 55)
    print(f" BACKTEST REPORT — {symbol}")
    print("=" * 55)
    print(f"Total Trades     : {result.total_trades}")
    print(f"Wins / Losses    : {result.wins} / {result.losses}")
    print(f"Win Rate         : {result.win_rate:.1f}%")
    print(f"Total PnL        : {result.total_pnl_pct:+.2f}%")
    print(f"Average Win      : {result.avg_win:+.2f}%")
    print(f"Average Loss     : {result.avg_loss:+.2f}%")
    print(f"Profit Factor    : {result.profit_factor:.2f}")
    print(f"Max Drawdown     : {result.max_drawdown:.2f}%")
    print("=" * 55)
    if result.trades:
        print("\nLast 10 trades:")
        for t in result.trades[-10:]:
            print(f"  {t.side:4} | Entry {t.entry_price:.4f} → Exit {t.exit_price:.4f} | "
                  f"PnL {t.pnl_pct:+.2f}% | Conf {t.confidence:.0f}%")
