"""Sentiment analysis tool — fetches articles and classifies sentiment via LLM."""

import asyncio
import json
import logging
from typing import Literal

import yfinance as yf
from pydantic import BaseModel, Field, ValidationError

from config import settings
from llm import openai_client
from prompts import SENTIMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Pydantic model for validating LLM sentiment output


class SentimentResult(BaseModel):
    score: float = Field(ge=-1.0, le=1.0)
    label: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)
    tickers: list[str] = Field(default_factory=list)


def _build_user_prompt(article: dict) -> str:
    """Build the user prompt for a single article."""
    return (
        f"---\n"
        f"Ticker: {article['ticker']}\n"
        f"Title: {article['title']}\n"
        f"Publisher: {article['publisher']}\n"
        f"Published: {article['published_at']}\n"
        f"---\n\n"
        f"{article['content'][:2000]}"
    )


# Article fetching (yfinance)


def _fetch_articles(tickers: list[str]) -> list[dict]:
    """Fetch recent news articles for a list of tickers via yfinance."""
    articles: list[dict] = []
    for ticker in tickers:
        try:
            raw = yf.Ticker(ticker).news or []
        except Exception as e:
            logger.warning("Failed to fetch news for %s: %s", ticker, e)
            continue

        for item in raw[: settings.sentiment_max_articles]:
            try:
                data = item.get("content", {})
                url = (
                    data.get("canonicalUrl", {}).get("url")
                    or data.get("clickThroughUrl", {}).get("url")
                    or ""
                )
                if not url:
                    continue

                pub_date = None
                raw_date = data.get("pubDate")
                if raw_date:
                    try:
                        from datetime import datetime

                        pub_date = datetime.fromisoformat(
                            raw_date.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                articles.append(
                    {
                        "ticker": ticker.upper(),
                        "title": data.get("title", "Untitled"),
                        "content": data.get("summary") or data.get("description") or "",
                        "url": url,
                        "publisher": (
                            data.get("provider", {}).get("displayName", "Unknown")
                            if isinstance(data.get("provider"), dict)
                            else "Unknown"
                        ),
                        "published_at": pub_date,
                    }
                )
            except Exception as e:
                logger.warning("Skipping malformed article for %s: %s", ticker, e)

    logger.info("Fetched %d articles for %s", len(articles), tickers)
    return articles


# LLM sentiment classification


async def _analyze_one_article(article: dict) -> dict:
    """Classify sentiment of a single article via LLM. Returns a dict with
    score, label, confidence, reasoning, and tickers."""
    user_prompt = _build_user_prompt(article)

    try:
        response = await openai_client.chat.completions.create(
            model=settings.sentiment_model,
            messages=[
                {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
            timeout=30.0,
        )
        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("Empty response from sentiment analysis")

        # Strip markdown code fences if present
        raw = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        result = SentimentResult.model_validate_json(raw)
        return result.model_dump()

    except (ValidationError, json.JSONDecodeError, ValueError) as e:
        logger.warning(
            "Sentiment validation failed for '%s': %s", article["title"][:60], e
        )
        return {
            "score": 0.0,
            "label": "neutral",
            "confidence": 0.0,
            "reasoning": "analysis failed",
            "tickers": [article["ticker"]],
        }


# Output formatting


def _format_articles(articles: list[dict]) -> str:
    """Format annotated articles as citable markdown blocks with per-article scores."""
    if not articles:
        return "No recent news articles found for the requested tickers."

    # Summary header — weighted average score per ticker
    by_ticker: dict[str, dict[str, int | float]] = {}
    for a in articles:
        t = a["ticker"]
        if t not in by_ticker:
            by_ticker[t] = {
                "bullish": 0,
                "bearish": 0,
                "neutral": 0,
                "total": 0,
                "score_sum": 0.0,
            }
        s = a.get("sentiment", {})
        label = s.get("label", "neutral")
        by_ticker[t][label] += 1  # type: ignore[operator]
        by_ticker[t]["total"] += 1  # type: ignore[operator]
        by_ticker[t]["score_sum"] += s.get("score", 0.0)  # type: ignore[operator]

    lines = ["## News Sentiment Analysis\n"]
    for ticker, counts in sorted(by_ticker.items()):
        total = int(counts["total"])
        avg = counts["score_sum"] / total if total > 0 else 0.0  # type: ignore[operator]
        overall = "bullish" if avg > 0.1 else ("bearish" if avg < -0.1 else "neutral")
        emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
        lines.append(
            f"**{ticker}** — {total} articles, avg score {avg:+.2f}: "
            f"{emoji[overall]} {int(counts['bullish'])} bullish · "  # type: ignore[arg-type]
            f"{emoji['bearish']} {int(counts['bearish'])} bearish · "  # type: ignore[arg-type]
            f"{emoji['neutral']} {int(counts['neutral'])} neutral"  # type: ignore[arg-type]
        )
    lines.append("")

    # Per-article blocks
    emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
    for a in articles:
        s = a.get("sentiment", {})
        label = s.get("label", "neutral")
        score = s.get("score", 0.0)
        conf = s.get("confidence", 0.0)
        reasoning = s.get("reasoning", "")

        pub_str = ""
        if a.get("published_at"):
            pub_str = a["published_at"].strftime("%b %d, %Y") + " · "

        lines.append(
            f"### [{a['title']}]({a['url']})  "
            f"{emoji.get(label, '⚪')} {label} · score: {score:+.2f} ({conf:.0%})"
        )
        lines.append(f"*{pub_str}{a['publisher']} · Ticker: {a['ticker']}*")
        if reasoning:
            lines.append(f"\n> {reasoning}")
        lines.append("")

    lines.append(
        "*Sentiment classified by LLM. Confidence indicates model certainty, "
        "not investment advice.*"
    )
    return "\n".join(lines)


# Public tool function


async def run_sentiment_analysis(tickers: list[str]) -> str:
    """Analyze news sentiment for a list of stock tickers. Fetches recent articles, classifies each as bullish/bearish/neutral via LLM, and returns per-article results with linked titles for citation and numerical sentiment scores."""
    if not tickers:
        return "Error: No tickers provided. Please provide a list of uppercase stock tickers (e.g. ['AAPL', 'MSFT'])."

    tickers = [t.upper().strip() for t in tickers]

    # Phase 1: fetch articles (sync yfinance calls offloaded to thread)
    articles = await asyncio.to_thread(_fetch_articles, tickers)

    if not articles:
        return "No recent news articles found for the requested tickers."

    sem = asyncio.Semaphore(settings.sentiment_max_concurrency)

    async def analyze_one(article: dict) -> dict:
        async with sem:
            result = await _analyze_one_article(article)
            article["sentiment"] = result
            return article

    await asyncio.gather(*[analyze_one(a) for a in articles])

    # Phase 3: format as citable markdown
    return _format_articles(articles)
