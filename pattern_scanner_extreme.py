from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

PatternDirection = Literal["Bullish", "Bearish", "Both"]
PivotMode = Literal["High/Low", "Close"]
PatternStatus = Literal["BC_FORMING", "NEAR_COMPLETE", "COMPLETE"]

DEFAULT_MONTHS = 3
DEFAULT_INTERVAL = "1h"

DEFAULT_RATIOS: dict[str, tuple[float, float]] = {
    "XA_over_OX": (0.50, 0.618),
    "AB_over_XA": (1.13, 1.618),
    "BC_over_AB": (1.618, 2.27),
}

# Optional saved universe. The app also supports live US index/universe lists.
CONFIGURED_TICKERS: list[str] = ['360ONE.NS', 'BAJAJHLDNG.NS', 'BDL.NS', 'GODREJPROP.NS', 'IEX.NS', 'INDUSINDBK.NS', 'JINDALSTEL.NS', 'LTF.NS', 'MCX.NS', 'NAUKRI.NS', 'OFSS.NS', 'OIL.NS', 'PATANJALI.NS', 'PETRONET.NS', 'SBILIFE.NS', 'SBIN.NS', 'SHRIRAMFIN.NS', 'UPL.NS', 'ANGELONE.NS', 'BANKINDIA.NS', 'BRITANNIA.NS', 'COFORGE.NS', 'COLPAL.NS', 'DIXON.NS', 'ICICIGI.NS', 'INFY.NS', 'NESTLEIND.NS', 'NIFTYNXT50.NS', 'PAGEIND.NS', 'PGEL.NS', 'PIDILITIND.NS', 'PNB.NS', 'SONACOMS.NS', 'WAAREEENER.NS', 'BHARATFORG.NS', 'CDSL.NS', 'CONCOR.NS', 'DELHIVERY.NS', 'HINDZINC.NS', 'KALYANKJIL.NS', 'NYKAA.NS', 'PREMIERENE.NS', 'SOLARINDS.NS', 'AMBUJACEM.NS', 'BLUESTARCO.NS', 'CHOLAFIN.NS', 'EICHERMOT.NS', 'GRASIM.NS', 'IDFCFIRSTB.NS', 'MPHASIS.NS', 'NBCC.NS', 'PAYTM.NS', 'RBLBANK.NS', 'SRF.NS', 'SUNPHARMA.NS', 'APLAPOLLO.NS', 'BHEL.NS', 'BOSCHLTD.NS', 'CROMPTON.NS', 'CUMMINSIND.NS', 'ETERNAL.NS', 'LUPIN.NS', 'SBICARD.NS', 'WIPRO.NS', 'ADANIGREEN.NS', 'APOLLOHOSP.NS', 'DABUR.NS', 'DIVISLAB.NS', 'FORTIS.NS', 'HAL.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'INDUSTOWER.NS', 'LICI.NS', 'LT.NS', 'MAXHEALTH.NS', 'MFSL.NS', 'MIDCPNIFTY.NS', 'PFC.NS', 'CGPOWER.NS', 'COALINDIA.NS', 'FINNIFTY.NS', 'HINDALCO.NS', 'INDIGO.NS', 'INOXWIND.NS', 'IRFC.NS', 'RELIANCE.NS', 'TATAPOWER.NS', 'TVSMOTOR.NS', 'ZYDUSLIFE.NS', 'BANKBARODA.NS', 'BANKNIFTY.NS', 'BEL.NS', 'HEROMOTOCO.NS', 'IREDA.NS', 'ITC.NS', 'JSWENERGY.NS', 'M&M.NS', 'NHPC.NS', 'NIFTY.NS', 'ONGC.NS', 'PHOENIXLTD.NS', 'SWIGGY.NS', 'TIINDIA.NS', 'ULTRACEMCO.NS', 'VEDL.NS', 'ADANIPORTS.NS', 'ASTRAL.NS', 'BHARTIARTL.NS', 'BPCL.NS', 'DRREDDY.NS', 'EXIDEIND.NS', 'HAVELLS.NS', 'HINDPETRO.NS', 'KAYNES.NS', 'MANKIND.NS', 'SHREECEM.NS', 'UNIONBANK.NS', 'AXISBANK.NS', 'BANDHANBNK.NS', 'DALBHARAT.NS', 'GMRAIRPORT.NS', 'HCLTECH.NS', 'NTPC.NS', 'PIIND.NS', 'PNBHOUSING.NS', 'SAMMAANCAP.NS', 'SIEMENS.NS', 'TITAN.NS', 'UNITDSPR.NS', 'ABCAPITAL.NS', 'ADANIENSOL.NS', 'ASIANPAINT.NS', 'AUBANK.NS', 'BIOCON.NS', 'CANBK.NS', 'GODREJCP.NS', 'IDEA.NS', 'INDIANB.NS', 'IOC.NS', 'KOTAKBANK.NS', 'POLYCAB.NS', 'POWERGRID.NS', 'RECLTD.NS', 'SAIL.NS', 'TATAELXSI.NS', 'TATASTEEL.NS', 'TECHM.NS', 'TORNTPHARM.NS', 'TRENT.NS', 'ASHOKLEY.NS', 'FEDERALBNK.NS', 'ICICIBANK.NS', 'KPITTECH.NS', 'MAZDOCK.NS', 'MUTHOOTFIN.NS', 'NMDC.NS', 'SUPREMEIND.NS', 'VBL.NS', 'ALKEM.NS', 'BAJAJ-AUTO.NS', 'BAJAJFINSV.NS', 'BAJFINANCE.NS', 'CAMS.NS', 'CIPLA.NS', 'INDHOTEL.NS', 'JIOFIN.NS', 'JSWSTEEL.NS', 'JUBLFOOD.NS', 'KFINTECH.NS', 'LAURUSLABS.NS', 'LTM.NS', 'MOTHERSON.NS', 'NATIONALUM.NS', 'NUVAMA.NS', 'OBEROIRLTY.NS', 'POLICYBZR.NS', 'POWERINDIA.NS', 'TMPV.NS', 'UNOMINDA.NS', 'YESBANK.NS', 'ABB.NS', 'ADANIENT.NS', 'AMBER.NS', 'AUROPHARMA.NS', 'BSE.NS', 'DLF.NS', 'GAIL.NS', 'HDFCAMC.NS', 'HINDUNILVR.NS', 'ICICIPRULI.NS', 'KEI.NS', 'LICHSGFIN.NS', 'LODHA.NS', 'MANAPPURAM.NS', 'PRESTIGE.NS', 'RVNL.NS', 'SUZLON.NS', 'TATACONSUM.NS', 'VOLTAS.NS', 'PERSISTENT.NS', 'TCS.NS']

DOW_30_TICKERS: list[str] = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT",
]


@dataclass(frozen=True)
class Pivot:
    index: int
    date: pd.Timestamp
    price: float
    kind: str  # "H" or "L"


def _yahoo_symbol(symbol: str) -> str:
    """Convert symbols from index lists into Yahoo Finance format."""
    return str(symbol).strip().upper().replace(".", "-")


def extract_ticker(yahoo_url_or_ticker: str) -> str:
    """Extract a ticker from a Yahoo Finance URL or return a cleaned ticker."""
    text = yahoo_url_or_ticker.strip()
    if not text:
        raise ValueError("Empty ticker or URL")

    if "finance.yahoo.com" not in text.lower() and "/quote/" not in text.lower():
        return _yahoo_symbol(text)

    parsed = urlparse(text)
    path_parts = [unquote(p) for p in parsed.path.split("/") if p]
    for key in ("quote", "chart"):
        if key in path_parts:
            idx = path_parts.index(key)
            if idx + 1 < len(path_parts):
                return _yahoo_symbol(path_parts[idx + 1])

    query = parse_qs(parsed.query)
    for key in ("p", "symbol"):
        if key in query and query[key]:
            return _yahoo_symbol(query[key][0])

    match = re.search(r"/quote/([^/?#]+)", text, re.IGNORECASE)
    if match:
        return _yahoo_symbol(unquote(match.group(1)))

    raise ValueError(f"Could not extract a ticker from: {text}")


def parse_inputs(raw_text: str) -> list[str]:
    """Parse URLs/tickers separated by newlines, spaces, commas, or tabs."""
    if not raw_text:
        return []
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


def _dedupe(tickers: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for ticker in tickers:
        value = _yahoo_symbol(ticker)
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


class _SimpleTableParser(HTMLParser):
    """Small stdlib HTML table parser so index lists do not require lxml."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_table and self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            value = data.strip()
            if value:
                self._current_cell.append(value)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._current_cell = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = []
            self._in_row = False
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = []
            self._in_table = False


def _fetch_html_tables(url: str) -> list[pd.DataFrame]:
    """Return HTML tables using only Python stdlib parsing."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = _SimpleTableParser()
    parser.feed(html)

    frames: list[pd.DataFrame] = []
    for table in parser.tables:
        cleaned = [[unescape(cell).strip() for cell in row] for row in table if row]
        if len(cleaned) < 2:
            continue
        header = cleaned[0]
        rows = cleaned[1:]
        width = len(header)
        normalized_rows = []
        for row in rows:
            if len(row) < width:
                row = row + [""] * (width - len(row))
            elif len(row) > width:
                row = row[:width]
            normalized_rows.append(row)
        try:
            frames.append(pd.DataFrame(normalized_rows, columns=header))
        except Exception:
            continue
    return frames


def _find_symbol_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        low = str(col).strip().lower()
        if low in {"symbol", "ticker"} or "ticker" in low:
            return str(col)
    return None


def get_sp500_tickers() -> list[str]:
    """Fetch current S&P 500 constituents without requiring lxml."""
    tables = _fetch_html_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    for df in tables:
        symbol_col = _find_symbol_column(df)
        if symbol_col and len(df) > 400:
            return _dedupe(df[symbol_col].dropna().astype(str).tolist())
    raise ValueError("Could not load S&P 500 symbols")


def get_nasdaq100_tickers() -> list[str]:
    """Fetch current Nasdaq-100 constituents without requiring lxml."""
    tables = _fetch_html_tables("https://en.wikipedia.org/wiki/Nasdaq-100")
    for df in tables:
        symbol_col = _find_symbol_column(df)
        if symbol_col and len(df) >= 90:
            return _dedupe(df[symbol_col].dropna().astype(str).tolist())
    raise ValueError("Could not load Nasdaq-100 symbols")


def _looks_like_common_stock(name: str) -> bool:
    lowered = str(name).lower()
    blocked = (
        " warrant", " warrants", " unit", " units", " right", " rights",
        " preferred", " preference", " depositary", " note", " notes",
        " bond", " debenture", " etf", " fund", " trust", " etn",
        " acquisition corp", " spac",
    )
    return not any(token in lowered for token in blocked)


def get_all_us_common_stock_tickers() -> list[str]:
    """Fetch US-listed common-stock-like symbols from Nasdaq Trader symbol directories."""
    urls = [
        "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    ]
    symbols: list[str] = []

    for url in urls:
        df = pd.read_csv(url, sep="|")
        df = df.dropna(how="all")
        if "File Creation Time" in df.columns:
            df = df[df["File Creation Time"].isna()]

        if "Test Issue" in df.columns:
            df = df[df["Test Issue"].astype(str).str.upper().eq("N")]
        if "ETF" in df.columns:
            df = df[df["ETF"].astype(str).str.upper().eq("N")]

        symbol_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
        name_col = "Security Name" if "Security Name" in df.columns else "Security Name"
        if symbol_col not in df.columns:
            continue

        if name_col in df.columns:
            df = df[df[name_col].fillna("").map(_looks_like_common_stock)]

        for symbol in df[symbol_col].dropna().astype(str):
            # Skip odd symbols that usually do not download cleanly from Yahoo.
            if "$" in symbol or "^" in symbol:
                continue
            symbols.append(symbol)

    return _dedupe(symbols)


def get_tickers_for_universe(universe: str, custom_text: str = "") -> list[str]:
    """Return tickers for the selected app universe."""
    choice = universe.strip().lower()
    if choice == "s&p 500":
        return get_sp500_tickers()
    if choice == "nasdaq-100":
        return get_nasdaq100_tickers()
    if choice == "dow 30":
        return DOW_30_TICKERS.copy()
    if choice == "all us-listed common stocks":
        return get_all_us_common_stock_tickers()
    if choice == "configured list":
        return CONFIGURED_TICKERS.copy()
    if choice == "custom tickers":
        return parse_inputs(custom_text)
    raise ValueError(f"Unknown stock universe: {universe}")


def _flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        first = list(df.columns.get_level_values(0))
        second = list(df.columns.get_level_values(1))
        ohlcv = {"Open", "High", "Low", "Close", "Volume"}
        if any(c in ohlcv for c in first):
            df.columns = df.columns.get_level_values(0)
        elif any(c in ohlcv for c in second):
            df.columns = df.columns.get_level_values(1)
        else:
            df.columns = [str(c[0]) for c in df.columns]
    return df


def download_prices(ticker: str, months: int = DEFAULT_MONTHS, interval: str = DEFAULT_INTERVAL) -> pd.DataFrame:
    """Download OHLCV data from Yahoo Finance through yfinance."""
    ticker = _yahoo_symbol(ticker)
    end = datetime.now()
    start = end - timedelta(days=max(int(months), 1) * 30)

    df = yf.download(
        ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise ValueError("No price data returned from Yahoo Finance")

    df = _flatten_yfinance_columns(df)
    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected OHLC columns: {missing}")
    if "Volume" not in df.columns:
        df["Volume"] = 0

    df = df.reset_index()
    date_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={date_col: "Date"})
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if len(df) < 50:
        raise ValueError(f"Insufficient data: only {len(df)} candles")
    return df.sort_values("Date").reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add moving averages and RSI for chart display."""
    out = df.copy()
    close = out["Close"].astype(float)

    # Hourly MAs are true candle-count MAs on the selected interval.
    out["HMA_50"] = close.rolling(window=50).mean()
    out["HMA_100"] = close.rolling(window=100).mean()
    out["HMA_200"] = close.rolling(window=200).mean()

    # Daily/weekly approximations for a 1-hour chart. They still work as longer overlays.
    out["DMA_50"] = close.rolling(window=325).mean()
    out["DMA_100"] = close.rolling(window=650).mean()
    out["DMA_200"] = close.rolling(window=1300).mean()
    out["WMA_50"] = close.rolling(window=1625).mean()
    out["WMA_100"] = close.rolling(window=3250).mean()
    out["WMA_200"] = close.rolling(window=6500).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, pd.NA)
    out["RSI"] = (100 - (100 / (1 + rs))).fillna(50)
    return out


def find_raw_pivots(df: pd.DataFrame, lookback: int = 5, mode: PivotMode = "High/Low") -> list[Pivot]:
    """Find local swing highs/lows."""
    if lookback < 1:
        raise ValueError("lookback must be at least 1")
    if len(df) < lookback * 2 + 1:
        return []

    pivots: list[Pivot] = []
    if mode == "Close":
        values = df["Close"].astype(float).to_numpy()
        for i in range(lookback, len(df) - lookback):
            window = values[i - lookback : i + lookback + 1]
            price = values[i]
            if price == max(window):
                pivots.append(Pivot(i, pd.Timestamp(df.loc[i, "Date"]), float(price), "H"))
            elif price == min(window):
                pivots.append(Pivot(i, pd.Timestamp(df.loc[i, "Date"]), float(price), "L"))
        return pivots

    highs = df["High"].astype(float).to_numpy()
    lows = df["Low"].astype(float).to_numpy()
    for i in range(lookback, len(df) - lookback):
        high_window = highs[i - lookback : i + lookback + 1]
        low_window = lows[i - lookback : i + lookback + 1]
        if highs[i] == max(high_window):
            pivots.append(Pivot(i, pd.Timestamp(df.loc[i, "Date"]), float(highs[i]), "H"))
        if lows[i] == min(low_window):
            pivots.append(Pivot(i, pd.Timestamp(df.loc[i, "Date"]), float(lows[i]), "L"))
    pivots.sort(key=lambda p: p.index)
    return pivots


def clean_pivots(pivots: Iterable[Pivot], min_move_pct: float = 0.005) -> list[Pivot]:
    """Keep alternating high/low pivots and ignore tiny swings."""
    ordered = sorted(list(pivots), key=lambda p: p.index)
    if not ordered:
        return []

    cleaned: list[Pivot] = []
    for p in ordered:
        if not cleaned:
            cleaned.append(p)
            continue

        last = cleaned[-1]
        if p.kind == last.kind:
            if p.kind == "H" and p.price >= last.price:
                cleaned[-1] = p
            elif p.kind == "L" and p.price <= last.price:
                cleaned[-1] = p
            continue

        move = abs(p.price - last.price) / max(abs(last.price), 1e-12)
        if move >= min_move_pct:
            cleaned.append(p)
        else:
            if p.kind == "H" and p.price > last.price:
                cleaned[-1] = p
            elif p.kind == "L" and p.price < last.price:
                cleaned[-1] = p
    return cleaned


def _direction_from_kinds(kinds: list[str]) -> str | None:
    if kinds == ["H", "L", "H", "L", "H"]:
        return "Bullish"
    if kinds == ["L", "H", "L", "H", "L"]:
        return "Bearish"
    return None


def _partial_direction_from_kinds(kinds: list[str]) -> str | None:
    if kinds == ["H", "L", "H", "L"]:
        return "Bullish"
    if kinds == ["L", "H", "L", "H"]:
        return "Bearish"
    return None


def _direction_allowed(found: str, requested: PatternDirection) -> bool:
    return requested == "Both" or found == requested


def _structure_for_direction(direction: str) -> str:
    """Map the detected direction to the visual W/M structure shown in the chart."""
    if direction == "Bullish":
        return "W"
    if direction == "Bearish":
        return "M"
    return ""


def _o_extreme_for_direction(direction: str) -> str:
    """Describe the required O-point position inside the detected wave."""
    if direction == "Bullish":
        return "Highest"
    if direction == "Bearish":
        return "Lowest"
    return ""


def _o_is_outer_extreme(points: list[Pivot], direction: str) -> bool:
    """Require O to be the outer high/low of the whole O-X-A-B-C wave.

    This prevents patterns where O is only a middle swing inside a larger move.
    For the W-style bullish shape, O must be the highest point of the wave.
    For the M-style bearish shape, O must be the lowest point of the wave.
    """
    if not points:
        return False

    o_price = float(points[0].price)
    prices = [float(p.price) for p in points]
    eps = max(abs(o_price), 1.0) * 1e-9

    if direction == "Bullish":
        return o_price >= max(prices) - eps
    if direction == "Bearish":
        return o_price <= min(prices) + eps
    return False


def _ratio_in_range(value: float, low: float, high: float, tolerance: float = 0.0) -> bool:
    return low * (1 - tolerance) <= value <= high * (1 + tolerance)


def _format_timestamp(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).isoformat(sep=" ", timespec="minutes")


def _legs(points: list[Pivot], direction: str) -> tuple[float, float, float] | None:
    O, X, A, B, C = points
    if direction == "Bullish":
        ox = O.price - X.price
        xa = A.price - X.price
        ab = A.price - B.price
        bc = C.price - B.price
    elif direction == "Bearish":
        ox = X.price - O.price
        xa = X.price - A.price
        ab = B.price - A.price
        bc = B.price - C.price
    else:
        return None
    if min(ox, xa, ab, bc) <= 0:
        return None
    return ox, xa, ab, bc


def _target_c_range(B_price: float, ab: float, bc_low: float, bc_high: float, direction: str) -> tuple[float, float]:
    if direction == "Bullish":
        prices = [B_price + ab * bc_low, B_price + ab * bc_high]
    else:
        prices = [B_price - ab * bc_low, B_price - ab * bc_high]
    return min(prices), max(prices)


def _score(xa_ratio: float, ab_ratio: float, bc_ratio: float, ratios: dict[str, tuple[float, float]], status: str) -> float:
    targets = {
        "XA_over_OX": sum(ratios["XA_over_OX"]) / 2,
        "AB_over_XA": sum(ratios["AB_over_XA"]) / 2,
        "BC_over_AB": sum(ratios["BC_over_AB"]) / 2,
    }
    deviation = (
        abs(xa_ratio - targets["XA_over_OX"]) / targets["XA_over_OX"]
        + abs(ab_ratio - targets["AB_over_XA"]) / targets["AB_over_XA"]
        + abs(bc_ratio - targets["BC_over_AB"]) / targets["BC_over_AB"]
    )
    base = 100 if status == "COMPLETE" else 90 if status == "NEAR_COMPLETE" else 75
    return round(max(0, base - deviation * 25), 2)


def _row(
    ticker: str,
    direction: str,
    status: str,
    points: list[Pivot],
    ratios_actual: tuple[float, float, float],
    target_c: tuple[float, float],
    ratios: dict[str, tuple[float, float]],
) -> dict:
    O, X, A, B, C = points
    xa_ratio, ab_ratio, bc_ratio = ratios_actual
    bc_low = ratios["BC_over_AB"][0]
    return {
        "ticker": ticker,
        "direction": direction,
        "status": status,
        "structure": _structure_for_direction(direction),
        "O_extreme": _o_extreme_for_direction(direction),
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
        "BC Progress %": round((bc_ratio / bc_low) * 100, 1),
        "Target C Low": round(target_c[0], 4),
        "Target C High": round(target_c[1], 4),
        "score": _score(xa_ratio, ab_ratio, bc_ratio, ratios, status),
        "O_index": O.index,
        "X_index": X.index,
        "A_index": A.index,
        "B_index": B.index,
        "C_index": C.index,
    }


def scan_oxabc_patterns(
    ticker: str,
    df: pd.DataFrame,
    pivots: list[Pivot],
    ratios: dict[str, tuple[float, float]] | None = None,
    tolerance: float = 0.04,
    direction: PatternDirection = "Both",
    forming_threshold: float = 0.75,
    near_complete_threshold: float = 0.90,
    recent_candles: int = 120,
) -> pd.DataFrame:
    """Scan for completed/forming O-X-A-B-C patterns with strict O-wave extremes."""
    ratios = ratios or DEFAULT_RATIOS
    rows: list[dict] = []
    recent_start = max(0, len(df) - max(int(recent_candles), 1))
    xa_low, xa_high = ratios["XA_over_OX"]
    ab_low, ab_high = ratios["AB_over_XA"]
    bc_low, bc_high = ratios["BC_over_AB"]

    # Completed O-X-A-B-C patterns: C is a confirmed pivot.
    for i in range(len(pivots) - 4):
        points = pivots[i : i + 5]
        found_direction = _direction_from_kinds([p.kind for p in points])
        if found_direction is None or not _direction_allowed(found_direction, direction):
            continue
        if points[-1].index < recent_start:
            continue
        if not _o_is_outer_extreme(points, found_direction):
            continue

        leg_values = _legs(points, found_direction)
        if leg_values is None:
            continue
        ox, xa, ab, bc = leg_values
        xa_ratio, ab_ratio, bc_ratio = xa / ox, ab / xa, bc / ab

        if not _ratio_in_range(xa_ratio, xa_low, xa_high, tolerance):
            continue
        if not _ratio_in_range(ab_ratio, ab_low, ab_high, tolerance):
            continue
        if not _ratio_in_range(bc_ratio, bc_low, bc_high, tolerance):
            continue

        target_c = _target_c_range(points[3].price, ab, bc_low, bc_high, found_direction)
        rows.append(_row(ticker, found_direction, "COMPLETE", points, (xa_ratio, ab_ratio, bc_ratio), target_c, ratios))

    # Forming O-X-A-B-C patterns: O-X-A-B is confirmed, C is current close.
    if len(df) > 0:
        current = Pivot(
            index=len(df) - 1,
            date=pd.Timestamp(df.iloc[-1]["Date"]),
            price=float(df.iloc[-1]["Close"]),
            kind="H",  # replaced below for bearish
        )
        for i in range(len(pivots) - 3):
            base_points = pivots[i : i + 4]
            found_direction = _partial_direction_from_kinds([p.kind for p in base_points])
            if found_direction is None or not _direction_allowed(found_direction, direction):
                continue
            if base_points[-1].index < recent_start:
                continue
            if base_points[-1].index >= len(df) - 1:
                continue

            O, X, A, B = base_points
            if found_direction == "Bullish":
                C = Pivot(current.index, current.date, current.price, "H")
            else:
                C = Pivot(current.index, current.date, current.price, "L")
            points = [O, X, A, B, C]
            if not _o_is_outer_extreme(points, found_direction):
                continue

            leg_values = _legs(points, found_direction)
            if leg_values is None:
                continue
            ox, xa, ab, bc = leg_values
            xa_ratio, ab_ratio, bc_ratio = xa / ox, ab / xa, bc / ab

            if not _ratio_in_range(xa_ratio, xa_low, xa_high, tolerance):
                continue
            if not _ratio_in_range(ab_ratio, ab_low, ab_high, tolerance):
                continue
            if bc_ratio > bc_high * (1 + tolerance):
                continue

            progress = bc_ratio / bc_low
            if progress < forming_threshold:
                continue

            status = "NEAR_COMPLETE" if progress >= near_complete_threshold else "BC_FORMING"
            target_c = _target_c_range(B.price, ab, bc_low, bc_high, found_direction)
            rows.append(_row(ticker, found_direction, status, points, (xa_ratio, ab_ratio, bc_ratio), target_c, ratios))

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result = remove_duplicate_patterns(result)
    return result.sort_values(by=["score", "BC Progress %", "C_date"], ascending=[False, False, False]).reset_index(drop=True)


def remove_duplicate_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the best row when the same O-X-A-B-C appears more than once."""
    if df.empty:
        return df
    work = df.copy()
    status_rank = {"COMPLETE": 3, "NEAR_COMPLETE": 2, "BC_FORMING": 1}
    work["_status_rank"] = work["status"].map(status_rank).fillna(0)
    work = work.sort_values(["_status_rank", "score", "BC Progress %"], ascending=[False, False, False])
    key_cols = ["ticker", "direction", "O_index", "X_index", "A_index", "B_index", "C_index"]
    work = work.drop_duplicates(subset=key_cols, keep="first")

    # If the same O-X-A-B has both forming and complete candidates, keep the stronger one.
    key_cols_base = ["ticker", "direction", "O_index", "X_index", "A_index", "B_index"]
    work = work.drop_duplicates(subset=key_cols_base, keep="first")
    return work.drop(columns=["_status_rank"], errors="ignore")


def scan_ticker(
    ticker: str,
    months: int = DEFAULT_MONTHS,
    interval: str = DEFAULT_INTERVAL,
    lookback: int = 5,
    min_move_pct: float = 0.005,
    tolerance: float = 0.04,
    direction: PatternDirection = "Both",
    pivot_mode: PivotMode = "High/Low",
    ratios: dict[str, tuple[float, float]] | None = None,
    forming_threshold: float = 0.75,
    near_complete_threshold: float = 0.90,
    recent_candles: int = 120,
) -> tuple[pd.DataFrame, pd.DataFrame, list[Pivot]]:
    ticker = _yahoo_symbol(ticker)
    df = download_prices(ticker, months=months, interval=interval)
    raw_pivots = find_raw_pivots(df, lookback=lookback, mode=pivot_mode)
    pivots = clean_pivots(raw_pivots, min_move_pct=min_move_pct)
    matches = scan_oxabc_patterns(
        ticker=ticker,
        df=df,
        pivots=pivots,
        ratios=ratios,
        tolerance=tolerance,
        direction=direction,
        forming_threshold=forming_threshold,
        near_complete_threshold=near_complete_threshold,
        recent_candles=recent_candles,
    )
    return matches, df, pivots


def scan_many(
    tickers: Iterable[str],
    months: int = DEFAULT_MONTHS,
    interval: str = DEFAULT_INTERVAL,
    lookback: int = 5,
    min_move_pct: float = 0.005,
    tolerance: float = 0.04,
    direction: PatternDirection = "Both",
    pivot_mode: PivotMode = "High/Low",
    ratios: dict[str, tuple[float, float]] | None = None,
    forming_threshold: float = 0.75,
    near_complete_threshold: float = 0.90,
    recent_candles: int = 120,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    frames: list[pd.DataFrame] = []
    errors: dict[str, str] = {}
    ticker_list = _dedupe(tickers)
    total = len(ticker_list)

    for i, ticker in enumerate(ticker_list, start=1):
        if progress_callback:
            progress_callback(i, total, ticker)
        try:
            matches, _, _ = scan_ticker(
                ticker,
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
            )
            if not matches.empty:
                frames.append(matches)
        except Exception as exc:
            errors[ticker] = str(exc)

    if frames:
        return pd.concat(frames, ignore_index=True), errors
    return pd.DataFrame(), errors
