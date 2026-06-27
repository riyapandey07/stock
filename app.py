from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pattern_scanner import DEFAULT_RATIOS, parse_inputs, scan_many, scan_ticker

st.set_page_config(
    page_title="Yahoo O-X-A-B-C Pattern Scanner",
    page_icon="📈",
    layout="wide",
)

st.title("Yahoo Finance O-X-A-B-C Pattern Scanner")
st.caption("Paste Yahoo Finance URLs or tickers. The app scans for the swing pattern from your sketch.")

with st.expander("Pattern this app scans for", expanded=False):
    st.markdown(
        """
        **Bullish shape:** `O high → X low → A high → B low → C high`  
        **Bearish inverse:** `O low → X high → A low → B high → C low`

        Default Fibonacci ranges:
        - `XA / OX`: 0.50 to 0.618
        - `AB / XA`: 1.13 to 1.618
        - `BC / AB`: 1.618 to 2.27

        This is a pattern scanner, not a buy/sell recommendation.
        """
    )

left, right = st.columns([0.58, 0.42], gap="large")

with left:
    raw_inputs = st.text_area(
        "Yahoo Finance URLs or tickers",
        value="https://finance.yahoo.com/quote/AAPL/\nhttps://finance.yahoo.com/quote/MSFT/\nhttps://finance.yahoo.com/quote/NVDA/",
        height=180,
        help="Separate items with spaces, commas, or new lines. Examples: AAPL, MSFT, RELIANCE.NS, https://finance.yahoo.com/quote/TSLA/",
    )

with right:
    st.subheader("Scan settings")
    period = st.selectbox("Price history", ["6mo", "1y", "2y", "5y", "10y", "max"], index=2)
    interval = st.selectbox("Candle interval", ["1d", "1wk", "1mo"], index=0)
    direction = st.selectbox("Pattern direction", ["Bullish", "Bearish", "Both"], index=0)
    pivot_mode = st.selectbox("Pivot source", ["High/Low", "Close"], index=0)

with st.sidebar:
    st.header("Fine tuning")
    lookback = st.slider("Pivot lookback candles", min_value=2, max_value=30, value=5, step=1)
    min_move_pct = st.slider("Minimum swing size", min_value=0.0, max_value=0.20, value=0.03, step=0.005, format="%.3f")
    tolerance = st.slider("Ratio tolerance", min_value=0.0, max_value=0.20, value=0.04, step=0.005, format="%.3f")

    st.divider()
    st.subheader("Ratio ranges")
    xa_low = st.number_input("XA/OX low", value=float(DEFAULT_RATIOS["XA_over_OX"][0]), step=0.01)
    xa_high = st.number_input("XA/OX high", value=float(DEFAULT_RATIOS["XA_over_OX"][1]), step=0.01)
    ab_low = st.number_input("AB/XA low", value=float(DEFAULT_RATIOS["AB_over_XA"][0]), step=0.01)
    ab_high = st.number_input("AB/XA high", value=float(DEFAULT_RATIOS["AB_over_XA"][1]), step=0.01)
    bc_low = st.number_input("BC/AB low", value=float(DEFAULT_RATIOS["BC_over_AB"][0]), step=0.01)
    bc_high = st.number_input("BC/AB high", value=float(DEFAULT_RATIOS["BC_over_AB"][1]), step=0.01)

ratios = {
    "XA_over_OX": (xa_low, xa_high),
    "AB_over_XA": (ab_low, ab_high),
    "BC_over_AB": (bc_low, bc_high),
}

scan_button = st.button("Scan", type="primary", use_container_width=True)


def make_pattern_chart(df: pd.DataFrame, row: pd.Series) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
        )
    )

    labels = ["O", "X", "A", "B", "C"]
    dates = [pd.to_datetime(row[f"{label}_date"]) for label in labels]
    prices = [float(row[f"{label}_price"]) for label in labels]

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            mode="lines+markers+text",
            text=labels,
            textposition="top center",
            name="O-X-A-B-C",
            line=dict(width=3),
            marker=dict(size=10),
        )
    )

    min_date = min(dates)
    max_date = max(dates)
    padded = df.loc[(df.index >= min_date - pd.Timedelta(days=20)) & (df.index <= max_date + pd.Timedelta(days=20))]
    if not padded.empty:
        fig.update_xaxes(range=[padded.index.min(), padded.index.max()])

    fig.update_layout(
        height=620,
        xaxis_rangeslider_visible=False,
        margin=dict(l=15, r=15, t=40, b=15),
        title=f"{row['ticker']} {row['direction']} match ending at C = {row['C_date']}",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


if scan_button:
    try:
        tickers = parse_inputs(raw_inputs)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    if not tickers:
        st.warning("Enter at least one Yahoo Finance URL or ticker.")
        st.stop()

    with st.status(f"Scanning {len(tickers)} ticker(s)...", expanded=True) as status:
        st.write(", ".join(tickers))
        results, errors = scan_many(
            tickers,
            period=period,
            interval=interval,
            lookback=lookback,
            min_move_pct=min_move_pct,
            tolerance=tolerance,
            direction=direction,
            pivot_mode=pivot_mode,
            ratios=ratios,
        )
        status.update(label="Scan complete", state="complete")

    if errors:
        with st.expander("Tickers with errors"):
            for ticker, message in errors.items():
                st.write(f"**{ticker}:** {message}")

    if results.empty:
        st.info("No matching patterns found with the current settings. Try increasing tolerance, lowering minimum swing size, or changing the lookback.")
        st.stop()

    st.success(f"Found {len(results)} matching pattern(s).")

    visible_cols = [
        "ticker",
        "direction",
        "O_date",
        "X_date",
        "A_date",
        "B_date",
        "C_date",
        "O_price",
        "X_price",
        "A_price",
        "B_price",
        "C_price",
        "XA/OX",
        "AB/XA",
        "BC/AB",
    ]
    results = results[visible_cols + [c for c in results.columns if c not in visible_cols]]

    st.dataframe(results[visible_cols], use_container_width=True, hide_index=True)
    st.download_button(
        "Download results as CSV",
        data=results[visible_cols].to_csv(index=False).encode("utf-8"),
        file_name="oxabc_scan_results.csv",
        mime="text/csv",
    )

    st.subheader("Chart a match")
    labels = [
        f"{i}: {r.ticker} {r.direction} | C {r.C_date} | XA/OX {r._asdict().get('XA/OX', '') if hasattr(r, '_asdict') else ''}"
        for i, r in enumerate(results[visible_cols].itertuples(index=False))
    ]
    # The label above avoids crashing on special column names; build cleaner labels below.
    labels = []
    for i, (_, row) in enumerate(results[visible_cols].iterrows()):
        labels.append(
            f"{i}: {row['ticker']} {row['direction']} | C {row['C_date']} | ratios {row['XA/OX']}, {row['AB/XA']}, {row['BC/AB']}"
        )

    choice = st.selectbox("Choose a detected pattern", labels)
    chosen_index = int(choice.split(":", 1)[0])
    chosen = results.iloc[chosen_index]

    with st.spinner("Loading chart data..."):
        _, chart_df, _ = scan_ticker(
            chosen["ticker"],
            period=period,
            interval=interval,
            lookback=lookback,
            min_move_pct=min_move_pct,
            tolerance=tolerance,
            direction=direction,
            pivot_mode=pivot_mode,
            ratios=ratios,
        )
    st.plotly_chart(make_pattern_chart(chart_df, chosen), use_container_width=True)

else:
    st.info("Paste Yahoo Finance URLs or tickers, adjust settings, then press Scan.")
