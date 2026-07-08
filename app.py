from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from pattern_scanner import (
    CONFIGURED_TICKERS,
    DEFAULT_INTERVAL,
    DEFAULT_MONTHS,
    DEFAULT_RATIOS,
    add_indicators,
    get_tickers_for_universe,
    parse_inputs,
    scan_many,
    scan_ticker,
)

st.set_page_config(
    page_title="OXABC Scanner",
    page_icon="📊",
    layout="wide",
)

st.title("OXABC Scanner")
st.caption("Default scan: 1-hour candles over 3 months. Data source: Yahoo Finance via yfinance.")

with st.expander("Pattern this app scans for", expanded=False):
    st.markdown(
        """
        **Bullish shape:** `O high → X low → A high → B low → C high`  
        **Bearish inverse:** `O low → X high → A low → B high → C low`

        Default Fibonacci ranges:
        - `XA / OX`: 0.50 to 0.618
        - `AB / XA`: 1.13 to 1.618
        - `BC / AB`: 1.618 to 2.27

        The scanner can show patterns that are still forming as well as completed patterns.
        """
    )


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_universe(universe: str, custom_text: str) -> list[str]:
    return get_tickers_for_universe(universe, custom_text)


@st.cache_data(ttl=15 * 60, show_spinner=False)
def cached_scan_ticker(**kwargs):
    return scan_ticker(**kwargs)


left, right = st.columns([0.62, 0.38], gap="large")

with left:
    universe = st.selectbox(
        "Stock universe",
        [
            "S&P 500",
            "Nasdaq-100",
            "Dow 30",
            "All US-listed common stocks",
            "Configured list",
            "Custom tickers",
        ],
        index=0,
        help="Choose which tickers to scan. The selected symbols are downloaded from Yahoo Finance.",
    )

    custom_input = st.text_area(
        "Custom tickers or Yahoo Finance URLs",
        value="AAPL\nMSFT\nNVDA\nTSLA\nSPY",
        height=130,
        disabled=universe != "Custom tickers",
        help="Used only when Stock universe is set to Custom tickers.",
    )

    if universe == "Configured list":
        st.caption(f"Configured list contains {len(CONFIGURED_TICKERS)} symbols.")

with right:
    st.subheader("Scan settings")
    interval_options = ["1h", "60m", "30m", "15m", "5m", "1d"]
    interval = st.selectbox(
        "Candle interval",
        interval_options,
        index=interval_options.index(DEFAULT_INTERVAL),
    )
    months = st.number_input("Price history window, months", min_value=1, max_value=12, value=DEFAULT_MONTHS, step=1)
    direction = st.selectbox("Pattern direction", ["Both", "Bullish", "Bearish"], index=0)
    max_tickers = st.number_input(
        "Max tickers to scan, 0 = no limit",
        min_value=0,
        max_value=10000,
        value=0,
        step=25,
        help="Useful for testing a large universe before scanning everything.",
    )

with st.sidebar:
    st.header("Pattern settings")
    pivot_mode = st.selectbox("Pivot source", ["High/Low", "Close"], index=0)
    lookback = st.slider("Pivot lookback candles", min_value=2, max_value=30, value=5, step=1)
    min_move_pct = st.slider(
        "Minimum swing size",
        min_value=0.0,
        max_value=0.20,
        value=0.005,
        step=0.001,
        format="%.3f",
    )
    tolerance = st.slider("Ratio tolerance", min_value=0.0, max_value=0.20, value=0.04, step=0.005, format="%.3f")
    recent_candles = st.slider("Only show patterns ending within recent candles", min_value=25, max_value=500, value=120, step=25)
    forming_threshold = st.slider("BC forming threshold", min_value=0.10, max_value=1.00, value=0.75, step=0.05)
    near_complete_threshold = st.slider("Near-complete threshold", min_value=0.50, max_value=1.00, value=0.90, step=0.05)

    st.divider()
    st.header("Ratio ranges")
    xa_low = st.number_input("XA/OX low", value=float(DEFAULT_RATIOS["XA_over_OX"][0]), step=0.01)
    xa_high = st.number_input("XA/OX high", value=float(DEFAULT_RATIOS["XA_over_OX"][1]), step=0.01)
    ab_low = st.number_input("AB/XA low", value=float(DEFAULT_RATIOS["AB_over_XA"][0]), step=0.01)
    ab_high = st.number_input("AB/XA high", value=float(DEFAULT_RATIOS["AB_over_XA"][1]), step=0.01)
    bc_low = st.number_input("BC/AB low", value=float(DEFAULT_RATIOS["BC_over_AB"][0]), step=0.01)
    bc_high = st.number_input("BC/AB high", value=float(DEFAULT_RATIOS["BC_over_AB"][1]), step=0.01)

    st.divider()
    st.header("Chart overlays")
    selected_mas = st.multiselect(
        "Show moving averages",
        ["hourly", "daily", "weekly"],
        default=["hourly", "daily", "weekly"],
    )

ratios = {
    "XA_over_OX": (xa_low, xa_high),
    "AB_over_XA": (ab_low, ab_high),
    "BC_over_AB": (bc_low, bc_high),
}

scan_button = st.button("Scan Yahoo Finance data", type="primary", use_container_width=True)

VISIBLE_COLS = [
    "ticker",
    "direction",
    "status",
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
    "BC Progress %",
    "Target C Low",
    "Target C High",
    "score",
]


if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "scan_errors" not in st.session_state:
    st.session_state.scan_errors = {}
if "scan_settings" not in st.session_state:
    st.session_state.scan_settings = None


def make_oxabc_chart(
    df: pd.DataFrame,
    row: pd.Series,
    selected_mas: list[str],
    interval_label: str,
) -> go.Figure:
    chart_df = add_indicators(df)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.62, 0.18, 0.20],
        subplot_titles=(
            f"{row['ticker']} - {interval_label} candles with OXABC overlay",
            "Volume",
            "RSI",
        ),
    )

    fig.add_trace(
        go.Candlestick(
            x=chart_df["Date"],
            open=chart_df["Open"],
            high=chart_df["High"],
            low=chart_df["Low"],
            close=chart_df["Close"],
            name="Price",
            increasing_line_color="#00ff00",
            decreasing_line_color="#ff0000",
        ),
        row=1,
        col=1,
    )

    labels = ["O", "X", "A", "B", "C"]
    dates = [pd.to_datetime(row[f"{label}_date"]) for label in labels]
    prices = [float(row[f"{label}_price"]) for label in labels]
    color = "lime" if row["direction"] == "Bullish" else "red"
    dash = "solid" if row["status"] == "COMPLETE" else "dash"

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            mode="lines+markers+text",
            text=labels,
            textposition="top center",
            line=dict(color=color, width=2.5, dash=dash),
            marker=dict(size=9),
            name=f"{row['direction']} {row['status']}",
        ),
        row=1,
        col=1,
    )

    # Target C zone
    fig.add_hrect(
        y0=float(row["Target C Low"]),
        y1=float(row["Target C High"]),
        line_width=0,
        fillcolor="LightGreen" if row["direction"] == "Bullish" else "LightCoral",
        opacity=0.12,
        row=1,
        col=1,
    )

    ma_groups = {
        "hourly": [("HMA_50", "50 HMA", "#FF6B35", "solid"), ("HMA_100", "100 HMA", "#F7931E", "solid"), ("HMA_200", "200 HMA", "#FDC830", "solid")],
        "daily": [("DMA_50", "50 DMA", "#4ECDC4", "dash"), ("DMA_100", "100 DMA", "#44A08D", "dash"), ("DMA_200", "200 DMA", "#1ABC9C", "dash")],
        "weekly": [("WMA_50", "50 WMA", "#A8E6CF", "dot"), ("WMA_100", "100 WMA", "#87CEEB", "dot"), ("WMA_200", "200 WMA", "#B0E0E6", "dot")],
    }
    for group in selected_mas:
        for column, name, color_value, dash_value in ma_groups.get(group, []):
            if column in chart_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=chart_df["Date"],
                        y=chart_df[column],
                        name=name,
                        line=dict(color=color_value, width=1.4, dash=dash_value),
                        connectgaps=True,
                    ),
                    row=1,
                    col=1,
                )

    fig.add_trace(
        go.Bar(x=chart_df["Date"], y=chart_df["Volume"], name="Volume", marker_color="lightblue"),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart_df["Date"], y=chart_df["RSI"], name="RSI", line=dict(width=1.5, color="#FFD700")),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    try:
        positions = chart_df["Date"].searchsorted(pd.to_datetime(dates))
        positions = [int(p) for p in positions if 0 <= int(p) < len(chart_df)]
        if positions:
            pad = 80
            start = max(min(positions) - pad, 0)
            end = min(max(positions) + pad, len(chart_df) - 1)
            fig.update_xaxes(range=[chart_df.loc[start, "Date"], chart_df.loc[end, "Date"]])
    except Exception:
        pass

    fig.update_layout(
        height=900,
        template="plotly_dark",
        showlegend=True,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        title=(
            f"{row['ticker']} {row['direction']} {row['status']} | "
            f"BC progress {row['BC Progress %']}%"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=15, r=15, t=80, b=15),
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)
    return fig


if scan_button:
    try:
        tickers = cached_universe(universe, custom_input)
    except Exception as exc:
        st.error(f"Could not load the selected stock universe: {exc}")
        st.stop()

    if universe == "Custom tickers":
        tickers = parse_inputs(custom_input)

    if max_tickers > 0:
        tickers = tickers[: int(max_tickers)]

    if not tickers:
        st.warning("No tickers found for the selected stock universe.")
        st.stop()

    st.write(f"Scanning {len(tickers)} ticker(s).")
    progress_bar = st.progress(0)
    progress_text = st.empty()

    def update_progress(i: int, total: int, ticker: str) -> None:
        progress_bar.progress(i / total)
        progress_text.write(f"Scanning {i}/{total}: {ticker}")

    results, errors = scan_many(
        tickers,
        months=months,
        interval=interval,
        lookback=lookback,
        min_move_pct=min_move_pct,
        tolerance=tolerance,
        direction=direction,
        pivot_mode=pivot_mode,
        ratios=ratios,
        forming_threshold=forming_threshold,
        near_complete_threshold=near_complete_threshold,
        recent_candles=recent_candles,
        progress_callback=update_progress,
    )
    progress_text.write("Scan complete.")

    st.session_state.scan_errors = errors

    if results.empty:
        st.session_state.scan_results = None
        st.session_state.scan_settings = None
        st.info("No OXABC patterns found with the current settings. Try lowering the minimum swing size, increasing tolerance, or scanning more tickers.")
        st.stop()

    results = results.sort_values(["score", "BC Progress %", "C_date"], ascending=[False, False, False]).reset_index(drop=True)

    # Store the scan so interacting with widgets below does not erase or rerun it.
    st.session_state.scan_results = results
    st.session_state.scan_settings = {
        "months": months,
        "interval": interval,
        "lookback": lookback,
        "min_move_pct": min_move_pct,
        "tolerance": tolerance,
        "direction": direction,
        "pivot_mode": pivot_mode,
        "ratios": ratios,
        "forming_threshold": forming_threshold,
        "near_complete_threshold": near_complete_threshold,
        "recent_candles": recent_candles,
    }
    st.session_state.selected_pattern_index = 0

results = st.session_state.scan_results
scan_settings = st.session_state.scan_settings
errors = st.session_state.scan_errors

if results is None or scan_settings is None:
    st.info("Choose a stock universe and press Scan to search for OXABC patterns.")
else:
    if errors:
        with st.expander(f"Tickers with errors ({len(errors)})"):
            for ticker, message in errors.items():
                st.write(f"**{ticker}:** {message}")

    st.success(f"Found {len(results)} OXABC pattern(s) across {results['ticker'].nunique()} ticker(s).")
    st.dataframe(results[VISIBLE_COLS], use_container_width=True, hide_index=True)
    st.download_button(
        "Download results as CSV",
        data=results[VISIBLE_COLS].to_csv(index=False).encode("utf-8"),
        file_name="oxabc_scan_results.csv",
        mime="text/csv",
    )

    st.subheader("Chart a detected OXABC pattern")
    pattern_options = list(range(len(results)))

    def pattern_label(i: int) -> str:
        row = results.iloc[i]
        return (
            f"{i}: {row['ticker']} {row['direction']} {row['status']} | "
            f"C {row['C_date']} | BC progress {row['BC Progress %']}%"
        )

    if st.session_state.get("selected_pattern_index", 0) not in pattern_options:
        st.session_state.selected_pattern_index = 0

    chosen_index = st.selectbox(
        "Choose a detected pattern",
        pattern_options,
        format_func=pattern_label,
        key="selected_pattern_index",
    )
    chosen = results.iloc[int(chosen_index)]

    with st.spinner("Loading chart data..."):
        _, chart_df, _ = cached_scan_ticker(
            ticker=chosen["ticker"],
            months=scan_settings["months"],
            interval=scan_settings["interval"],
            lookback=scan_settings["lookback"],
            min_move_pct=scan_settings["min_move_pct"],
            tolerance=scan_settings["tolerance"],
            direction=scan_settings["direction"],
            pivot_mode=scan_settings["pivot_mode"],
            ratios=scan_settings["ratios"],
            forming_threshold=scan_settings["forming_threshold"],
            near_complete_threshold=scan_settings["near_complete_threshold"],
            recent_candles=scan_settings["recent_candles"],
        )
    st.plotly_chart(
        make_oxabc_chart(chart_df, chosen, selected_mas, scan_settings["interval"]),
        use_container_width=True,
    )
