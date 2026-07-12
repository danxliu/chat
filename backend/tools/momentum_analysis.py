"""Momentum / technical analysis tool — RSI, SMA, MACD, Stochastic indicators."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pandas_ta  # noqa: F401 — registers .ta accessor on DataFrames
import yfinance as yf

logger = logging.getLogger(__name__)


def _get_last(df: pd.DataFrame, col: str) -> float | None:
    """Safely extract the last non-NaN value from a DataFrame column."""
    if col not in df.columns:
        return None
    series = df[col].dropna()
    if series.empty:
        return None
    return round(float(series.iloc[-1]), 4)


def _calculate_one(ticker: str) -> str:
    """Calculate momentum indicators for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")

        if df.empty or len(df) < 200:
            return f"### {ticker}\n\nInsufficient price history (need at least 200 trading days, got {len(df)})."

        # Ensure lowercase column names for pandas_ta compatibility
        df.columns = [c.lower() for c in df.columns]

        # Calculate indicators
        df.ta.rsi(close="close", length=14, append=True)
        df.ta.sma(close="close", length=20, append=True)
        df.ta.sma(close="close", length=50, append=True)
        df.ta.sma(close="close", length=200, append=True)
        df.ta.macd(close="close", fast=12, slow=26, signal=9, append=True)
        df.ta.stoch(high="high", low="low", close="close", k=14, d=3, append=True)

        latest_close = round(float(df["close"].iloc[-1]), 2)

        rsi = _get_last(df, "RSI_14")
        macd = _get_last(df, "MACD_12_26_9")
        macd_signal = _get_last(df, "MACDs_12_26_9")
        stoch_k = _get_last(df, "STOCHk_14_3_3")
        stoch_d = _get_last(df, "STOCHd_14_3_3")
        sma20 = _get_last(df, "SMA_20")
        sma50 = _get_last(df, "SMA_50")
        sma200 = _get_last(df, "SMA_200")

        # Interpret signals
        rsi_signal = ""
        if rsi is not None:
            if rsi > 70:
                rsi_signal = " ⚠ Overbought"
            elif rsi < 30:
                rsi_signal = " ★ Oversold"
            else:
                rsi_signal = " ● Neutral"

        macd_label = ""
        if macd is not None and macd_signal is not None:
            macd_label = (
                " ▲ Bullish crossover" if macd > macd_signal else " ▼ Bearish crossover"
            )

        lines = [f"### {ticker} — Momentum Indicators", ""]
        lines.append("| Indicator | Value | Signal |")
        lines.append("|-----------|-------|--------|")
        lines.append(f"| Latest Close | ${latest_close} | — |")
        lines.append(f"| RSI (14) | {rsi or 'N/A'} |{rsi_signal} |")
        lines.append(f"| SMA 20 | {sma20 or 'N/A'} | — |")
        lines.append(f"| SMA 50 | {sma50 or 'N/A'} | — |")
        lines.append(f"| SMA 200 | {sma200 or 'N/A'} | — |")
        lines.append(f"| MACD | {macd or 'N/A'} |{macd_label} |")
        lines.append(f"| MACD Signal | {macd_signal or 'N/A'} | — |")
        lines.append(f"| Stochastic %K | {stoch_k or 'N/A'} | — |")
        lines.append(f"| Stochastic %D | {stoch_d or 'N/A'} | — |")

        # SMA trend alignment
        if sma20 and sma50 and sma200:
            lines.append("")
            lines.append("**SMA Alignment:**")
            if sma20 > sma50 > sma200:
                lines.append("- ▲ Bullish alignment (SMA20 > SMA50 > SMA200)")
            elif sma20 < sma50 < sma200:
                lines.append("- ▼ Bearish alignment (SMA20 < SMA50 < SMA200)")
            else:
                lines.append("- ● Mixed — no clear trend alignment")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(
            "Error calculating momentum for %s: %s", ticker, e, exc_info=True
        )
        return f"### {ticker}\n\nError: {e}"


def run_momentum_analysis(tickers: list[str]) -> str:
    """Run technical momentum analysis on a list of stock tickers. Returns latest close price, RSI-14, SMA-20/50/200, MACD, MACD signal, Stochastic %K and %D."""
    if not tickers:
        return "Error: No tickers provided. Please provide a list of uppercase stock tickers (e.g. ['AAPL', 'MSFT'])."

    tickers = [t.upper().strip() for t in tickers]
    results: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(tickers), 5)) as executor:
        futures = {executor.submit(_calculate_one, t): t for t in tickers}
        for future in as_completed(futures):
            results.append(future.result())

    return "\n\n---\n\n".join(results)
