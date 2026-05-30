"""Stock news snapshot generator for iran-war-notelm → stock_1901 bridge.

Run this script from iran-war-notelm repo (or as standalone) to produce
reports/stock_news_snapshot.json that stock_1901 reads via notebooklm_news.py.

Schedule: GitHub Actions every 30 min OR standalone cron every 15 min.

Usage:
    python scripts/notebooklm_stock_snapshot.py
    python scripts/notebooklm_stock_snapshot.py --tickers AAPL,MSFT,NVDA,005930

Environment variables:
    STOCK_TICKERS          comma-separated list (default: AAPL,MSFT,NVDA,GOOGL,005930)
    NOTEBOOKLM_API_KEY     for direct NoteBookLM API (optional)
    SNAPSHOT_OUTPUT_PATH   output file path (default: reports/stock_news_snapshot.json)
"""

from __future__ import annotations

import argparse
import feedparser
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_LOGGER = logging.getLogger("notebooklm_stock_snapshot")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TICKERS = os.environ.get(
    "STOCK_TICKERS", "AAPL,MSFT,NVDA,GOOGL,TSLA,005930,000660"
).split(",")

RSS_SOURCES = {
    "reuters": "https://feeds.reuters.com/reuters/businessNews",
    "ap_finance": "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "yonhap_kr":  "https://www.yonhapnewstv.co.kr/category/news/economy/rss",
    "mk_business": "https://rss.mk.co.kr/rss/30000023.xml",
    "naver_finance": "https://rss.naver.com/business.xml",
}

# Ticker → keywords to filter relevant news
TICKER_KEYWORDS: dict[str, list[str]] = {
    "AAPL":   ["Apple", "iPhone", "Tim Cook", "App Store", "AAPL"],
    "MSFT":   ["Microsoft", "Azure", "Satya Nadella", "MSFT", "Windows"],
    "NVDA":   ["NVIDIA", "Jensen Huang", "GPU", "NVDA", "H100"],
    "GOOGL":  ["Google", "Alphabet", "Sundar", "Search", "GOOGL"],
    "TSLA":   ["Tesla", "Elon Musk", "EV", "TSLA"],
    "META":   ["Meta", "Zuckerberg", "Facebook", "Instagram", "META"],
    "005930": ["Samsung Electronics", "삼성전자", "Galaxy", "반도체"],
    "000660": ["SK Hynix", "SK하이닉스", "DRAM", "메모리"],
    "035420": ["NAVER", "네이버", "LINE"],
    "005380": ["Hyundai", "현대자동차", "EV"],
}

OUTPUT_PATH = Path(os.environ.get(
    "SNAPSHOT_OUTPUT_PATH", "reports/stock_news_snapshot.json"
))

MAX_HEADLINES_PER_TICKER = 8
FETCH_TIMEOUT_SEC = 10


# ---------------------------------------------------------------------------
# RSS scraping (adapted from iran-war-notelm/scrapers/rss_feed.py pattern)
# ---------------------------------------------------------------------------

def scrape_rss_for_ticker(ticker: str, keywords: list[str]) -> list[dict[str, Any]]:
    """Scrape all RSS sources and return relevant headlines for ticker."""
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for source_id, feed_url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""

                # Filter by keyword relevance
                text = (title + " " + summary).lower()
                if not any(kw.lower() in text for kw in keywords):
                    continue

                if link in seen_urls:
                    continue
                seen_urls.add(link)

                published = getattr(entry, "published", "") or ""
                results.append({
                    "source": source_id,
                    "title": title.strip(),
                    "url": link,
                    "summary": summary.strip()[:500],
                    "published": published,
                })

                if len(results) >= MAX_HEADLINES_PER_TICKER:
                    break

        except Exception as exc:
            _LOGGER.warning("RSS %s failed: %s", source_id, exc)

    return results[:MAX_HEADLINES_PER_TICKER]


# ---------------------------------------------------------------------------
# NotebookLM enrichment (optional)
# ---------------------------------------------------------------------------

def enrich_with_notebooklm(ticker: str, headlines: list[dict]) -> str | None:
    """Query NotebookLM for AI summary. Returns summary string or None."""
    try:
        notebook_id = os.environ.get(f"NOTEBOOKLM_NOTEBOOK_{ticker}")
        if not notebook_id:
            return None

        import subprocess
        query = f"Summarize the latest news and investment implications for {ticker}"
        result = subprocess.run(
            ["notebooklm-mcp", "query", "--notebook", notebook_id, "--query", query],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("summary") or data.get("response")
    except Exception as exc:
        _LOGGER.debug("NotebookLM enrich skipped for %s: %s", ticker, exc)
    return None


# ---------------------------------------------------------------------------
# Main snapshot builder
# ---------------------------------------------------------------------------

def build_snapshot(tickers: list[str]) -> dict[str, Any]:
    """Build the full snapshot JSON for all tickers."""
    _LOGGER.info("Building stock news snapshot for %d tickers", len(tickers))

    tickers_data: dict[str, list[dict]] = {}

    for ticker in tickers:
        clean = ticker.strip().upper()
        keywords = TICKER_KEYWORDS.get(clean, [clean])
        _LOGGER.info("  Scraping %s (keywords: %s)", clean, keywords[:3])

        headlines = scrape_rss_for_ticker(clean, keywords)
        _LOGGER.info("  %s: %d headlines", clean, len(headlines))

        # Optional: upload to NotebookLM and get AI summary
        ai_summary = enrich_with_notebooklm(clean, headlines)
        if ai_summary:
            # Prepend AI summary as a special headline
            headlines.insert(0, {
                "source": "notebooklm_ai",
                "title": f"[AI Summary] {clean}",
                "url": "",
                "summary": ai_summary,
                "published": datetime.now(UTC).isoformat(),
            })

        tickers_data[clean] = headlines
        time.sleep(0.5)  # rate limit between tickers

    return {
        "schema": "stock_news_snapshot.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "tickers": tickers_data,
        "source_count": len(RSS_SOURCES),
        "ticker_count": len(tickers),
    }


def write_snapshot(snapshot: dict[str, Any], output: Path) -> None:
    """Write snapshot to disk atomically."""
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output)
    _LOGGER.info("Snapshot written → %s (%d bytes)", output, output.stat().st_size)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build stock news snapshot for stock_1901")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                        help="Comma-separated ticker list")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print snapshot, don't write")
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    snapshot = build_snapshot(tickers)

    if args.dry_run:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        write_snapshot(snapshot, Path(args.output))

    total_headlines = sum(len(v) for v in snapshot["tickers"].values())
    _LOGGER.info("Done: %d tickers, %d total headlines", len(tickers), total_headlines)


if __name__ == "__main__":
    main()
