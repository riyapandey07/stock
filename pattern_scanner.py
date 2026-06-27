from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np
import pandas as pd
import yfinance as yf

PatternDirection = Literal["Bullish", "Bearish", "Both"]
PivotMode = Literal["High/Low", "Close"]

DEFAULT_RATIOS = {
    "XA_over_OX": (0.50, 0.618),
    "AB_over_XA": (1.13, 1.618),
    "BC_over_AB": (1.618, 2.27),
}


@dataclass(frozen=True)
class Pivot:
    date: pd.Timestamp
    price: float
    kind: str  # "H" or "L"


def extract_ticker(yahoo_url_or_ticker: str) -> str:
    """Extract a ticker from a Yahoo Finance URL or return a cleaned ticker."""
    text = yahoo_url_or_ticker.strip()
    if not text:
        raise ValueError("Empty ticker or URL")

    # Plain ticker input, including suffixes like RELIANCE.NS, SHOP.TO, BARC.L
    if "finance.yahoo.com" not in text.lower() and "/quote/" not in text.lower():
        return text.upper()

    parsed = urlparse(text)
    path_parts = [unquote(p) for p in parsed.path.split("/") if p]

    for key in ("quote", "chart"):
        if key in path_parts:
            idx = path_parts.index(key)
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1].upper()

    query = parse_qs(parsed.query)
    for key in ("p", "symbol"):
        if key in query and query[key]:
            return query[key][0].upper()

    # Last-chance regex for copied text that contains /quote/TICKER
    match = re.search(r"/quote/([^/?#]+)", text, re.IGNORECASE)
    if match:
        return unquote(match.group(1)).upper()

    raise ValueError(f"Could not extract a ticker from: {text}")


def parse_inputs(raw_text: str) -> list[str]:
    """Parse a text box containing URLs/tickers separated by newlines, spaces, or commas."""
    chunks = re.split(r"[\n,\t ]+", raw_text.strip())
    tickers: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        if not chunk.strip():
            continue
        ticker = extract_ticker(chunk)
        if ticker not in seen:
            tickers.append(ticker)
            seen.add(ticker)
    return tickers


def download_prices(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Download adjusted OHLC data with yfinance."""
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError("No price data returned")

    if isinstance(df.columns, pd.MultiIndex):
        # yfinance can return MultiIndex columns for some versions/configurations.
        df.columns = df.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close"}
    missing = required.difference(set(df.columns))
    if missing:
        raise ValueError(f"Missing expected OHLC columns: {sorted(missing)}")

    df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    df.index = pd.to_datetime(df.index)
    return df


def find_raw_pivots(df: pd.DataFrame, lookback: int = 5, mode: PivotMode = "High/Low") -> list[Pivot]:
    """Find local swing highs/lows."""
    if lookback < 1:
        raise ValueError("lookback must be at least 1")
    if len(df) < lookback * 2 + 1:
        return []

    pivots: list[Pivot] = []
    dates = df.index

    if mode == "Close":
        prices = df["Close"].astype(float).to_numpy()
        for i in range(lookback, len(df) - lookback):
            window = prices[i - lookback : i + lookback + 1]
            price = prices[i]
            if price == np.nanmax(window):
                pivots.append(Pivot(pd.Timestamp(dates[i]), float(price), "H"))
            elif price == np.nanmin(window):
                pivots.append(Pivot(pd.Timestamp(dates[i]), float(price), "L"))
        return pivots

    highs = df["High"].astype(float).to_numpy()
    lows = df["Low"].astype(float).to_numpy()
    for i in range(lookback, len(df) - lookback):
        high_window = highs[i - lookback : i + lookback + 1]
        low_window = lows[i - lookback : i + lookback + 1]
        if highs[i] == np.nanmax(high_window):
            pivots.append(Pivot(pd.Timestamp(dates[i]), float(highs[i]), "H"))
        if lows[i] == np.nanmin(low_window):
            pivots.append(Pivot(pd.Timestamp(dates[i]), float(lows[i]), "L"))

    pivots.sort(key=lambda p: p.date)
    return pivots


def clean_pivots(pivots: Iterable[Pivot], min_move_pct: float = 0.03) -> list[Pivot]:
    """Keep alternating high/low pivots and ignore tiny swings."""
    ordered = sorted(list(pivots), key=lambda p: p.date)
    if not ordered:
        return []

    cleaned: list[Pivot] = []

    for p in ordered:
        if not cleaned:
            cleaned.append(p)
            continue

        last = cleaned[-1]

        if p.kind == last.kind:
            # Replace same-kind consecutive pivots with the more extreme one.
            if p.kind == "H" and p.price >= last.price:
                cleaned[-1] = p
            elif p.kind == "L" and p.price <= last.price:
                cleaned[-1] = p
            continue

        move = abs(p.price - last.price) / max(abs(last.price), 1e-12)
        if move >= min_move_pct:
            cleaned.append(p)
        else:
            # For small counter-moves, keep the more extreme continuation if possible.
            if p.kind == "H" and p.price > last.price:
                cleaned[-1] = p
            elif p.kind == "L" and p.price < last.price:
                cleaned[-1] = p

    return cleaned


def _in_range(value: float, low: float, high: float, tolerance: float) -> bool:
    return low * (1 - tolerance) <= value <= high * (1 + tolerance)


def _pattern_direction(kinds: list[str]) -> str | None:
    if kinds == ["H", "L", "H", "L", "H"]:
        return "Bullish"
    if kinds == ["L", "H", "L", "H", "L"]:
        return "Bearish"
    return None


def _legs_for_ratio(points: list[Pivot], direction: str) -> tuple[float, float, float, float] | None:
    O, X, A, B, C = points
    if direction == "Bullish":
        OX = O.price - X.price
        XA = A.price - X.price
        AB = A.price - B.price
        BC = C.price - B.price
    elif direction == "Bearish":
        OX = X.price - O.price
        XA = X.price - A.price
        AB = B.price - A.price
        BC = B.price - C.price
    else:
        return None

    if min(OX, XA, AB, BC) <= 0:
        return None
    return OX, XA, AB, BC


def _format_timestamp(ts: pd.Timestamp) -> str:
    """Keep intraday timestamps when scanning 1-minute candles."""
    ts = pd.Timestamp(ts)
    return ts.isoformat(sep=" ", timespec="minutes")


def scan_oxabc_pattern(
    pivots: list[Pivot],
    ratios: dict[str, tuple[float, float]] | None = None,
    tolerance: float = 0.04,
    direction: PatternDirection = "Bullish",
) -> pd.DataFrame:
    """Scan pivot sequence for O-X-A-B-C Fibonacci pattern matches."""
    ratios = ratios or DEFAULT_RATIOS
    rows: list[dict] = []

    for i in range(len(pivots) - 4):
        points = pivots[i : i + 5]
        kinds = [p.kind for p in points]
        found_direction = _pattern_direction(kinds)
        if found_direction is None:
            continue
        if direction != "Both" and found_direction != direction:
            continue

        legs = _legs_for_ratio(points, found_direction)
        if legs is None:
            continue
        OX, XA, AB, BC = legs

        xa_ratio = XA / OX
        ab_ratio = AB / XA
        bc_ratio = BC / AB

        checks = {
            "XA/OX": _in_range(xa_ratio, *ratios["XA_over_OX"], tolerance),
            "AB/XA": _in_range(ab_ratio, *ratios["AB_over_XA"], tolerance),
            "BC/AB": _in_range(bc_ratio, *ratios["BC_over_AB"], tolerance),
        }

        if all(checks.values()):
            O, X, A, B, C = points
            rows.append(
                {
                    "direction": found_direction,
                    "O_date": _format_timestamp(O.date),
                    "X_date": _format_timestamp(X.date),
                    "A_date": _format_timestamp(A.date),
                    "B_date": _format_timestamp(B.date),
                    "C_date": _format_timestamp(C.date),
                    "O_price": round(O.price, 4),
                    "X_price": round(X.price, 4),
                    "A_price": round(A.price, 4),
                    "B_price": round(B.price, 4),
                    "C_price": round(C.price, 4),
                    "XA/OX": round(xa_ratio, 4),
                    "AB/XA": round(ab_ratio, 4),
                    "BC/AB": round(bc_ratio, 4),
                    "pivot_start_index": i,
                }
            )

    return pd.DataFrame(rows)


def scan_ticker(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
    lookback: int = 5,
    min_move_pct: float = 0.03,
    tolerance: float = 0.04,
    direction: PatternDirection = "Bullish",
    pivot_mode: PivotMode = "High/Low",
    ratios: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[Pivot]]:
    df = download_prices(ticker, period=period, interval=interval)
    raw = find_raw_pivots(df, lookback=lookback, mode=pivot_mode)
    pivots = clean_pivots(raw, min_move_pct=min_move_pct)
    matches = scan_oxabc_pattern(pivots, ratios=ratios, tolerance=tolerance, direction=direction)
    if not matches.empty:
        matches.insert(0, "ticker", ticker)
    return matches, df, pivots


def scan_many(
    tickers: Iterable[str],
    period: str = "2y",
    interval: str = "1d",
    lookback: int = 5,
    min_move_pct: float = 0.03,
    tolerance: float = 0.04,
    direction: PatternDirection = "Bullish",
    pivot_mode: PivotMode = "High/Low",
    ratios: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    frames: list[pd.DataFrame] = []
    errors: dict[str, str] = {}
    for ticker in tickers:
        try:
            matches, _, _ = scan_ticker(
                ticker,
                period=period,
                interval=interval,
                lookback=lookback,
                min_move_pct=min_move_pct,
                tolerance=tolerance,
                direction=direction,
                pivot_mode=pivot_mode,
                ratios=ratios,
            )
            if not matches.empty:
                frames.append(matches)
        except Exception as exc:  # safe to show in app UI
            errors[ticker] = str(exc)

    if frames:
        return pd.concat(frames, ignore_index=True), errors
    return pd.DataFrame(), errors
