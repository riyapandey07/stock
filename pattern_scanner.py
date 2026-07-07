from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import yfinance as yf

PatternDirection = Literal["BULLISH", "BEARISH", "Both"]
PatternType = Literal["COMPLETE", "NEAR_COMPLETE", "PARTIAL_XABC"]

# Same stock universe used in the TXT/Dash version.
STOCK_TICKERS: list[str] = ['360ONE.NS', 'BAJAJHLDNG.NS', 'BDL.NS', 'GODREJPROP.NS', 'IEX.NS', 'INDUSINDBK.NS', 'JINDALSTEL.NS', 'LTF.NS', 'MCX.NS', 'NAUKRI.NS', 'OFSS.NS', 'OIL.NS', 'PATANJALI.NS', 'PETRONET.NS', 'SBILIFE.NS', 'SBIN.NS', 'SHRIRAMFIN.NS', 'UPL.NS', 'ANGELONE.NS', 'BANKINDIA.NS', 'BRITANNIA.NS', 'COFORGE.NS', 'COLPAL.NS', 'DIXON.NS', 'ICICIGI.NS', 'INFY.NS', 'NESTLEIND.NS', 'NIFTYNXT50.NS', 'PAGEIND.NS', 'PGEL.NS', 'PIDILITIND.NS', 'PNB.NS', 'SONACOMS.NS', 'WAAREEENER.NS', 'BHARATFORG.NS', 'CDSL.NS', 'CONCOR.NS', 'DELHIVERY.NS', 'HINDZINC.NS', 'KALYANKJIL.NS', 'NYKAA.NS', 'PREMIERENE.NS', 'SOLARINDS.NS', 'AMBUJACEM.NS', 'BLUESTARCO.NS', 'CHOLAFIN.NS', 'EICHERMOT.NS', 'GRASIM.NS', 'IDFCFIRSTB.NS', 'MPHASIS.NS', 'NBCC.NS', 'PAYTM.NS', 'RBLBANK.NS', 'SRF.NS', 'SUNPHARMA.NS', 'APLAPOLLO.NS', 'BHEL.NS', 'BOSCHLTD.NS', 'CROMPTON.NS', 'CUMMINSIND.NS', 'ETERNAL.NS', 'LUPIN.NS', 'SBICARD.NS', 'WIPRO.NS', 'ADANIGREEN.NS', 'APOLLOHOSP.NS', 'DABUR.NS', 'DIVISLAB.NS', 'FORTIS.NS', 'HAL.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'INDUSTOWER.NS', 'LICI.NS', 'LT.NS', 'MAXHEALTH.NS', 'MFSL.NS', 'MIDCPNIFTY.NS', 'PFC.NS', 'CGPOWER.NS', 'COALINDIA.NS', 'FINNIFTY.NS', 'HINDALCO.NS', 'INDIGO.NS', 'INOXWIND.NS', 'IRFC.NS', 'RELIANCE.NS', 'TATAPOWER.NS', 'TVSMOTOR.NS', 'ZYDUSLIFE.NS', 'BANKBARODA.NS', 'BANKNIFTY.NS', 'BEL.NS', 'HEROMOTOCO.NS', 'IREDA.NS', 'ITC.NS', 'JSWENERGY.NS', 'M&M.NS', 'NHPC.NS', 'NIFTY.NS', 'ONGC.NS', 'PHOENIXLTD.NS', 'SWIGGY.NS', 'TIINDIA.NS', 'ULTRACEMCO.NS', 'VEDL.NS', 'ADANIPORTS.NS', 'ASTRAL.NS', 'BHARTIARTL.NS', 'BPCL.NS', 'DRREDDY.NS', 'EXIDEIND.NS', 'HAVELLS.NS', 'HINDPETRO.NS', 'KAYNES.NS', 'MANKIND.NS', 'SHREECEM.NS', 'UNIONBANK.NS', 'AXISBANK.NS', 'BANDHANBNK.NS', 'DALBHARAT.NS', 'GMRAIRPORT.NS', 'HCLTECH.NS', 'NTPC.NS', 'PIIND.NS', 'PNBHOUSING.NS', 'SAMMAANCAP.NS', 'SIEMENS.NS', 'TITAN.NS', 'UNITDSPR.NS', 'ABCAPITAL.NS', 'ADANIENSOL.NS', 'ASIANPAINT.NS', 'AUBANK.NS', 'BIOCON.NS', 'CANBK.NS', 'GODREJCP.NS', 'IDEA.NS', 'INDIANB.NS', 'IOC.NS', 'KOTAKBANK.NS', 'POLYCAB.NS', 'POWERGRID.NS', 'RECLTD.NS', 'SAIL.NS', 'TATAELXSI.NS', 'TATASTEEL.NS', 'TECHM.NS', 'TORNTPHARM.NS', 'TRENT.NS', 'ASHOKLEY.NS', 'FEDERALBNK.NS', 'ICICIBANK.NS', 'KPITTECH.NS', 'MAZDOCK.NS', 'MUTHOOTFIN.NS', 'NMDC.NS', 'SUPREMEIND.NS', 'VBL.NS', 'ALKEM.NS', 'BAJAJ-AUTO.NS', 'BAJAJFINSV.NS', 'BAJFINANCE.NS', 'CAMS.NS', 'CIPLA.NS', 'INDHOTEL.NS', 'JIOFIN.NS', 'JSWSTEEL.NS', 'JUBLFOOD.NS', 'KFINTECH.NS', 'LAURUSLABS.NS', 'LTM.NS', 'MOTHERSON.NS', 'NATIONALUM.NS', 'NUVAMA.NS', 'OBEROIRLTY.NS', 'POLICYBZR.NS', 'POWERINDIA.NS', 'TMPV.NS', 'UNOMINDA.NS', 'YESBANK.NS', 'ABB.NS', 'ADANIENT.NS', 'AMBER.NS', 'AUROPHARMA.NS', 'BSE.NS', 'DLF.NS', 'GAIL.NS', 'HDFCAMC.NS', 'HINDUNILVR.NS', 'ICICIPRULI.NS', 'KEI.NS', 'LICHSGFIN.NS', 'LODHA.NS', 'MANAPPURAM.NS', 'PRESTIGE.NS', 'RVNL.NS', 'SUZLON.NS', 'TATACONSUM.NS', 'VOLTAS.NS', 'PERSISTENT.NS', 'TCS.NS']

DEFAULT_MONTHS = 3
DEFAULT_INTERVAL = "1h"

# Same Gartley Fibonacci ranges used in the TXT file.
DEFAULT_RATIOS: dict[str, tuple[float, float]] = {
    "AB_XA": (0.50, 0.618),
    "BC_AB": (1.13, 1.61),
    "CD_BC": (1.61, 2.24),
}


def normalize_direction(direction: str) -> str:
    value = (direction or "Both").strip().upper()
    if value in {"BULLISH", "BULL"}:
        return "BULLISH"
    if value in {"BEARISH", "BEAR"}:
        return "BEARISH"
    return "Both"


def clean_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def parse_inputs(raw_text: str) -> list[str]:
    """Optional helper for custom ticker text boxes."""
    if not raw_text:
        return []
    items = []
    seen: set[str] = set()
    for chunk in raw_text.replace(",", " ").split():
        ticker = clean_ticker(chunk)
        if ticker and ticker not in seen:
            items.append(ticker)
            seen.add(ticker)
    return items


def _flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance may return either (field, ticker) or (ticker, field) columns.
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
    """Download Yahoo Finance OHLCV data using the same 3-month hourly idea as the TXT file."""
    ticker = clean_ticker(ticker)
    end = datetime.now()
    start = end - timedelta(days=int(months) * 30)

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


def check_ratio(actual: float, low: float, high: float) -> bool:
    return low <= actual <= high


def find_swing_points(df: pd.DataFrame, lookback_periods: Iterable[int] = (1, 2, 3, 5)):
    """Find swing highs/lows with the same multi-lookback approach as the TXT file."""
    swing_highs: list[tuple[int, float, pd.Timestamp]] = []
    swing_lows: list[tuple[int, float, pd.Timestamp]] = []

    for lookback in lookback_periods:
        for i in range(lookback, len(df) - lookback):
            high = float(df.loc[i, "High"])
            low = float(df.loc[i, "Low"])

            is_swing_high = True
            for j in range(1, lookback + 1):
                if high < float(df.loc[i - j, "High"]) or high < float(df.loc[i + j, "High"]):
                    is_swing_high = False
                    break
            if is_swing_high and not any(sh[0] == i for sh in swing_highs):
                swing_highs.append((i, high, pd.Timestamp(df.loc[i, "Date"])))

            is_swing_low = True
            for j in range(1, lookback + 1):
                if low > float(df.loc[i - j, "Low"]) or low > float(df.loc[i + j, "Low"]):
                    is_swing_low = False
                    break
            if is_swing_low and not any(sl[0] == i for sl in swing_lows):
                swing_lows.append((i, low, pd.Timestamp(df.loc[i, "Date"])))

    swing_highs.sort(key=lambda x: x[0])
    swing_lows.sort(key=lambda x: x[0])
    return swing_highs, swing_lows


def _target_alignment_score(pattern: dict) -> float:
    ab_target = 0.559
    bc_target = 1.37
    cd_target = 1.925
    total_deviation = (
        abs((pattern["AB_ratio"] / 100) - ab_target)
        + abs((pattern["BC_ratio"] / 100) - bc_target)
        + abs((pattern["CD_ratio"] / 100) - cd_target)
    )
    return float(pattern.get("score", 100)) - (total_deviation * 100)


def remove_duplicate_patterns(all_patterns: list[dict]) -> list[dict]:
    """Same duplicate cleanup idea as the TXT file."""
    if not all_patterns:
        return []

    exact_unique: dict[tuple, dict] = {}
    for pattern in all_patterns:
        exact_key = (
            pattern["X"][0], pattern["A"][0], pattern["B"][0],
            pattern["C"][0], pattern["D"][0], pattern["direction"],
        )
        exact_unique.setdefault(exact_key, pattern)

    abcd_groups: dict[tuple, list[dict]] = {}
    for pattern in exact_unique.values():
        abcd_key = (
            pattern["A"][0], pattern["B"][0], pattern["C"][0],
            pattern["D"][0], pattern["direction"],
        )
        abcd_groups.setdefault(abcd_key, []).append(pattern)

    patterns_after_abcd: list[dict] = []
    for patterns in abcd_groups.values():
        if len(patterns) == 1:
            patterns_after_abcd.append(patterns[0])
        else:
            patterns_after_abcd.append(max(patterns, key=_target_alignment_score))

    xabc_groups: dict[tuple, list[dict]] = {}
    for pattern in patterns_after_abcd:
        xabc_key = (
            pattern["X"][0], pattern["A"][0], pattern["B"][0],
            pattern["C"][0], pattern["direction"],
        )
        xabc_groups.setdefault(xabc_key, []).append(pattern)

    unique_patterns: list[dict] = []
    for patterns in xabc_groups.values():
        if len(patterns) == 1:
            unique_patterns.append(patterns[0])
            continue

        direction = patterns[0]["direction"]
        if direction == "BULLISH":
            unique_patterns.append(min(patterns, key=lambda p: p["D"][1]))
        else:
            unique_patterns.append(max(patterns, key=lambda p: p["D"][1]))

    unique_patterns.sort(key=lambda p: (p["D"][0], p["score"]), reverse=True)
    return unique_patterns


def find_gartley_bullish(df: pd.DataFrame, swing_highs, swing_lows, ratios: dict[str, tuple[float, float]] | None = None) -> list[dict]:
    """Bullish Gartley: X low → A high → B low → C high → D low."""
    ratios = ratios or DEFAULT_RATIOS
    patterns: list[dict] = []
    recent_threshold = max(0, len(df) - 30)

    for X_idx, X_price, X_date in swing_lows[:-2]:
        potential_A = [sh for sh in swing_highs if sh[0] > X_idx]
        for A_idx, A_price, A_date in potential_A:
            if A_price <= X_price:
                continue

            segment_x_to_a = df.iloc[X_idx : A_idx + 1]
            if segment_x_to_a["Low"].min() < X_price or segment_x_to_a["High"].max() > A_price:
                continue

            XA_range = A_price - X_price
            potential_B = [sl for sl in swing_lows if sl[0] > A_idx]
            for B_idx, B_price, B_date in potential_B:
                if B_price >= A_price or B_price <= X_price:
                    continue

                segment_a_to_b = df.iloc[A_idx : B_idx + 1]
                if segment_a_to_b["Low"].min() < B_price:
                    continue
                segment_x_to_b = df.iloc[X_idx : B_idx + 1]
                if segment_x_to_b["High"].max() > A_price:
                    continue

                AB_range = A_price - B_price
                AB_ratio = AB_range / XA_range
                if not check_ratio(AB_ratio, *ratios["AB_XA"]):
                    continue

                potential_C = [sh for sh in swing_highs if sh[0] > B_idx]
                for C_idx, C_price, C_date in potential_C:
                    if C_price <= B_price:
                        continue

                    segment_b_to_c = df.iloc[B_idx : C_idx + 1]
                    if segment_b_to_c["High"].max() > C_price:
                        continue
                    segment_a_to_c = df.iloc[A_idx : C_idx + 1]
                    if segment_a_to_c["Low"].min() < B_price:
                        continue

                    BC_range = C_price - B_price
                    BC_ratio = BC_range / AB_range
                    if not check_ratio(BC_ratio, *ratios["BC_AB"]):
                        continue

                    if C_idx >= recent_threshold:
                        current_price = float(df.iloc[-1]["Close"])
                        if current_price < C_price:
                            CD_current = C_price - current_price
                            CD_progress = CD_current / BC_range
                            if CD_progress >= 0.75:
                                segment_b_to_now = df.iloc[B_idx:]
                                if segment_b_to_now["High"].max() > C_price:
                                    continue
                                if segment_b_to_now["Low"].min() < B_price:
                                    continue
                                patterns.append({
                                    "direction": "BULLISH",
                                    "type": "PARTIAL_XABC",
                                    "X": (X_idx, X_price, X_date),
                                    "A": (A_idx, A_price, A_date),
                                    "B": (B_idx, B_price, B_date),
                                    "C": (C_idx, C_price, C_date),
                                    "D": (len(df) - 1, current_price, pd.Timestamp(df.iloc[-1]["Date"])),
                                    "AB_ratio": AB_ratio * 100,
                                    "BC_ratio": BC_ratio * 100,
                                    "CD_ratio": CD_progress * 100,
                                    "score": 70,
                                })

                    potential_D = [sl for sl in swing_lows if sl[0] > C_idx]
                    for D_idx, D_price, D_date in potential_D:
                        if C_idx < recent_threshold and D_idx < recent_threshold:
                            continue
                        if D_price >= C_price:
                            continue

                        segment_c_to_d = df.iloc[C_idx : D_idx + 1]
                        if segment_c_to_d["Low"].min() < D_price:
                            continue
                        segment_b_to_d = df.iloc[B_idx : D_idx + 1]
                        if segment_b_to_d["High"].max() > C_price:
                            continue

                        CD_range = C_price - D_price
                        CD_ratio = CD_range / BC_range
                        cd_complete = check_ratio(CD_ratio, *ratios["CD_BC"])
                        cd_near_complete = 0.75 <= CD_ratio < ratios["CD_BC"][0]
                        if not (cd_complete or cd_near_complete):
                            continue

                        data_after_D = df.iloc[D_idx + 1 :]
                        if len(data_after_D) > 0:
                            fall_from_D = D_price - data_after_D["Low"].min()
                            if fall_from_D > (CD_range * 0.5):
                                continue

                        patterns.append({
                            "direction": "BULLISH",
                            "type": "COMPLETE" if cd_complete else "NEAR_COMPLETE",
                            "X": (X_idx, X_price, X_date),
                            "A": (A_idx, A_price, A_date),
                            "B": (B_idx, B_price, B_date),
                            "C": (C_idx, C_price, C_date),
                            "D": (D_idx, D_price, D_date),
                            "AB_ratio": AB_ratio * 100,
                            "BC_ratio": BC_ratio * 100,
                            "CD_ratio": CD_ratio * 100,
                            "score": 100 if cd_complete else 85,
                        })
    return patterns


def find_gartley_bearish(df: pd.DataFrame, swing_highs, swing_lows, ratios: dict[str, tuple[float, float]] | None = None) -> list[dict]:
    """Bearish Gartley: X high → A low → B high → C low → D high."""
    ratios = ratios or DEFAULT_RATIOS
    patterns: list[dict] = []
    recent_threshold = max(0, len(df) - 30)

    for X_idx, X_price, X_date in swing_highs[:-2]:
        potential_A = [sl for sl in swing_lows if sl[0] > X_idx]
        for A_idx, A_price, A_date in potential_A:
            if A_price >= X_price:
                continue

            segment_x_to_a = df.iloc[X_idx : A_idx + 1]
            if segment_x_to_a["High"].max() > X_price or segment_x_to_a["Low"].min() < A_price:
                continue

            XA_range = X_price - A_price
            potential_B = [sh for sh in swing_highs if sh[0] > A_idx]
            for B_idx, B_price, B_date in potential_B:
                if B_price <= A_price or B_price >= X_price:
                    continue

                segment_a_to_b = df.iloc[A_idx : B_idx + 1]
                if segment_a_to_b["High"].max() > B_price:
                    continue
                segment_x_to_b = df.iloc[X_idx : B_idx + 1]
                if segment_x_to_b["Low"].min() < A_price or segment_x_to_b["High"].max() > X_price:
                    continue

                AB_range = B_price - A_price
                AB_ratio = AB_range / XA_range
                if not check_ratio(AB_ratio, *ratios["AB_XA"]):
                    continue

                potential_C = [sl for sl in swing_lows if sl[0] > B_idx]
                for C_idx, C_price, C_date in potential_C:
                    if C_price >= B_price:
                        continue

                    segment_b_to_c = df.iloc[B_idx : C_idx + 1]
                    if segment_b_to_c["Low"].min() < C_price:
                        continue
                    segment_a_to_c = df.iloc[A_idx : C_idx + 1]
                    if segment_a_to_c["High"].max() > B_price or segment_a_to_c["Low"].min() < A_price:
                        continue

                    BC_range = B_price - C_price
                    BC_ratio = BC_range / AB_range
                    if not check_ratio(BC_ratio, *ratios["BC_AB"]):
                        continue

                    if C_idx >= recent_threshold:
                        current_price = float(df.iloc[-1]["Close"])
                        if current_price > C_price:
                            CD_current = current_price - C_price
                            CD_progress = CD_current / BC_range
                            if CD_progress >= 0.75:
                                patterns.append({
                                    "direction": "BEARISH",
                                    "type": "PARTIAL_XABC",
                                    "X": (X_idx, X_price, X_date),
                                    "A": (A_idx, A_price, A_date),
                                    "B": (B_idx, B_price, B_date),
                                    "C": (C_idx, C_price, C_date),
                                    "D": (len(df) - 1, current_price, pd.Timestamp(df.iloc[-1]["Date"])),
                                    "AB_ratio": AB_ratio * 100,
                                    "BC_ratio": BC_ratio * 100,
                                    "CD_ratio": CD_progress * 100,
                                    "score": 70,
                                })

                    potential_D = [sh for sh in swing_highs if sh[0] > C_idx]
                    for D_idx, D_price, D_date in potential_D:
                        if C_idx < recent_threshold and D_idx < recent_threshold:
                            continue
                        if D_price <= C_price:
                            continue

                        segment_c_to_d = df.iloc[C_idx : D_idx + 1]
                        if segment_c_to_d["High"].max() > D_price:
                            continue
                        segment_b_to_d = df.iloc[B_idx : D_idx + 1]
                        if segment_b_to_d["Low"].min() < C_price:
                            continue

                        CD_range = D_price - C_price
                        CD_ratio = CD_range / BC_range
                        cd_complete = check_ratio(CD_ratio, *ratios["CD_BC"])
                        cd_near_complete = 0.75 <= CD_ratio < ratios["CD_BC"][0]
                        if not (cd_complete or cd_near_complete):
                            continue

                        data_after_D = df.iloc[D_idx + 1 :]
                        if len(data_after_D) > 0:
                            rise_from_D = data_after_D["High"].max() - D_price
                            if rise_from_D > (CD_range * 0.5):
                                continue

                        patterns.append({
                            "direction": "BEARISH",
                            "type": "COMPLETE" if cd_complete else "NEAR_COMPLETE",
                            "X": (X_idx, X_price, X_date),
                            "A": (A_idx, A_price, A_date),
                            "B": (B_idx, B_price, B_date),
                            "C": (C_idx, C_price, C_date),
                            "D": (D_idx, D_price, D_date),
                            "AB_ratio": AB_ratio * 100,
                            "BC_ratio": BC_ratio * 100,
                            "CD_ratio": CD_ratio * 100,
                            "score": 100 if cd_complete else 85,
                        })
    return patterns


def scan_dataframe(df: pd.DataFrame, direction: str = "Both", ratios: dict[str, tuple[float, float]] | None = None) -> list[dict]:
    swing_highs, swing_lows = find_swing_points(df)
    normalized = normalize_direction(direction)

    patterns: list[dict] = []
    if normalized in ('BULLISH', 'Both'):
        patterns.extend(find_gartley_bullish(df, swing_highs, swing_lows, ratios=ratios))
    if normalized in ('BEARISH', 'Both'):
        patterns.extend(find_gartley_bearish(df, swing_highs, swing_lows, ratios=ratios))

    return remove_duplicate_patterns(patterns)


def _format_timestamp(ts) -> str:
    return pd.Timestamp(ts).isoformat(sep=" ", timespec="minutes")


def _pattern_to_row(ticker: str, pattern: dict) -> dict:
    row = {
        "ticker": ticker,
        "direction": pattern["direction"],
        "type": pattern["type"],
        "score": int(pattern.get("score", 0)),
        "AB/XA %": round(float(pattern["AB_ratio"]), 2),
        "BC/AB %": round(float(pattern["BC_ratio"]), 2),
        "CD/BC %": round(float(pattern["CD_ratio"]), 2),
        "pattern_key": "-".join(str(pattern[label][0]) for label in ["X", "A", "B", "C", "D"]),
    }
    for label in ["X", "A", "B", "C", "D"]:
        _, price, date = pattern[label]
        row[f"{label}_date"] = _format_timestamp(date)
        row[f"{label}_price"] = round(float(price), 4)
    return row


def scan_ticker(
    ticker: str,
    months: int = DEFAULT_MONTHS,
    interval: str = DEFAULT_INTERVAL,
    direction: str = "Both",
    ratios: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    df = download_prices(ticker, months=months, interval=interval)
    patterns = scan_dataframe(df, direction=direction, ratios=ratios)
    rows = [_pattern_to_row(clean_ticker(ticker), p) for p in patterns]
    return pd.DataFrame(rows), df, patterns


def scan_many(
    tickers: Iterable[str],
    months: int = DEFAULT_MONTHS,
    interval: str = DEFAULT_INTERVAL,
    direction: str = "Both",
    ratios: dict[str, tuple[float, float]] | None = None,
    progress_callback: Callable[[int, int, str, int, str | None], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, str], dict[str, pd.DataFrame], dict[str, list[dict]]]:
    frames: list[pd.DataFrame] = []
    errors: dict[str, str] = {}
    data_by_ticker: dict[str, pd.DataFrame] = {}
    patterns_by_ticker: dict[str, list[dict]] = {}

    normalized_tickers = [clean_ticker(t) for t in tickers if clean_ticker(t)]
    total = len(normalized_tickers)

    for i, ticker in enumerate(normalized_tickers, 1):
        error: str | None = None
        count = 0
        try:
            matches, df, patterns = scan_ticker(
                ticker,
                months=months,
                interval=interval,
                direction=direction,
                ratios=ratios,
            )
            data_by_ticker[ticker] = df
            patterns_by_ticker[ticker] = patterns
            if not matches.empty:
                frames.append(matches)
                count = len(matches)
        except Exception as exc:
            error = str(exc)
            errors[ticker] = error

        if progress_callback is not None:
            progress_callback(i, total, ticker, count, error)

    if frames:
        results = pd.concat(frames, ignore_index=True)
        type_rank = {"COMPLETE": 0, "NEAR_COMPLETE": 1, "PARTIAL_XABC": 2}
        results["type_rank"] = results["type"].map(type_rank).fillna(9)
        results = results.sort_values(
            by=["type_rank", "score", "D_date", "ticker"],
            ascending=[True, False, False, True],
        ).drop(columns=["type_rank"]).reset_index(drop=True)
        return results, errors, data_by_ticker, patterns_by_ticker

    return pd.DataFrame(), errors, data_by_ticker, patterns_by_ticker


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add chart indicators for the Streamlit chart."""
    out = df.copy()
    close = out["Close"].astype(float)

    # Hourly candle moving averages: same default interval requested for the app.
    out["HMA_50"] = close.rolling(window=50).mean()
    out["HMA_100"] = close.rolling(window=100).mean()
    out["HMA_200"] = close.rolling(window=200).mean()

    # Approximate daily/weekly MAs on an hourly chart.
    bars_per_day = 6
    out["DMA_50"] = close.rolling(window=50 * bars_per_day).mean()
    out["DMA_100"] = close.rolling(window=100 * bars_per_day).mean()
    out["DMA_200"] = close.rolling(window=200 * bars_per_day).mean()

    bars_per_week = bars_per_day * 5
    out["WMA_50"] = close.rolling(window=50 * bars_per_week).mean()
    out["WMA_100"] = close.rolling(window=100 * bars_per_week).mean()
    out["WMA_200"] = close.rolling(window=200 * bars_per_week).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    safe_loss = loss.mask(loss == 0)
    rs = gain / safe_loss
    out["RSI"] = (100 - (100 / (1 + rs))).fillna(50).astype(float)
    return out
