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

st.set_page_config(page_title="TradeFusion AI", page_icon="📈", layout="wide")

st.title("📈 TradeFusion AI Dashboard")
st.caption("Multi-indicator analysis • Confidence scoring • Backtesting • Sentinel explanations")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Asset", ["BTC-USD", "ETH-USD", "GC=F", "EURUSD=X", "GBPUSD=X", "AAPL"], index=0)
    risk_mode = st.selectbox("Risk Mode", ["low", "medium", "high"], index=1)
    period = st.selectbox("Data Period", ["3mo", "6mo", "1y"], index=1)
    interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
    use_synthetic = st.checkbox("Force Synthetic Data", value=False)

    st.divider()
    st.subheader("Telegram (Optional)")
    tg_token = st.text_input("Bot Token", type="password")
    tg_chat = st.text_input("Chat ID")
    send_tg = st.button("Send Latest Signal to Telegram")

# Load data
with st.spinner("Loading market data..."):
    df = get_data(symbol, period=period, interval=interval, use_synthetic=use_synthetic)
    df_ind = compute_all_indicators(df).dropna()

# Analysis
analyzer = TradeFusionAnalyzer(risk_mode=risk_mode)
analysis = analyzer.analyze(df, symbol=symbol)

# Metrics row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Price", f"{analysis['price']}")
col2.metric("Signal", analysis['signal'])
col3.metric("Confidence", f"{analysis['confidence']}%")
col4.metric("Bullish", f"{analysis['bullish_score']}%")
col5.metric("Bearish", f"{analysis['bearish_score']}%")

# Signal color
if analysis['signal'] == "BUY":
    st.success(f"🟢 **BUY** signal with **{analysis['confidence']}%** confidence")
elif analysis['signal'] == "SELL":
    st.error(f"🔴 **SELL** signal with **{analysis['confidence']}%** confidence")
else:
    st.info(f"⚪ **NO TRADE** — Confidence {analysis['confidence']}% below threshold")

# Charts
st.subheader("Price & Indicators")

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.55, 0.25, 0.20],
    subplot_titles=("Price + EMAs + Bollinger", "RSI", "MACD")
)

# Candlestick
fig.add_trace(go.Candlestick(
    x=df_ind.index, open=df_ind['open'], high=df_ind['high'],
    low=df_ind['low'], close=df_ind['close'], name="Price"
), row=1, col=1)

fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['ema_50'], name="EMA 50", line=dict(width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['ema_200'], name="EMA 200", line=dict(width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['bb_upper'], name="BB Upper", line=dict(width=1, dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['bb_lower'], name="BB Lower", line=dict(width=1, dash="dot")), row=1, col=1)

# RSI
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['rsi'], name="RSI", line=dict(color="purple")), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

# MACD
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['macd'], name="MACD", line=dict(color="blue")), row=3, col=1)
fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind['macd_signal'], name="Signal", line=dict(color="orange")), row=3, col=1)

fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# Sentinel explanation
st.subheader("🧠 Sentinel Analysis")
st.code(analysis['explanation'], language=None)

# Backtest section
st.subheader("📊 Quick Backtest")
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

# Telegram send
if send_tg:
    notifier = TelegramNotifier(token=tg_token or None, chat_id=tg_chat or None)
    if notifier.send_signal(analysis):
        st.success("Signal sent to Telegram!")
    else:
        st.warning("Failed to send. Check token & chat ID.")
