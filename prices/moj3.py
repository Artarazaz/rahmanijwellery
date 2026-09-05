"""Scrape live gold and currency prices from https://moj3.ir/price/."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MOJ3_PRICE_URL = "https://moj3.ir/price/"
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

SYMBOLS = (
    "gold18",
    "gold24",
    "usd",
    "eur",
    "dirham",
    "silver",
    "tether",
    "coin_full",
    "coin_old",
    "coin_half",
    "coin_quarter",
    "ounce",
    "silver_ounce",
    "oil",
)
GLOBAL_SYMBOLS = {"ounce", "silver_ounce", "oil"}

_NAME_RULES = (
    ("طلای 18 عیار", "gold18"),
    ("طلای 24 عیار", "gold24"),
    ("سکه طرح جدید", "coin_full"),
    ("سکه طرح قدیم", "coin_old"),
    ("نیم سکه", "coin_half"),
    ("ربع سکه", "coin_quarter"),
    ("نقره 925", "silver"),
    ("انس جهانی طلا", "ounce"),
    ("انس جهانی نقره", "silver_ounce"),
    ("نفت برنت", "oil"),
    ("تتر", "tether"),
    ("درهم", "dirham"),
    ("یورو", "eur"),
    ("دلار", "usd"),
)


class ProviderError(RuntimeError):
    """Raised when the Moj3 price page cannot be scraped."""


def _normalise_name(value: str) -> str:
    text = str(value).translate(PERSIAN_DIGITS)
    text = text.replace("ي", "ی").replace("ك", "ک").replace("‌", " ").replace("٪", "%")
    return re.sub(r"\s+", " ", text).strip()


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


def symbol_from_name(name: str) -> str | None:
    normalised = _normalise_name(name)
    if not normalised or "ذاتی" in normalised:
        return None
    for needle, symbol in _NAME_RULES:
        if needle in normalised:
            return symbol
    return None


class _Moj3PriceTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif self._row is not None and tag in {"td", "th"}:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(_normalise_name("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_moj3_html(html: str) -> dict:
    parser = _Moj3PriceTableParser()
    parser.feed(html)
    prices: dict[str, Decimal] = {}
    changes: dict[str, Decimal | None] = {}
    for row in parser.rows:
        if len(row) < 2:
            continue
        symbol = symbol_from_name(row[0])
        value = as_decimal(row[1])
        if not symbol or value is None or symbol in prices:
            continue
        prices[symbol] = value
        change = None
        for cell in row[2:]:
            if "%" in cell:
                change = as_decimal(cell)
                break
        changes[symbol] = change
    if "gold18" not in prices:
        raise ProviderError("صفحه موج سوم قیمت طلای ۱۸ عیار را ندارد.")
    return {"prices": prices, "changes": changes}


def fetch_moj3_html(url: str = MOJ3_PRICE_URL, timeout: float = 12) -> str:
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
    last_error = None
    for _attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as error:
            last_error = error
    raise ProviderError(f"خواندن صفحه موج سوم ناموفق بود: {last_error}") from last_error


def scrape_moj3_prices(url: str = MOJ3_PRICE_URL, timeout: float = 12) -> dict:
    return parse_moj3_html(fetch_moj3_html(url=url, timeout=timeout))
