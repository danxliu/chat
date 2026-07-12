"""Volatility analysis tool — close-to-close, Garman-Klass, and EWMA estimators."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)

TRADING_DAYS = 252


def _close_to_close(closes: np.ndarray) -> float:
    """Annualized close-to-close volatility (std of log returns)."""
    if len(closes) < 2:
        raise ValueError("Insufficient data")
    log_returns = np.diff(np.log(closes))
    daily_std = np.std(log_returns, ddof=1)
    return float(daily_std * np.sqrt(TRADING_DAYS))


def _garman_klass(
    opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
) -> float:
    """Annualized Garman-Klass volatility estimator using OHLC data."""
    if len(closes) < 2:
        raise ValueError("Insufficient data")
    log_hl = np.log(highs / lows)
    log_co = np.log(closes / opens)
    rs = 0.5 * (log_hl**2) - (2 * np.log(2) - 1) * (log_co**2)
    daily_var = np.mean(rs)
    return float(np.sqrt(daily_var) * np.sqrt(TRADING_DAYS))


def _ewma(closes: np.ndarray, lambda_: float = 0.94) -> float:
    """Annualized EWMA (exponentially weighted moving average) volatility."""
    if len(closes) < 2:
        raise ValueError("Insufficient data")
    log_returns = np.diff(np.log(closes))
    var = np.var(log_returns, ddof=1)
    for r in log_returns:
        var = (1 - lambda_) * (r**2) + lambda_ * var
    return float(np.sqrt(var) * np.sqrt(TRADING_DAYS))


def _calculate_one(ticker: str) -> str:
    """Calculate volatility metrics for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")

        if df.empty or len(df) < 30:
            return (
                f"### {ticker}\n\nInsufficient price history "
                f"(need at least 30 trading days, got {len(df)})."
            )

        closes = df["Close"].to_numpy(dtype=np.float64)
        opens = df["Open"].to_numpy(dtype=np.float64)
        highs = df["High"].to_numpy(dtype=np.float64)
        lows = df["Low"].to_numpy(dtype=np.float64)

        cc = round(_close_to_close(closes) * 100, 2)
        gk = round(_garman_klass(opens, highs, lows, closes) * 100, 2)
        ew = round(_ewma(closes) * 100, 2)

        def _level(pct: float) -> str:
            if pct < 20:
                return "Low"
            if pct < 40:
                return "Moderate"
            if pct < 60:
                return "High"
            return "Very High"

        lines = [f"### {ticker} — Volatility Analysis", ""]
        lines.append("| Estimator | Annualized Volatility | Level |")
        lines.append("|-----------|----------------------|-------|")
        lines.append(f"| Close-to-Close | {cc}% | {_level(cc)} |")
        lines.append(f"| Garman-Klass (OHLC) | {gk}% | {_level(gk)} |")
        lines.append(f"| EWMA (λ=0.94) | {ew}% | {_level(ew)} |")
        lines.append("")
        lines.append(
            "*Close-to-Close uses only closing prices. "
            "Garman-Klass incorporates intraday OHLC for a more efficient estimate. "
            "EWMA gives more weight to recent observations.*"
        )

        return "\n".join(lines)

    except Exception as e:
        logger.warning(
            "Error calculating volatility for %s: %s", ticker, e, exc_info=True
        )
        return f"### {ticker}\n\nError: {e}"


def run_volatility_analysis(tickers: list[str]) -> str:
    """Calculate volatility metrics for a list of stock tickers. Returns close-to-close (annualized std of log returns), Garman-Klass (OHLC estimator), and EWMA volatility predictions."""
    if not tickers:
        return "Error: No tickers provided. Please provide a list of uppercase stock tickers (e.g. ['AAPL', 'MSFT'])."

    tickers = [t.upper().strip() for t in tickers]
    results: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(tickers), 5)) as executor:
        futures = {executor.submit(_calculate_one, t): t for t in tickers}
        for future in as_completed(futures):
            results.append(future.result())

    return "\n\n---\n\n".join(results)
