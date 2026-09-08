#!/usr/bin/env python3
"""
TradeFusion AI - Streamlit Dashboard
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.data.fetcher import get_data
from backend.indicators.core import compute_all_indicators
from backend.analyzer import TradeFusionAnalyzer
from backend.backtester import Backtester
from backend.notifications.telegram import TelegramNotifier
from backend.performance.tracker import PerformanceTracker

st.set_page_config(page_title="TradeFusion AI", page_icon="📈", layout="wide")

st.title("📈 TradeFusion AI Dashboard")
st.caption("Multi-indicator analysis • Confidence scoring • Backtesting • Performance tracking • Sentinel")

# Sidebar
with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox(
        "Asset",
        ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
         "GC=F", "SI=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AAPL", "TSLA"],
        index=0
    )
    risk_mode = st.selectbox("Risk Mode", ["low", "medium", "high"], index=1)
    period = st.selectbox("Data Period", ["3mo", "6mo", "1y"], index=1)
    interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
    use_synthetic = st.checkbox("Force Synthetic Data", value=False)

    st.divider()
    st.subheader("Telegram (Optional)")
    tg_token = st.text_input("Bot Token", type="password")
    tg_chat = st.text_input("Chat ID")
    send_tg = st.button("Send Latest Signal to Telegram")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Analysis", "📈 Backtest", "🏆 Performance Tracker"])

# ---------- TAB 1: Analysis ----------
with tab1:
    with st.spinner("Loading market data..."):
        df = get_data(symbol, period=period, interval=interval, use_synthetic=use_synthetic)
        df_ind = compute_all_indicators(df).dropna()

    analyzer = TradeFusionAnalyzer(risk_mode=risk_mode)
    analysis = analyzer.analyze(df, symbol=symbol)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Price", f"{analysis['price']}")
    c2.metric("Signal", analysis['signal'])
    c3.metric("Confidence", f"{analysis['confidence']}%")
    c4.metric("Bullish", f"{analysis['bullish_score']}%")
    c5.metric("Bearish", f"{analysis['bearish_score']}%")

    if analysis['signal'] == "BUY":
        st.success(f"🟢 **BUY** — {analysis['confidence']}% confidence")
    elif analysis['signal'] == "SELL":
        st.error(f"🔴 **SELL** — {analysis['confidence']}% confidence")
    else:
        st.info(f"⚪ **NO TRADE** — {analysis['confidence']}% (below threshold)")

    # Charts
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.55, 0.25, 0.20],
        subplot_titles=("Price + EMAs + Bollinger", "RSI", "MACD")
    )
    fig.add_trace(go.Candlestick(
        x=df_ind.index, open=df_ind['open'], high=df_ind['high'],
        low=df_ind['low'], close=df_ind['close'], name="Price"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['ema_50'], name="EMA 50", line=dict(width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['ema_200'], name="EMA 200", line=dict(width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['bb_upper'], name="BB Upper", line=dict(width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['bb_lower'], name="BB Lower", line=dict(width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['rsi'], name="RSI", line=dict(color="purple")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['macd'], name="MACD", line=dict(color="blue")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['macd_signal'], name="Signal", line=dict(color="orange")), row=3, col=1)
    fig.update_layout(height=780, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧠 Sentinel Analysis")
    st.code(analysis['explanation'], language=None)

    # Track button
    if analysis['signal'] in ("BUY", "SELL"):
        if st.button("📌 Track This Signal"):
            tracker = PerformanceTracker()
            s = tracker.add_signal(analysis)
            st.success(f"Signal #{s['id']} tracked!")

# ---------- TAB 2: Backtest ----------
with tab2:
    st.subheader("Quick Backtest")
    if st.button("Run Backtest on Current Data"):
        with st.spinner("Running backtest..."):
            bt = Backtester(risk_mode=risk_mode)
            result = bt.run(df, symbol=symbol)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Trades", result.total_trades)
            m2.metric("Win Rate", f"{result.win_rate:.1f}%")
            m3.metric("Total PnL", f"{result.total_pnl_pct:+.2f}%")
            m4.metric("Profit Factor", f"{result.profit_factor:.2f}")

            if result.trades:
                trades_df = pd.DataFrame([{
                    "Side": t.side,
                    "Entry": t.entry_price,
                    "Exit": t.exit_price,
                    "PnL %": round(t.pnl_pct, 2),
                    "Confidence": t.confidence
                } for t in result.trades])
                st.dataframe(trades_df, use_container_width=True)

# ---------- TAB 3: Performance Tracker ----------
with tab3:
    st.subheader("🏆 Performance Tracker")
    tracker = PerformanceTracker()
    summary = tracker.summary()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Signals", summary["total_signals"])
    k2.metric("Open", summary["open"])
    k3.metric("Win Rate", f"{summary['win_rate']}%")
    k4.metric("Avg PnL", f"{summary['avg_pnl']:+.2f}%")
    k5.metric("Total PnL", f"{summary['total_pnl']:+.2f}%")

    # By symbol
    by_sym = tracker.summary_by_symbol()
    if by_sym:
        st.write("**Performance by Asset**")
        sym_df = pd.DataFrame([
            {"Symbol": k, **v} for k, v in by_sym.items()
        ])
        st.dataframe(sym_df, use_container_width=True)

    # Open signals
    open_signals = tracker.get_open_signals()
    if open_signals:
        st.write("**Open Signals**")
        open_df = pd.DataFrame(open_signals)[["id", "timestamp", "symbol", "signal", "confidence", "price"]]
        st.dataframe(open_df, use_container_width=True)

        st.write("Close a signal:")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            close_id = st.number_input("Signal ID", min_value=1, step=1)
        with col_b:
            exit_price = st.number_input("Exit Price", min_value=0.0, format="%.4f")
        with col_c:
            if st.button("Close Signal"):
                closed = tracker.close_signal(int(close_id), float(exit_price))
                if closed:
                    st.success(f"Signal #{close_id} closed as {closed['status'].upper()} ({closed['pnl_pct']:+.2f}%)")
                    st.rerun()
                else:
                    st.warning("Signal not found or already closed.")

    closed_signals = tracker.get_closed_signals()
    if closed_signals:
        st.write("**Closed Signals**")
        closed_df = pd.DataFrame(closed_signals)[["id", "symbol", "signal", "confidence", "price", "exit_price", "pnl_pct", "status"]]
        st.dataframe(closed_df, use_container_width=True)

# Telegram
if send_tg:
    notifier = TelegramNotifier(token=tg_token or None, chat_id=tg_chat or None)
    if notifier.send_signal(analysis):
        st.success("Signal sent to Telegram!")
    else:
        st.warning("Failed to send. Check token & chat ID.")
