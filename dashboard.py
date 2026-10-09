#!/usr/bin/env python3
"""TradeFusion AI - Streamlit Dashboard"""

import backend.config  # auto-loads .env
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.data.fetcher import get_data
from backend.indicators.core import compute_all_indicators
from backend.analyzer import TradeFusionAnalyzer
from backend.backtester import Backtester
from backend.notifications.telegram import TelegramNotifier
from backend.performance.tracker import PerformanceTracker
from backend.market_schedule import get_market_status
from backend.position_sizing import calculate_position_size
from backend.personal_trades import PersonalTradeManager
from backend.user_settings import (
    load_user_settings,
    save_user_settings,
    VALID_SYMBOLS,
    VALID_INTERVALS,
    VALID_PERIODS,
    VALID_RISK_MODES,
)

st.set_page_config(page_title="TradeFusion AI", page_icon="[#]", layout="wide")
st.title("TradeFusion AI - Trading Intelligence & Paper Trading")
st.caption("Real Market Data Analysis * Multi-Indicator Strategy * Simulated & Personal Paper Execution")

# --------------------------------------------------
# Sidebar - Settings & Persistent Selection
# --------------------------------------------------
saved_settings = load_user_settings()

sym_idx = VALID_SYMBOLS.index(saved_settings["symbol"]) if saved_settings["symbol"] in VALID_SYMBOLS else 0
int_idx = VALID_INTERVALS.index(saved_settings["interval"]) if saved_settings["interval"] in VALID_INTERVALS else 3
period_idx = VALID_PERIODS.index(saved_settings["period"]) if saved_settings["period"] in VALID_PERIODS else 1
risk_idx = VALID_RISK_MODES.index(saved_settings["risk_mode"]) if saved_settings["risk_mode"] in VALID_RISK_MODES else 1

with st.sidebar:
    st.header("Market Selection")
    symbol = st.selectbox("Asset", VALID_SYMBOLS, index=sym_idx)
    risk_mode = st.selectbox("Strategy Risk Mode", VALID_RISK_MODES, index=risk_idx)
    period = st.selectbox("Historical Period", VALID_PERIODS, index=period_idx)
    interval = st.selectbox("Timeframe (Interval)", VALID_INTERVALS, index=int_idx)

    st.divider()
    st.subheader("Position Sizing Parameters")
    account_balance = st.number_input(
        "Account Balance ($)",
        min_value=100.0,
        value=float(saved_settings.get("account_balance", 10000.0)),
        step=500.0,
    )
    risk_pct = st.slider(
        "Risk Per Trade (%)",
        min_value=0.25,
        max_value=5.0,
        value=float(saved_settings.get("risk_pct", 1.0)),
        step=0.25,
    )
    max_pos_pct = st.slider(
        "Max Portfolio Exposure (%)",
        min_value=1.0,
        max_value=30.0,
        value=float(saved_settings.get("max_pos_pct", 10.0)),
        step=1.0,
    )

    # Persist selection changes (changing selections never creates a trade)
    if (
        symbol != saved_settings.get("symbol")
        or interval != saved_settings.get("interval")
        or period != saved_settings.get("period")
        or risk_mode != saved_settings.get("risk_mode")
        or account_balance != saved_settings.get("account_balance")
        or risk_pct != saved_settings.get("risk_pct")
        or max_pos_pct != saved_settings.get("max_pos_pct")
    ):
        save_user_settings({
            "symbol": symbol,
            "interval": interval,
            "period": period,
            "risk_mode": risk_mode,
            "account_balance": account_balance,
            "risk_pct": risk_pct,
            "max_pos_pct": max_pos_pct,
        })

    st.divider()
    refresh_clicked = st.button("Refresh Market Data")

    st.divider()
    st.subheader("Telegram Notifications")
    send_tg = st.button("Send Signal to Telegram")

# --------------------------------------------------
# Session state: Cache market data for explicit refresh
# --------------------------------------------------
if (
    "df" not in st.session_state
    or refresh_clicked
    or st.session_state.get("current_symbol") != symbol
    or st.session_state.get("current_interval") != interval
    or st.session_state.get("current_period") != period
):
    with st.spinner("Fetching real market data..."):
        st.session_state.df = get_data(symbol, period=period, interval=interval)
        st.session_state.fetch_time = datetime.now(timezone.utc)
        st.session_state.current_symbol = symbol
        st.session_state.current_interval = interval
        st.session_state.current_period = period

df = st.session_state.df
fetch_time = st.session_state.get("fetch_time")

# Check market session schedule
market_info = get_market_status(symbol)

# --------------------------------------------------
# Top Banner: Market Status & Freshness Header
# --------------------------------------------------
col_stat1, col_stat2 = st.columns([1, 2])

with col_stat1:
    if market_info["is_open"]:
        st.success(f"MARKET OPEN: {market_info['category']} ({market_info['session']})")
    else:
        st.error(f"MARKET CLOSED: {market_info['category']} ({market_info['session']})")
        st.caption("Note: Charts and analysis reflect the last available trading session.")

with col_stat2:
    if df is not None and len(df) > 0:
        data_source = df.attrs.get("data_source", "Unknown")
        latest_candle = df.attrs.get("latest_candle", df.index[-1])
        now_utc = datetime.now(timezone.utc)
        
        lc_dt = pd.to_datetime(latest_candle)
        if lc_dt.tzinfo is None:
            lc_dt = lc_dt.tz_localize(timezone.utc)
        else:
            lc_dt = lc_dt.tz_convert(timezone.utc)
        
        age = now_utc - lc_dt
        hours = int(age.total_seconds() // 3600)
        minutes = int((age.total_seconds() % 3600) // 60)
        age_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        sub_c1, sub_c2, sub_c3, sub_c4 = st.columns(4)
        sub_c1.metric("Data Source", data_source)
        sub_c2.metric("Latest Candle", lc_dt.strftime("%b %d, %H:%M UTC"))
        sub_c3.metric("Data Age", age_str)
        sub_c4.metric("Timeframe", interval)
    else:
        st.warning("Data status: Not available")

# --------------------------------------------------
# Monitor Personal Paper Trades on Active Price
# --------------------------------------------------
pt_manager = PersonalTradeManager()
if df is not None and len(df) > 0:
    current_px = float(df.iloc[-1]["close"])
    closed_triggers = pt_manager.check_and_update_trades({symbol: current_px})
    if closed_triggers:
        for ct in closed_triggers:
            st.toast(f"Paper Trade {ct['trade_id']} triggered {ct['exit_reason']} at ${ct['exit_price']:,.4f} ({ct['pnl_pct']:+.2f}%)!")

# --------------------------------------------------
# Tabs: Analysis / Backtest / Personal Trades / System Signals
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Analysis & Live Setup",
    "Backtest (Historical Simulation)",
    "Personal Trade History",
    "System Signals Tracker",
])

# ==================================================
# TAB 1 - Analysis & Live Trade Setup
# ==================================================
with tab1:
    # 1. DATA UNAVAILABLE GUARD
    if df is None:
        st.error("DATA UNAVAILABLE")
        st.markdown(
            f"""
### Unable to obtain reliable real market data for **{symbol}** ({interval}).

The system queried all active data providers in priority order:
1. **Twelve Data** - check API key / quota in `.env`
2. **Finnhub** - check API key / quota in `.env`
3. **yfinance** - check network connectivity

**Zero synthetic/fake data is permitted.**  
Please check your connection and press **Refresh Market Data** in the sidebar.
"""
        )
        st.stop()

    # 2. RUN TECHNICAL ANALYSIS
    analyzer = TradeFusionAnalyzer(risk_mode=risk_mode)
    analysis = analyzer.analyze(df, symbol=symbol, timeframe=interval)

    if "error" in analysis:
        st.warning(f"Analysis Warning: {analysis['error']}")
        st.info("Insufficient historical candles. Try selecting a longer historical period in the sidebar.")
        st.stop()

    # 3. METRICS ROW
    df_ind = compute_all_indicators(df).dropna()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Price", f"${analysis['price']:,.4f}" if analysis['price'] < 10 else f"${analysis['price']:,.2f}")
    m2.metric("Signal", analysis["signal"])
    m3.metric("Confidence", f"{analysis['confidence']}%")
    m4.metric("Bullish Score", f"{analysis['bullish_score']}%")
    m5.metric("Bearish Score", f"{analysis['bearish_score']}%")

    st.markdown("---")

    # 4. TRADE SETUP / NO TRADE DISPLAY
    signal = analysis["signal"]
    setup = analysis.get("trade_setup")

    if signal in ("BUY", "SELL") and setup:
        st.subheader(f"Analytical Setup: {signal}")
        
        # Position Sizing Calculation
        pos_sizing = calculate_position_size(
            account_balance=account_balance,
            risk_per_trade_pct=risk_pct,
            entry_price=setup["entry"],
            stop_loss_price=setup["stop_loss"],
            take_profit_price=setup["take_profit"],
            symbol=symbol,
            max_position_pct=max_pos_pct,
        )

        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.info(
                f"""
**Trade Levels (Analytical)**
- **Direction:** {signal}
- **Entry:** {setup['entry']}
- **Stop Loss:** {setup['stop_loss']}
- **Take Profit:** {setup['take_profit']}
- **Risk / Reward:** {setup['risk_reward']}
"""
            )

        with s_col2:
            st.info(
                f"""
**Timing & Horizons**
- **Timeframe:** {setup['timeframe']}
- **Signal Time:** {setup['signal_time']}
- **Review Reminder:** {setup['review_time']}
- **ATR (14):** {setup['atr']}
"""
            )

        with s_col3:
            st.info(
                f"""
**Position Sizing ({pos_sizing['category']})**
- **Size:** {pos_sizing['position_size']} {pos_sizing['unit']}
- **Risk Amount:** ${pos_sizing['risk_amount']:,.2f} ({risk_pct}%)
- **Est. Loss at SL:** -${pos_sizing['estimated_loss_at_sl']:,.2f}
- **Est. Profit at TP:** +${pos_sizing['estimated_profit_at_tp']:,.2f}
"""
            )

        st.caption("ANALYTICAL SETUP: These are simulated risk levels. No broker order is placed.")

        # STRICT PERSONAL TRADE CREATION CONTROL
        st.markdown("---")
        st.subheader("Personal Paper Trade Entry")
        st.caption("Only clicking ENTER TRADE will record a trade in your personal history. Unaccepted signals are never traded.")
        
        n_col1, n_col2 = st.columns([2, 1])
        with n_col1:
            user_notes = st.text_input("Trade Notes (optional)", key="pt_notes_input", placeholder="e.g. Trend pullback test")
        with n_col2:
            expiry_hours = st.number_input("Expiry Horizon (hours, 0 = no expiry)", min_value=0.0, value=0.0, step=1.0, key="pt_expiry_input")

        btn_enter = st.button("ENTER TRADE (Personal Paper Trade)", key="btn_enter_trade", type="primary")
        if btn_enter:
            ok, msg, created_pt = pt_manager.create_personal_trade(
                analysis=analysis,
                position_sizing=pos_sizing,
                user_notes=user_notes,
                expiry_hours=expiry_hours if expiry_hours > 0 else None,
            )
            if ok:
                st.success(f"{msg} Recorded in Personal Trade History.")
                st.rerun()
            else:
                st.warning(f"{msg}")

    else:
        st.subheader("NO TRADE - Market Monitoring Active")
        st.info(
            f"""
**Current Market State:**
Real market data is available and technical analysis completed.
Current conditions produce a confidence of **{analysis['confidence']}%**, which does not satisfy the **{risk_mode.upper()}** threshold requirement.
Indicators are currently in conflict or lack sufficient directional agreement.

**ENTER TRADE is disabled** because no high-probability setup exists.
"""
        )

    # 5. CHART VISUALIZATION
    if not df_ind.empty:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.55, 0.25, 0.20],
            subplot_titles=("Price + Moving Averages + Bollinger Bands", "RSI (14)", "MACD (12, 26, 9)"),
        )
        fig.add_trace(go.Candlestick(
            x=df_ind.index, open=df_ind["open"], high=df_ind["high"],
            low=df_ind["low"], close=df_ind["close"], name="Price",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["ema_50"],  name="EMA 50",  line=dict(width=1, color="cyan")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["ema_200"], name="EMA 200", line=dict(width=1, color="yellow")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_upper"], name="BB Upper", line=dict(width=1, dash="dot", color="grey")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_lower"], name="BB Lower", line=dict(width=1, dash="dot", color="grey")), row=1, col=1)

        # Draw SL / TP lines if a valid setup exists
        if setup:
            fig.add_hline(y=setup["take_profit"], line_dash="dash", line_color="green", annotation_text="Take Profit", row=1, col=1)
            fig.add_hline(y=setup["stop_loss"], line_dash="dash", line_color="red", annotation_text="Stop Loss", row=1, col=1)

        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["rsi"], name="RSI", line=dict(color="purple")), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd"], name="MACD", line=dict(color="blue")), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd_signal"], name="Signal", line=dict(color="orange")), row=3, col=1)
        fig.update_layout(height=750, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    # 6. SENTINEL EXPLANATION
    st.subheader("Sentinel Strategy Analysis")
    st.code(analysis["explanation"], language=None)


# ==================================================
# TAB 2 - Backtest (Historical Simulation)
# ==================================================
with tab2:
    st.subheader("Strategy Backtest Engine")
    st.warning("HISTORICAL SIMULATION -- NOT YOUR PERSONAL TRADES. These trades were simulated on historical candles, not executed by you.")

    if df is None:
        st.error("DATA UNAVAILABLE - Cannot execute backtest without real historical data.")
    else:
        b_c1, b_c2, b_c3 = st.columns(3)
        tp_mult = b_c1.number_input("Take Profit (x ATR)", min_value=1.0, max_value=5.0, value=2.5, step=0.5)
        sl_mult = b_c2.number_input("Stop Loss (x ATR)", min_value=0.5, max_value=3.0, value=1.2, step=0.1)
        use_trail = b_c3.checkbox("Enable Trailing Stop", value=True)

        if st.button("Run Simulation on Real Historical Data"):
            with st.spinner("Simulating strategy on real historical candles..."):
                bt = Backtester(
                    risk_mode=risk_mode,
                    take_profit_atr=tp_mult,
                    stop_loss_atr=sl_mult,
                    use_trailing=use_trail,
                )
                res = bt.run(df, symbol=symbol)

                r1, r2, r3, r4, r5 = st.columns(5)
                r1.metric("Simulated Trades", res.total_trades)
                r2.metric("Wins", res.wins)
                r3.metric("Losses", res.losses)
                r4.metric("Win Rate", f"{res.win_rate:.1f}%")
                r5.metric("Total P/L", f"{res.total_pnl_pct:+.2f}%")

                r6, r7, r8 = st.columns(3)
                r6.metric("Profit Factor", f"{res.profit_factor:.2f}" if res.profit_factor != float("inf") else "N/A")
                r7.metric("Max Drawdown", f"{res.max_drawdown:.2f}%")
                r8.metric("Avg Win / Loss", f"+{res.avg_win:.2f}% / {res.avg_loss:.2f}%")

                if res.trades:
                    st.write("**Simulated Historical Trade Records** (HISTORICAL SIMULATION)")
                    trade_rows = [{
                        "#": i + 1,
                        "Entry Time": t.entry_time,
                        "Exit Time": t.exit_time,
                        "Side": t.side,
                        "Entry": round(t.entry_price, 4),
                        "Exit": round(t.exit_price, 4) if t.exit_price else None,
                        "P/L %": round(t.pnl_pct, 2),
                        "Confidence": f"{t.confidence:.1f}%"
                    } for i, t in enumerate(res.trades)]
                    st.dataframe(pd.DataFrame(trade_rows), use_container_width=True)
                else:
                    st.info("No trades met the strategy confidence threshold during this period.")


# ==================================================
# TAB 3 - Personal Trade History (Paper Trading)
# ==================================================
with tab3:
    st.subheader("Personal Paper Trade History")
    st.caption("Records ONLY trades you explicitly submitted via ENTER TRADE. All trades are paper/simulated trades.")

    pt_summary = pt_manager.summary()
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Total Personal Trades", pt_summary["total_trades"])
    p2.metric("Open Active", pt_summary["open_count"])
    p3.metric("Win Rate", f"{pt_summary['win_rate']}%")
    p4.metric("Realized P/L %", f"{pt_summary['total_pnl_pct']:+.2f}%")
    p5.metric("Realized P/L ($)", f"${pt_summary['total_pnl_amount']:+,.2f}")

    st.markdown("---")
    open_pts = pt_manager.get_open_trades()

    st.subheader(f"Active Paper Trades ({len(open_pts)})")
    if open_pts:
        open_df_rows = []
        for t in open_pts:
            curr_p = t.get("current_price", t["entry_price"])
            entry_p = t["entry_price"]
            if t["direction"] == "BUY":
                unrealized_pct = ((curr_p - entry_p) / entry_p) * 100
            else:
                unrealized_pct = ((entry_p - curr_p) / entry_p) * 100
            
            open_df_rows.append({
                "Trade ID": t["trade_id"],
                "Asset": t["symbol"],
                "Side": t["direction"],
                "Entry": t["entry_price"],
                "Current Price": curr_p,
                "Stop Loss": t["stop_loss"],
                "Take Profit": t["take_profit"],
                "R:R": t["risk_reward"],
                "Unrealized P/L %": f"{unrealized_pct:+.2f}%",
                "Size": f"{t.get('position_size', 0)} {t.get('unit', '')}",
                "Review Reminder": t.get("review_time", "N/A"),
                "Expiry": t.get("expiry_time", "None"),
                "Notes": t.get("notes", ""),
            })
        st.dataframe(pd.DataFrame(open_df_rows), use_container_width=True)

        # Manual Close Control
        st.write("**Manual Trade Exit**")
        c_col1, c_col2, c_col3, c_col4 = st.columns([2, 1, 2, 1])
        with c_col1:
            trade_to_close = st.selectbox(
                "Select Trade to Close",
                [t["trade_id"] for t in open_pts],
                key="select_close_trade",
            )
        with c_col2:
            suggested_px = current_px if df is not None and len(df) > 0 else 0.0
            manual_exit_px = st.number_input("Exit Price", min_value=0.0001, value=float(suggested_px), format="%.4f", key="input_exit_px")
        with c_col3:
            close_reason = st.text_input("Exit Reason", value="Manual User Exit", key="input_close_reason")
        with c_col4:
            st.write("")
            st.write("")
            btn_close_now = st.button("Close Trade", key="btn_close_paper_trade")

        if btn_close_now:
            ok, msg, closed_t = pt_manager.close_trade_manually(
                trade_id=trade_to_close,
                exit_price=manual_exit_px,
                reason=close_reason,
            )
            if ok:
                st.success(f"{msg} Realized P/L: {closed_t['pnl_pct']:+.2f}%")
                st.rerun()
            else:
                st.warning(f"{msg}")
    else:
        st.info("No open personal paper trades. You can enter trades on valid setups in the Analysis tab.")

    st.markdown("---")
    closed_pts = pt_manager.get_closed_trades()
    st.subheader(f"Closed Paper Trades History ({len(closed_pts)})")
    if closed_pts:
        closed_df_rows = []
        for t in closed_pts:
            closed_df_rows.append({
                "Trade ID": t["trade_id"],
                "Asset": t["symbol"],
                "Side": t["direction"],
                "Entry": t["entry_price"],
                "Exit": t.get("exit_price"),
                "Realized P/L %": f"{t.get('pnl_pct', 0.0):+.2f}%",
                "Realized P/L ($)": f"${t.get('pnl_amount', 0.0):+,.2f}" if t.get("pnl_amount") is not None else "N/A",
                "Outcome": t.get("outcome", "N/A"),
                "Exit Reason": t.get("exit_reason", "N/A"),
                "Entry Time": t.get("entry_time"),
                "Exit Time": t.get("exit_time"),
                "Notes": t.get("notes", ""),
            })
        st.dataframe(pd.DataFrame(closed_df_rows), use_container_width=True)
    else:
        st.info("No closed paper trades in history.")


# ==================================================
# TAB 4 - System Signals Tracker (Automated Simulation)
# ==================================================
with tab4:
    st.subheader("System Signals Tracker")
    st.caption("Tracks system-generated automated signals. Distinct from your personal paper trade history.")

    tracker = PerformanceTracker()
    summary = tracker.summary()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Signals", summary["total_signals"])
    k2.metric("Open System Signals", summary["open"])
    k3.metric("Win Rate", f"{summary['win_rate']}%")
    k4.metric("Avg P/L", f"{summary['avg_pnl']:+.2f}%")
    k5.metric("Total Net P/L", f"{summary['total_pnl']:+.2f}%")

    open_signals = tracker.get_open_signals()
    if open_signals:
        st.write("**Active System Signals**")
        st.dataframe(pd.DataFrame(open_signals), use_container_width=True)
    else:
        st.info("No active system signals currently open.")

    closed_signals = tracker.get_closed_signals()
    if closed_signals:
        st.write("**Closed System Signals**")
        st.dataframe(pd.DataFrame(closed_signals), use_container_width=True)

    by_sym = tracker.summary_by_symbol()
    if by_sym:
        st.write("**System Performance Breakdown by Asset**")
        st.dataframe(pd.DataFrame([{"Symbol": k, **v} for k, v in by_sym.items()]), use_container_width=True)


# --------------------------------------------------
# Telegram Notification Dispatch
# --------------------------------------------------
if send_tg:
    if df is None:
        st.sidebar.warning("Cannot dispatch: Real market data is unavailable.")
    elif "analysis" not in dir() or "error" in analysis:
        st.sidebar.warning("Cannot dispatch: Analysis not available.")
    else:
        notifier = TelegramNotifier()
        if notifier.send_signal(analysis):
            st.sidebar.success("Signal successfully dispatched to Telegram!")
        else:
            st.sidebar.warning("Failed to dispatch. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
