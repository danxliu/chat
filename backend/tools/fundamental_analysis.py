"""Fundamental analysis tool — valuation, profitability, growth, and earnings data."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_INFO_FIELD_MAP: dict[str, tuple[str, str]] = {
    # yfinance_key: (display_name, is_percentage)
    "trailingPE": ("Trailing P/E", False),
    "forwardPE": ("Forward P/E", False),
    "pegRatio": ("PEG Ratio", False),
    "priceToBook": ("Price/Book", False),
    "priceToSales": ("Price/Sales", False),
    "returnOnEquity": ("ROE", True),
    "returnOnAssets": ("ROA", True),
    "grossMargins": ("Gross Margin", True),
    "operatingMargins": ("Operating Margin", True),
    "profitMargins": ("Net Margin", True),
    "debtToEquity": ("Debt/Equity", False),
    "currentRatio": ("Current Ratio", False),
    "quickRatio": ("Quick Ratio", False),
    "revenueGrowth": ("Revenue Growth YoY", True),
    "earningsGrowth": ("Earnings Growth YoY", True),
    "marketCap": ("Market Cap", False),
    "enterpriseValue": ("Enterprise Value", False),
    "beta": ("Beta", False),
    "dividendYield": ("Dividend Yield", True),
    "payoutRatio": ("Payout Ratio", True),
    "trailingEps": ("Trailing EPS", False),
    "freeCashflow": ("Free Cash Flow", False),
    "operatingCashflow": ("Operating Cash Flow", False),
}

_BIG_NUMBER_KEYS = {"marketCap", "enterpriseValue", "freeCashflow", "operatingCashflow"}


def _fmt_val(value, *, is_pct: bool = False, is_big: bool = False) -> str:
    """Format a numeric value for display."""
    if value is None:
        return "N/A"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if is_big:
        if abs(f) >= 1e12:
            return f"${f / 1e12:.2f}T"
        if abs(f) >= 1e9:
            return f"${f / 1e9:.2f}B"
        if abs(f) >= 1e6:
            return f"${f / 1e6:.2f}M"
        return f"${f:,.0f}"
    if is_pct:
        return f"{f * 100:.2f}%" if abs(f) < 10 else f"{f:.2f}%"
    return f"{f:.2f}"


def _analyze_one(ticker: str) -> str:
    """Fetch and format fundamental data for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        if not info or (
            info.get("trailingPE") is None and info.get("marketCap") is None
        ):
            return f"### {ticker}\n\nNo fundamental data available. The ticker may be invalid or delisted."

        lines = [f"### {ticker} — Fundamental Analysis"]
        lines.append(f"*Data as of: {datetime.now().strftime('%Y-%m-%d')}*\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")

        for yf_key, (label, is_pct) in _INFO_FIELD_MAP.items():
            val = info.get(yf_key)
            if val is not None:
                is_big = yf_key in _BIG_NUMBER_KEYS
                lines.append(
                    f"| {label} | {_fmt_val(val, is_pct=is_pct, is_big=is_big)} |"
                )

        # Earnings surprises
        try:
            earnings_dates = t.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                surprises = []
                for row_idx, (idx, row) in enumerate(earnings_dates.head(4).iterrows()):
                    eps_actual = row.get("EPS Actual")
                    if eps_actual is None or (
                        isinstance(eps_actual, float) and pd.isna(eps_actual)
                    ):
                        continue
                    eps_est = row.get("EPS Estimate")
                    surprise_pct = row.get("Surprise(%)")
                    date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)
                    surprises.append(
                        {
                            "date": date_str,
                            "eps_actual": round(float(eps_actual), 4),
                            "eps_estimate": round(float(eps_est), 4)
                            if eps_est is not None
                            and not (isinstance(eps_est, float) and pd.isna(eps_est))
                            else None,
                            "surprise_pct": round(float(surprise_pct), 2)
                            if surprise_pct is not None
                            and not (
                                isinstance(surprise_pct, float)
                                and pd.isna(surprise_pct)
                            )
                            else None,
                        }
                    )

                if surprises:
                    lines.append("\n**Recent Earnings Surprises:**\n")
                    lines.append("| Date | EPS Actual | EPS Estimate | Surprise % |")
                    lines.append("|------|-----------|-------------|------------|")
                    for s in surprises:
                        lines.append(
                            f"| {s['date']} | {s['eps_actual']} | "
                            f"{s['eps_estimate'] or 'N/A'} | {s['surprise_pct'] or 'N/A'} |"
                        )
        except Exception:
            logger.debug("%s: no earnings_dates available", ticker)

        # Upcoming events
        try:
            cal = t.calendar
            if cal is not None and not cal.empty:
                row = cal.iloc[0] if isinstance(cal, pd.DataFrame) else cal
                earnings_date = (
                    row.get("Earnings Date") if hasattr(row, "get") else None
                )
                div_date = row.get("Ex-Dividend Date") if hasattr(row, "get") else None
                if earnings_date is not None or div_date is not None:
                    lines.append("\n**Upcoming Events:**")
                    if earnings_date is not None:
                        lines.append(f"- Next Earnings: {earnings_date}")
                    if div_date is not None:
                        lines.append(f"- Ex-Dividend Date: {div_date}")
        except Exception:
            logger.debug("%s: no calendar available", ticker)

        return "\n".join(lines)

    except Exception as e:
        logger.warning(
            "Error fetching fundamentals for %s: %s", ticker, e, exc_info=True
        )
        return f"### {ticker}\n\nError: {e}"


def run_fundamental_analysis(tickers: list[str]) -> str:
    """Run fundamental analysis on a list of stock tickers. Returns valuation metrics (P/E, P/B, P/S, PEG), profitability (ROE, ROA, margins), growth rates, financial health ratios, earnings surprises, and dividend data."""
    if not tickers:
        return "Error: No tickers provided. Please provide a list of uppercase stock tickers (e.g. ['AAPL', 'MSFT'])."

    tickers = [t.upper().strip() for t in tickers]
    results: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(tickers), 5)) as executor:
        futures = {executor.submit(_analyze_one, t): t for t in tickers}
        for future in as_completed(futures):
            results.append(future.result())

    return "\n\n---\n\n".join(results)
