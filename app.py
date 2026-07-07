from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from pattern_scanner import (
    DEFAULT_INTERVAL,
    DEFAULT_MONTHS,
    DEFAULT_RATIOS,
    STOCK_TICKERS,
    add_indicators,
    parse_inputs,
    scan_many,
    scan_ticker,
)

st.set_page_config(
    page_title="Gartley XABCD Scanner",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Gartley XABCD Scanner - Yahoo Finance")
st.caption(
    "Default scan: 1-hour candles, last 3 months, full stock universe from the TXT file via Yahoo Finance."
)

with st.expander("Pattern this app scans for", expanded=False):
    st.markdown(
        """
        **Bullish Gartley:** `X low → A high → B low → C high → D low`  
        **Bearish Gartley:** `X high → A low → B high → C low → D high`

        Default Fibonacci ranges, matching the TXT scanner:
        - `AB / XA`: 50% to 61.8%
        - `BC / AB`: 113% to 161%
        - `CD / BC`: 161% to 224% for complete patterns

        `NEAR_COMPLETE` starts at 75% CD progress. `PARTIAL_XABC` uses the current close as the temporary D point.
        """
    )

left, right = st.columns([0.62, 0.38], gap="large")

with left:
    use_full_universe = st.checkbox(
        f"Use full TXT stock universe ({len(STOCK_TICKERS)} Yahoo Finance tickers)",
        value=True,
    )
    custom_input = st.text_area(
        "Optional custom tickers",
        value="\n".join(STOCK_TICKERS[:20]),
        height=150,
        disabled=use_full_universe,
        help="Used only when the full universe checkbox is off. Separate tickers with spaces, commas, or new lines.",
    )

with right:
    st.subheader("Scan settings")
    interval_options = ["1h", "60m", "30m", "15m", "5m", "1d"]
    interval = st.selectbox(
        "Candle interval",
        interval_options,
        index=interval_options.index(DEFAULT_INTERVAL),
        help="Default is 1h to match your requested hourly scan.",
    )
    months = st.number_input("Yahoo Finance history window, months", min_value=1, max_value=12, value=DEFAULT_MONTHS, step=1)
    direction = st.selectbox("Pattern direction", ["Both", "BULLISH", "BEARISH"], index=0)

with st.sidebar:
    st.header("Ratio ranges")
    st.caption("Defaults match the TXT file.")
    ab_low = st.number_input("AB/XA low", value=float(DEFAULT_RATIOS["AB_XA"][0]), step=0.01)
    ab_high = st.number_input("AB/XA high", value=float(DEFAULT_RATIOS["AB_XA"][1]), step=0.01)
    bc_low = st.number_input("BC/AB low", value=float(DEFAULT_RATIOS["BC_AB"][0]), step=0.01)
    bc_high = st.number_input("BC/AB high", value=float(DEFAULT_RATIOS["BC_AB"][1]), step=0.01)
    cd_low = st.number_input("CD/BC complete low", value=float(DEFAULT_RATIOS["CD_BC"][0]), step=0.01)
    cd_high = st.number_input("CD/BC complete high", value=float(DEFAULT_RATIOS["CD_BC"][1]), step=0.01)

    st.divider()
    st.header("Chart overlays")
    selected_mas = st.multiselect(
        "Show moving averages",
        ["hourly", "daily", "weekly"],
        default=["hourly", "daily", "weekly"],
        help="Daily/weekly MAs are approximated on the hourly chart. Longer weekly MAs may be blank with only 3 months of data.",
    )

ratios = {
    "AB_XA": (ab_low, ab_high),
    "BC_AB": (bc_low, bc_high),
    "CD_BC": (cd_low, cd_high),
}

scan_button = st.button("Scan Yahoo Finance data", type="primary", use_container_width=True)


def make_gartley_chart(df: pd.DataFrame, row: pd.Series, selected_mas: list[str]) -> go.Figure:
    chart_df = add_indicators(df)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.62, 0.18, 0.20],
        subplot_titles=(
            f"{row['ticker']} - {interval} candles with Gartley XABCD overlay",
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

    labels = ["X", "A", "B", "C", "D"]
    dates = [pd.to_datetime(row[f"{label}_date"]) for label in labels]
    prices = [float(row[f"{label}_price"]) for label in labels]
    color = "lime" if row["direction"] == "BULLISH" else "red"

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            mode="lines+markers+text",
            text=labels,
            textposition="top center",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            name=f"{row['direction']} XABCD",
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    ma_specs = []
    if "hourly" in selected_mas:
        ma_specs.extend([
            ("HMA_50", "50 HMA", dict(color="#FF6B35", width=1.5)),
            ("HMA_100", "100 HMA", dict(color="#F7931E", width=1.5)),
            ("HMA_200", "200 HMA", dict(color="#FDC830", width=1.5)),
        ])
    if "daily" in selected_mas:
        ma_specs.extend([
            ("DMA_50", "50 DMA", dict(color="#4ECDC4", width=1.5, dash="dash")),
            ("DMA_100", "100 DMA", dict(color="#44A08D", width=1.5, dash="dash")),
            ("DMA_200", "200 DMA", dict(color="#1ABC9C", width=1.5, dash="dash")),
        ])
    if "weekly" in selected_mas:
        ma_specs.extend([
            ("WMA_50", "50 WMA", dict(color="#A8E6CF", width=1.5, dash="dot")),
            ("WMA_100", "100 WMA", dict(color="#87CEEB", width=1.5, dash="dot")),
            ("WMA_200", "200 WMA", dict(color="#B0E0E6", width=1.5, dash="dot")),
        ])

    for column, name, line in ma_specs:
        if column in chart_df.columns and chart_df[column].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=chart_df["Date"],
                    y=chart_df[column],
                    name=name,
                    line=line,
                    connectgaps=True,
                ),
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Bar(
            x=chart_df["Date"],
            y=chart_df["Volume"],
            name="Volume",
            marker_color="lightblue",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df["Date"],
            y=chart_df["RSI"],
            name="RSI",
            line=dict(width=1.5, color="#FFD700"),
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    try:
        positions = chart_df["Date"].searchsorted(pd.DatetimeIndex(dates))
        if len(positions):
            pad = 80
            start = max(int(min(positions)) - pad, 0)
            end = min(int(max(positions)) + pad, len(chart_df) - 1)
            fig.update_xaxes(range=[chart_df.iloc[start]["Date"], chart_df.iloc[end]["Date"]])
    except Exception:
        pass

    fig.update_layout(
        height=900,
        template="plotly_dark",
        showlegend=True,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        margin=dict(l=15, r=15, t=60, b=15),
        title=(
            f"{row['ticker']} {row['direction']} {row['type']} | "
            f"AB={row['AB/XA %']:.1f}% BC={row['BC/AB %']:.1f}% CD={row['CD/BC %']:.1f}%"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_yaxes(title_text="Price ₹", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)
    return fig


if scan_button:
    tickers = STOCK_TICKERS if use_full_universe else parse_inputs(custom_input)

    if not tickers:
        st.warning("Enter at least one ticker or use the full TXT stock universe.")
        st.stop()

    progress = st.progress(0)
    status_text = st.empty()
    log_box = st.empty()
    recent_lines: list[str] = []

    def progress_callback(i: int, total: int, ticker: str, count: int, error: str | None):
        progress.progress(i / total)
        if error:
            line = f"[{i}/{total}] {ticker}: error - {error}"
        else:
            line = f"[{i}/{total}] {ticker}: {count} pattern(s)"
        recent_lines.append(line)
        status_text.write(line)
        log_box.code("\n".join(recent_lines[-12:]))

    with st.spinner(f"Downloading and scanning {len(tickers)} Yahoo Finance ticker(s)..."):
        results, errors, data_by_ticker, patterns_by_ticker = scan_many(
            tickers,
            months=int(months),
            interval=interval,
            direction=direction,
            ratios=ratios,
            progress_callback=progress_callback,
        )

    st.session_state["results"] = results
    st.session_state["errors"] = errors
    st.session_state["data_by_ticker"] = data_by_ticker
    st.session_state["patterns_by_ticker"] = patterns_by_ticker

    progress.progress(1.0)
    status_text.write("Scan complete")

results = st.session_state.get("results", pd.DataFrame())
errors = st.session_state.get("errors", {})
data_by_ticker = st.session_state.get("data_by_ticker", {})

if errors:
    with st.expander(f"Tickers with errors ({len(errors)})"):
        for ticker, message in errors.items():
            st.write(f"**{ticker}:** {message}")

if results.empty:
    st.info("Press Scan to download Yahoo Finance data and search for Gartley XABCD patterns.")
    st.stop()

st.success(f"Found {len(results)} Gartley pattern(s) across {results['ticker'].nunique()} ticker(s).")

visible_cols = [
    "ticker",
    "direction",
    "type",
    "score",
    "X_date",
    "A_date",
    "B_date",
    "C_date",
    "D_date",
    "X_price",
    "A_price",
    "B_price",
    "C_price",
    "D_price",
    "AB/XA %",
    "BC/AB %",
    "CD/BC %",
]
visible_cols = [c for c in visible_cols if c in results.columns]
st.dataframe(results[visible_cols], use_container_width=True, hide_index=True)

st.download_button(
    "Download results as CSV",
    data=results[visible_cols].to_csv(index=False).encode("utf-8"),
    file_name="gartley_xabcd_scan_results.csv",
    mime="text/csv",
)

st.subheader("Chart a detected Gartley pattern")
labels = []
for i, row in results.iterrows():
    labels.append(
        f"{i}: {row['ticker']} {row['direction']} {row['type']} | D {row['D_date']} | "
        f"AB {row['AB/XA %']:.1f}% BC {row['BC/AB %']:.1f}% CD {row['CD/BC %']:.1f}%"
    )

choice = st.selectbox("Choose a detected pattern", labels)
chosen_index = int(choice.split(":", 1)[0])
chosen = results.iloc[chosen_index]
chart_df = data_by_ticker.get(chosen["ticker"])

if chart_df is None or chart_df.empty:
    with st.spinner("Reloading chart data from Yahoo Finance..."):
        _, chart_df, _ = scan_ticker(
            chosen["ticker"],
            months=int(months),
            interval=interval,
            direction=direction,
            ratios=ratios,
        )

st.plotly_chart(make_gartley_chart(chart_df, chosen, selected_mas), use_container_width=True)
