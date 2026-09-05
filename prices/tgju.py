"""Scrape live prices from https://www.tgju.org using only HTML web scraping."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TGJU_HOME = "https://www.tgju.org"
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

SYMBOLS = (
    "gold18", "gold24",
    "usd", "eur", "dirham", "tether",
    "coin_full", "coin_old", "coin_half", "coin_quarter",
    "silver",
    "ounce", "silver_ounce", "oil",
)
GLOBAL_SYMBOLS = {"ounce", "silver_ounce", "oil"}

# Persian label → internal symbol (order matters for matching)
_LABEL_MAP = [
    ("طلای ۱۸ عیار", "gold18"),
    ("طلای 24 عیار", "gold24"),
    ("طلای ۲۴ عیار", "gold24"),
    ("دلار", "usd"),
    ("یورو", "eur"),
    ("درهم امارات", "dirham"),
    ("درهم", "dirham"),
    ("تتر", "tether"),
    ("سکه امامی", "coin_full"),
    ("سکه بهار آزادی", "coin_old"),
    ("نیم سکه", "coin_half"),
    ("ربع سکه", "coin_quarter"),
    ("نقره ۹۲۵", "silver"),
    ("گرم نقره", "silver"),
    ("انس جهانی طلا", "ounce"),
    ("انس طلا", "ounce"),
    ("انس نقره", "silver_ounce"),
    ("انس جهانی نقره", "silver_ounce"),
    ("نفت برنت", "oil"),
]


class ProviderError(RuntimeError):
    """Raised when the TGJU page cannot be scraped."""


def as_decimal(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    text = str(value).translate(PERSIAN_DIGITS).replace(",", "").replace("٬", "").replace("%", "").replace("+", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def _normalise(text: str) -> str:
    t = text.translate(PERSIAN_DIGITS)
    t = t.replace("ي", "ی").replace("ك", "ک").replace("‌", " ").replace("怎样", "")
    return re.sub(r"\s+", " ", t).strip()


def _symbol_for(label: str) -> str | None:
    norm = _normalise(label)
    if not norm or "ذاتی" in norm:
        return None
    for needle, symbol in _LABEL_MAP:
        if needle in norm:
            return symbol
    return None


# ---------------------------------------------------------------------------
# HTML table parser — extracts rows with cells, href, data-market-row, data-price
# ---------------------------------------------------------------------------

class _TGJUPriceTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self._row: dict | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            attrs_map = dict(attrs)
            self._row = {
                "cells": [],
                "href": None,
                "market_row": attrs_map.get("data-market-row"),
                "data_price": attrs_map.get("data-price"),
            }
        elif self._row is not None and tag in {"td", "th"}:
            self._cell = []
        elif self._row is not None and tag == "a":
            href = dict(attrs).get("href", "")
            if href and "profile/" in href:
                self._row["href"] = href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row["cells"].append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _fetch_html(url: str) -> str:
    last_error = None
    for _ in range(2):
        request = Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=12) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as error:
            last_error = error
    raise ProviderError(f"TGJU page request failed: {last_error}") from last_error


def _parse_rows(html: str) -> list[dict]:
    parser = _TGJUPriceTableParser()
    parser.feed(html)
    return parser.rows


# ---------------------------------------------------------------------------
# Scrape ALL prices from the TGJU main page — pure HTML, no API
# ---------------------------------------------------------------------------

def scrape_tgju_prices() -> dict:
    """Scrape all prices from tgju.org homepage using only HTML web scraping."""
    html = _fetch_html(TGJU_HOME)
    rows = _parse_rows(html)

    found: dict[str, Decimal] = {}

    for row in rows:
        cells = row.get("cells", [])
        if len(cells) < 2:
            continue

        # Method 1: match by cell text label (main table rows)
        symbol = _symbol_for(cells[0])
        if symbol and symbol not in found:
            value = as_decimal(cells[1])
            if value is not None:
                found[symbol] = value

        # Method 2: match by data-market-row attribute (ticker/market rows)
        mr = str(row.get("market_row") or "").strip()
        if mr and symbol is None and mr not in found:
            # Try mapping data-market-row slugs directly
            MR_MAP = {
                "geram18": "gold18", "geram24": "gold24",
                "price_dollar_rl": "usd", "price_eur": "eur",
                "price_aed": "dirham", "crypto-tether": "tether",
                "sekee": "coin_full", "sekeb": "coin_old",
                "nim": "coin_half", "rob": "coin_quarter",
                "silver_999": "silver",
                "ons": "ounce", "silver": "silver_ounce",
                "oil_brent": "oil",
            }
            mapped = MR_MAP.get(mr)
            if mapped and mapped not in found:
                dp = as_decimal(row.get("data_price"))
                if dp is not None:
                    found[mapped] = dp

    # Also extract from <li> ticker items (global markets like oil, ounce)
    li_pattern = re.compile(
        r'<li\b[^>]*id=["\']l-([^"\']+)["\'][^>]*>.*?'
        r'<span\b[^>]*class=["\'][^"\']*info-price[^"\']*["\'][^>]*>(.*?)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    LI_SLUG_MAP = {
        "ons": "ounce", "silver": "silver_ounce", "oil_brent": "oil",
        "geram18": "gold18", "geram24": "gold24",
        "price_dollar_rl": "usd", "price_eur": "eur",
        "price_aed": "dirham", "crypto-tether": "tether",
        "sekee": "coin_full", "sekeb": "coin_old",
        "nim": "coin_half", "rob": "coin_quarter",
    }
    for m in li_pattern.finditer(html):
        slug = m.group(1).strip()
        mapped = LI_SLUG_MAP.get(slug)
        if mapped and mapped not in found:
            value = as_decimal(re.sub(r"<[^>]+>", " ", m.group(2)))
            if value is not None:
                found[mapped] = value

    # Also try extracting from data-price attributes on table rows
    for row in rows:
        mr = str(row.get("market_row") or "").strip()
        MR_MAP = {
            "geram18": "gold18", "geram24": "gold24",
            "price_dollar_rl": "usd", "price_eur": "eur",
            "price_aed": "dirham", "crypto-tether": "tether",
            "sekee": "coin_full", "sekeb": "coin_old",
            "nim": "coin_half", "rob": "coin_quarter",
            "silver_999": "silver",
            "ons": "ounce", "silver": "silver_ounce",
            "oil_brent": "oil",
        }
        mapped = MR_MAP.get(mr)
        if mapped and mapped not in found:
            dp = as_decimal(row.get("data_price"))
            if dp is not None:
                found[mapped] = dp

    missing = [s for s in SYMBOLS if s not in found]
    if missing:
        raise ProviderError(f"TGJU page is missing: {', '.join(missing)}")

    return {
        "prices": {s: found[s] for s in SYMBOLS},
        "changes": {s: None for s in SYMBOLS},
    }
