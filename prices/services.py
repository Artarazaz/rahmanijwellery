"""Market data integration, normalization and history for the public API."""

from __future__ import annotations

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from http.client import IncompleteRead
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.utils import timezone

from .models import MarketSnapshot


SYMBOLS = (
    "gold18",
    "gold24",
    "usd",
    "eur",
    "silver",
    "tether",
    "coin_full",
    "coin_half",
    "coin_quarter",
    "ounce",
    "oil",
)
GLOBAL_SYMBOLS = {"ounce", "oil"}
LOCAL_PRICE_SYMBOLS = set(SYMBOLS) - GLOBAL_SYMBOLS
SYMBOL_ALIASES = {
    "gold18": ("gold18", "gold18k", "gold_18k", "geram18", "geram18k", "18k", "gold18karat"),
    "gold24": ("gold24", "gold24k", "gold_24k", "geram24", "geram24k", "24k", "gold24karat"),
    "usd": ("usd", "dollar", "dollaram", "us dollar", "us_dollar", "dollarusa"),
    "eur": ("eur", "euro", "euros"),
    "silver": ("silver", "silver999", "silver_999", "xag", "noghre", "geramnaghre"),
    "tether": ("tether", "usdt", "cryptotether"),
    "coin_full": ("coinfull", "sekeb", "baharazadi", "fullcoin"),
    "coin_half": ("coinhalf", "nim", "halfcoin"),
    "coin_quarter": ("coinquarter", "rob", "quartercoin"),
    "ounce": ("ounce", "ons", "goldounce"),
    "oil": ("oil", "brentoil", "energybrentoil"),
}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PERSIAN_WEEKDAYS = ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه")
CACHE_KEY = "rahmani:market:latest:v1"
_FETCH_LOCK = threading.Lock()
TEHRAN_ZONE = ZoneInfo("Asia/Tehran")


class ProviderError(RuntimeError):
    """Raised when the configured market provider cannot return valid data."""


def _setting(name: str, default):
    return getattr(settings, name, default)


def _normalise_text(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower().translate(PERSIAN_DIGITS))


def _as_decimal(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    text = str(value).translate(PERSIAN_DIGITS).replace(",", "").replace("٬", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def _number(value: Decimal | None):
    if value is None:
        return None
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _padded_number(value: Decimal | None) -> str:
    number = _number(value)
    if number is None:
        return "—"
    return f"{number:,}".translate(PERSIAN_DIGITS)


def _symbol_from_text(*parts) -> str | None:
    text = _normalise_text(" ".join(str(part) for part in parts if part is not None))
    if not text:
        return None
    for symbol, aliases in SYMBOL_ALIASES.items():
        if any(_normalise_text(alias) in text for alias in aliases):
            return symbol
    return None


def _value_from_record(record: dict):
    preferred = ("value", "price", "last", "close", "rate", "amount", "p", "sell", "mid")
    for key in preferred:
        if key in record:
            value = _as_decimal(record[key])
            if value is not None:
                return value
    for key, value in record.items():
        if key in {"symbol", "name", "code", "item", "id", "title", "timestamp", "time", "date"}:
            continue
        parsed = _as_decimal(value)
        if parsed is not None:
            return parsed
    return None


def _records(payload, key_hint=""):
    """Yield (symbol hint, record) pairs from common JSON API envelopes."""
    if isinstance(payload, dict):
        if _value_from_record(payload) is not None:
            yield key_hint, payload
        for key, value in payload.items():
            if key in {"timestamp", "updated_at", "status", "success", "message"}:
                continue
            yield from _records(value, key)
    elif isinstance(payload, list):
        for item in payload:
            yield from _records(item, key_hint)
    elif _as_decimal(payload) is not None:
        yield key_hint, {"value": payload}


def _extract_prices(payload) -> dict[str, Decimal]:
    prices: dict[str, Decimal] = {}
    for hint, record in _records(payload):
        if not isinstance(record, dict):
            continue
        symbol = _symbol_from_text(
            hint,
            record.get("symbol"),
            record.get("name"),
            record.get("code"),
            record.get("item"),
            record.get("id"),
            record.get("title"),
        )
        value = _value_from_record(record)
        if symbol and value is not None and symbol not in prices:
            prices[symbol] = value

    if set(prices) != set(SYMBOLS):
        missing = ", ".join(symbol for symbol in SYMBOLS if symbol not in prices)
        raise ProviderError(f"Provider response is missing: {missing}")
    return prices


def _provider_timestamp(payload) -> datetime | None:
    candidates = []
    if isinstance(payload, dict):
        for key in ("timestamp", "updated_at", "updatedAt", "time", "date"):
            if payload.get(key):
                candidates.append(payload[key])
        for envelope in ("data", "result", "meta"):
            nested = payload.get(envelope)
            if isinstance(nested, dict):
                for key in ("timestamp", "updated_at", "updatedAt", "time", "date"):
                    if nested.get(key):
                        candidates.append(nested[key])
    for candidate in candidates:
        if isinstance(candidate, (int, float)):
            try:
                return datetime.fromtimestamp(candidate, tz=dt_timezone.utc)
            except (OverflowError, OSError, ValueError):
                continue
        try:
            parsed = datetime.fromisoformat(str(candidate).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
    return None


def _provider_url() -> str:
    url = str(_setting("MARKET_PROVIDER_URL", "")).strip()
    provider = str(_setting("MARKET_PROVIDER", "tgju")).lower()
    if not url:
        raise ProviderError("MARKET_PROVIDER_URL is not configured")

    params = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    items = str(_setting("MARKET_PROVIDER_ITEMS", "usd,eur,geram18,geram24,silver_999")).strip()
    token = str(_setting("MARKET_PROVIDER_TOKEN", "")).strip()
    if provider == "tgju":
        params.setdefault("items", items)
        if token:
            params.setdefault("token", token)
    query = urlencode(params)
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _fetch_provider_payload():
    provider = str(_setting("MARKET_PROVIDER", "tgju")).lower()
    if provider == "tgju_scrape":
        return _fetch_tgju_scrape_payload()
    url = _provider_url()
    token = str(_setting("MARKET_PROVIDER_TOKEN", "")).strip()
    headers = {"Accept": "application/json", "User-Agent": "RahmaniMarket/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=float(_setting("MARKET_PROVIDER_TIMEOUT_SECONDS", 8))) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise ProviderError(f"Market provider request failed: {error}") from error
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderError("Market provider returned invalid JSON") from error


class _TGJUPriceTableParser(HTMLParser):
    """Small, dependency-free parser for TGJU's public price tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            attrs_map = dict(attrs)
            self.row = {
                "cells": [],
                "href": None,
                "market_row": attrs_map.get("data-market-row"),
                "data_price": attrs_map.get("data-price"),
            }
        elif self.row is not None and tag in {"td", "th"}:
            self.cell = []
        elif self.row is not None and tag == "a":
            href = dict(attrs).get("href", "")
            if href and "profile/" in href:
                self.row["href"] = href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.row is not None and self.cell is not None:
            self.row["cells"].append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def _fetch_tgju_html(url):
    last_error = None
    for _attempt in range(2):
        request = Request(
            url,
            headers={"Accept": "text/html", "User-Agent": "RahmaniMarket/1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=float(_setting("MARKET_PROVIDER_TIMEOUT_SECONDS", 8))) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as error:
            last_error = error
    raise ProviderError(f"TGJU page request failed: {last_error}") from last_error


def _scrape_tgju_page(url):
    parser = _TGJUPriceTableParser()
    parser.feed(_fetch_tgju_html(url))
    return parser.rows


def _fetch_tgju_profile_current(slug):
    profile_base_url = str(_setting("TGJU_PROFILE_BASE_URL", "https://www.tgju.org/profile")).rstrip("/")
    rows = _scrape_tgju_page(f"{profile_base_url}/{slug}")
    # The profile table explicitly labels this value as "نرخ فعلی".
    for row in rows:
        cells = row.get("cells", [])
        if not cells or "نرخ فعلی" not in cells[0].replace("‌", ""):
            continue
        for cell in cells[1:]:
            value = _as_decimal(cell)
            if value is not None:
                return value
    raise ProviderError(f"TGJU profile {slug} is missing its current rate")


def _fetch_tgju_local_tether_current():
    """Read the first active USDT/IRR sell quote from TGJU's local market table."""
    profile_base_url = str(_setting("TGJU_PROFILE_BASE_URL", "https://www.tgju.org/profile")).rstrip("/")
    rows = _scrape_tgju_page(f"{profile_base_url}/crypto-tether/markets-local")
    for row in rows:
        cells = row.get("cells", [])
        if len(cells) < 3 or "USDT / IRR" not in cells[1].upper():
            continue
        value = _as_decimal(cells[2])
        if value is not None:
            return value
    raise ProviderError("TGJU local tether market has no active USDT/IRR quote")


def _extract_tgju_market_list(payload, slugs):
    prices = {}
    for row in payload.get("data", []):
        if len(row) < 2:
            continue
        match = re.search(r"profile[\\/]([a-z0-9_]+)", str(row[0]), flags=re.IGNORECASE)
        slug = match.group(1) if match else None
        if slug not in slugs:
            continue
        value = _as_decimal(row[1])
        if value is not None:
            prices[slug] = value
    return prices


def _extract_tgju_market_rows(html, slugs):
    """Extract current values from TGJU's HTML market rows."""
    parser = _TGJUPriceTableParser()
    parser.feed(html)
    prices = {}
    for row in parser.rows:
        slug = str(row.get("market_row") or "").strip()
        if slug not in slugs:
            continue
        value = _as_decimal(row.get("data_price"))
        if value is not None:
            prices[slug] = value
    return prices


def _extract_tgju_global_market_rows(html, slugs):
    """Extract current values from TGJU's global-market ticker rows."""
    prices = {}
    pattern = re.compile(
        r'<li\b[^>]*id=["\']l-([^"\']+)["\'][^>]*>.*?'
        r'<span\b[^>]*class=["\'][^"\']*info-price[^"\']*["\'][^>]*>(.*?)</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        slug = match.group(1).strip()
        if slug not in slugs:
            continue
        value = _as_decimal(re.sub(r"<[^>]+>", " ", match.group(2)))
        if value is not None:
            prices[slug] = value
    return prices


def _fetch_tgju_scrape_payload():
    market_list_url = str(
        _setting("TGJU_MARKET_LIST_API_URL", "https://api.tgju.org/v1/market/list-data")
    )
    local_markets_url = str(
        _setting("TGJU_LOCAL_MARKETS_URL", "https://www.tgju.org/local-markets")
    )
    global_markets_url = str(
        _setting(
            "TGJU_GLOBAL_MARKETS_URL",
            "https://www.tgju.org/profile/crypto-page/markets-global",
        )
    )

    def fetch_market_list(category_id):
        return _fetch_tgju_json(
            market_list_url,
            {"category_ids": category_id, "extra_data": "1", "lang": "fa"},
        )

    def fetch_local_markets():
        return _extract_tgju_market_rows(
            _fetch_tgju_html(local_markets_url),
            {"sekeb", "nim", "rob", "ons"},
        )

    def fetch_global_markets():
        return _extract_tgju_global_market_rows(_fetch_tgju_html(global_markets_url), {"oil_brent"})

    extracted = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        gold_future = executor.submit(fetch_market_list, _setting("TGJU_GOLD_CATEGORY_ID", "91818"))
        currency_future = executor.submit(fetch_market_list, _setting("TGJU_CURRENCY_CATEGORY_ID", "28070"))
        local_future = executor.submit(fetch_local_markets)
        global_future = executor.submit(fetch_global_markets)
        profile_futures = {
            "silver": executor.submit(_fetch_tgju_profile_current, "silver_999"),
            "tether": executor.submit(_fetch_tgju_local_tether_current),
        }
        gold_prices = _extract_tgju_market_list(gold_future.result(), {"geram18", "geram24"})
        extracted.update(
            {
                "gold18": gold_prices.get("geram18"),
                "gold24": gold_prices.get("geram24"),
            }
        )
        currency_prices = _extract_tgju_market_list(
            currency_future.result(), {"price_dollar_rl", "price_eur"}
        )
        extracted.update(
            {"usd": currency_prices.get("price_dollar_rl"), "eur": currency_prices.get("price_eur")}
        )
        local_prices = local_future.result()
        extracted.update(
            {
                "coin_full": local_prices.get("sekeb"),
                "coin_half": local_prices.get("nim"),
                "coin_quarter": local_prices.get("rob"),
                "ounce": local_prices.get("ons"),
            }
        )
        extracted["oil"] = global_future.result().get("oil_brent")
        for symbol, future in profile_futures.items():
            extracted[symbol] = future.result()

    missing = [symbol for symbol in SYMBOLS if extracted.get(symbol) is None]
    if missing:
        raise ProviderError(f"TGJU public pages are missing: {', '.join(missing)}")
    return {
        "prices": {symbol: {"value": str(extracted[symbol])} for symbol in SYMBOLS},
        "timestamp": timezone.now().isoformat(),
    }


def _fetch_tgju_json(url, params):
    query = urlencode(params)
    last_error = None
    for _attempt in range(2):
        request = Request(
            f"{url}{'&' if '?' in url else '?'}{query}",
            headers={"Accept": "application/json", "User-Agent": "RahmaniMarket/1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=float(_setting("MARKET_PROVIDER_TIMEOUT_SECONDS", 8))) as response:
                raw = response.read()
            break
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead) as error:
            last_error = error
    else:
        raise ProviderError(f"TGJU history request failed: {last_error}") from last_error
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderError("TGJU history endpoint returned invalid JSON") from error


def _tgju_display_gold(value):
    converted = _convert_to_display_unit({"gold18": value})
    return converted["gold18"]


def _fetch_tgju_daily_history():
    payload = _fetch_tgju_json(
        str(_setting(
            "TGJU_HISTORY_API_URL",
            "https://api.tgju.org/v1/market/indicator/summary-table-data/geram18",
        )),
        {
            "lang": "fa",
            "draw": "1",
            "start": "0",
            "length": str(_setting("TGJU_HISTORY_PAGE_LENGTH", 5000)),
            "search": "",
            "order_col": "timestamp",
            "order_dir": "asc",
            "from": "",
            "to": "",
            "convert_to_ad": "1",
        },
    )
    rows = []
    for row in payload.get("data", []):
        if len(row) < 8:
            continue
        close = _as_decimal(row[3])
        try:
            date_value = datetime.strptime(str(row[6]).strip(), "%Y/%m/%d").date()
        except ValueError:
            continue
        if close is not None:
            rows.append((date_value, _tgju_display_gold(close)))
    if len(rows) < 7:
        raise ProviderError("TGJU history endpoint returned fewer than seven daily points")
    return rows


def _fetch_tgju_intraday_history():
    html = _fetch_tgju_html(str(_setting("TGJU_PROFILE_URL", "https://www.tgju.org/profile/geram18")))
    match = re.search(
        r'\$\("#ChartBlock-1"\)\.msHighcharts\(\{\s*chartData:\s*(\[\[.*?\]\])\s*,\s*chartType:\s*"candlestick"',
        html,
        flags=re.DOTALL,
    )
    if not match:
        raise ProviderError("TGJU profile page does not contain intraday chart data")
    try:
        chart_data = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ProviderError("TGJU profile page returned invalid intraday chart data") from error

    points = []
    for row in chart_data:
        if len(row) < 5:
            continue
        try:
            captured_at = datetime.fromtimestamp(float(row[0]) / 1000, tz=dt_timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        close = _as_decimal(row[-1])
        if close is not None:
            points.append((captured_at, _tgju_display_gold(close)))
    if len(points) < 7:
        raise ProviderError("TGJU profile page returned fewer than seven intraday points")
    return points


def _convert_to_display_unit(prices: dict[str, Decimal]) -> dict[str, Decimal]:
    provider_unit = str(_setting("MARKET_PROVIDER_UNIT", "rial")).lower()
    display_unit = str(_setting("MARKET_DISPLAY_UNIT", "toman")).lower()
    converted = dict(prices)
    if provider_unit == display_unit:
        return converted
    if provider_unit == "rial" and display_unit == "toman":
        return {
            symbol: value / Decimal("10") if symbol in LOCAL_PRICE_SYMBOLS else value
            for symbol, value in converted.items()
        }
    if provider_unit == "toman" and display_unit == "rial":
        return {
            symbol: value * Decimal("10") if symbol in LOCAL_PRICE_SYMBOLS else value
            for symbol, value in converted.items()
        }
    raise ProviderError(f"Unsupported unit conversion: {provider_unit} -> {display_unit}")


def _display_unit_for_symbol(symbol):
    return "usd" if symbol in GLOBAL_SYMBOLS else str(_setting("MARKET_DISPLAY_UNIT", "toman"))


def _change(current: Decimal, previous) -> Decimal | None:
    previous = _as_decimal(previous)
    if previous in (None, Decimal("0")):
        return None
    change = ((current - previous) / previous * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    # Avoid serializing Decimal("-0.00"), which is mathematically zero but
    # can be rendered as a misleading downward movement in the UI.
    return Decimal("0.00") if change == Decimal("0") else change


def _first_snapshot_of_day(provider, captured_at):
    """Return the first complete snapshot today for daily percentage baselines."""
    day_start = _local_bucket(captured_at, "daily")
    snapshots = MarketSnapshot.objects.filter(
        provider=provider,
        captured_at__gte=day_start,
    ).order_by("captured_at")
    for snapshot in snapshots.iterator():
        if all(_as_decimal(snapshot.prices.get(symbol)) is not None for symbol in SYMBOLS):
            return snapshot
    return None


def seed_market_history():
    """Persist real TGJU points used to initialize the chart periods."""
    daily_history = _fetch_tgju_daily_history()
    intraday_history = _fetch_tgju_intraday_history()

    latest_live = MarketSnapshot.objects.filter(provider="tgju_scrape").first()
    base_prices = {
        symbol: _as_decimal(latest_live.prices.get(symbol)) if latest_live else None
        for symbol in SYMBOLS
    }
    if any(value is None for value in base_prices.values()):
        provider_payload = _fetch_provider_payload()
        base_prices = _convert_to_display_unit(_extract_prices(provider_payload))

    recent_daily = daily_history[-7:]
    monthly_closes = {}
    for date_value, price in daily_history:
        monthly_closes[(date_value.year, date_value.month)] = (date_value, price)
    recent_monthly = list(monthly_closes.values())[-7:]

    points = []
    for captured_at, price in intraday_history[-7:]:
        points.append((captured_at, price))
    for date_value, price in recent_daily:
        points.append((datetime(date_value.year, date_value.month, date_value.day, 15, tzinfo=TEHRAN_ZONE), price))
    for date_value, price in recent_monthly:
        points.append((datetime(date_value.year, date_value.month, date_value.day, 15, tzinfo=TEHRAN_ZONE), price))

    unique_points = {}
    for captured_at, price in points:
        unique_points[(captured_at, str(price))] = (captured_at, price)

    previous_gold = None
    saved = {"intraday": len(intraday_history[-7:]), "daily": len(recent_daily), "monthly": len(recent_monthly)}
    with transaction.atomic():
        MarketSnapshot.objects.filter(provider="tgju_history_seed").delete()
        for captured_at, gold18 in sorted(unique_points.values(), key=lambda item: item[0]):
            prices = dict(base_prices)
            prices["gold18"] = gold18
            change = _change(gold18, previous_gold)
            MarketSnapshot.objects.create(
                provider="tgju_history_seed",
                unit=str(_setting("MARKET_DISPLAY_UNIT", "toman")),
                prices={symbol: str(prices[symbol]) for symbol in SYMBOLS},
                changes={
                    symbol: (str(change) if symbol == "gold18" and change is not None else None)
                    for symbol in SYMBOLS
                },
                provider_timestamp=captured_at,
                captured_at=captured_at,
            )
            previous_gold = gold18
    clear_market_cache()
    return saved


def _snapshot_payload(snapshot: MarketSnapshot, stale=False, error=None, chart=None):
    prices = {}
    for symbol in SYMBOLS:
        value = _as_decimal(snapshot.prices.get(symbol))
        change = _as_decimal(snapshot.changes.get(symbol))
        prices[symbol] = {
            "value": _number(value),
            "formatted": _padded_number(value),
            "change_percent": _number(change),
            "unit": _display_unit_for_symbol(symbol),
        }
    payload = {
        "timestamp": snapshot.captured_at.isoformat(),
        "provider_timestamp": snapshot.provider_timestamp.isoformat() if snapshot.provider_timestamp else None,
        "unit": snapshot.unit,
        "provider": snapshot.provider,
        "stale": stale,
        "prices": prices,
        "chart": chart if chart is not None else build_chart_data(),
    }
    if error:
        payload["error"] = error
    return payload


def refresh_market_snapshot():
    """Fetch TGJU once and persist a complete, normalized market snapshot."""
    with _FETCH_LOCK:
        provider_payload = _fetch_provider_payload()
        prices = _convert_to_display_unit(_extract_prices(provider_payload))
        provider = str(_setting("MARKET_PROVIDER", "tgju_scrape"))
        captured_at = timezone.now()
        first_today = _first_snapshot_of_day(provider, captured_at)
        baseline_prices = first_today.prices if first_today else {}
        changes = {symbol: _change(prices[symbol], baseline_prices.get(symbol)) for symbol in SYMBOLS}
        snapshot = MarketSnapshot.objects.create(
            provider=provider,
            unit=str(_setting("MARKET_DISPLAY_UNIT", "toman")),
            prices={symbol: str(prices[symbol]) for symbol in SYMBOLS},
            changes={symbol: str(changes[symbol]) if changes[symbol] is not None else None for symbol in SYMBOLS},
            provider_timestamp=_provider_timestamp(provider_payload),
            captured_at=captured_at,
        )
        clear_market_cache()
        return snapshot


def _is_vercel_runtime():
    return str(os.getenv("VERCEL", "")).strip().lower() in {"1", "true", "yes", "on"}


def _append_live_chart_point(chart, captured_at, gold18):
    """Add a non-persisted Vercel reading to the chart response."""
    for period in ("hourly", "daily", "monthly"):
        source = chart[period]
        bucket = _local_bucket(captured_at, period)
        label = _chart_label(bucket, period)
        value = _number(gold18)
        if source["labels"] and source["labels"][-1] == label:
            source["values"][-1] = value
            source["data"][-1] = value
        else:
            source["labels"].append(label)
            source["values"].append(value)
            source["data"].append(value)
            source["labels"] = source["labels"][-7:]
            source["values"] = source["values"][-7:]
            source["data"] = source["data"][-7:]


def _live_chart_without_database(captured_at, gold18):
    """Return a usable first chart point when Vercel has no SQLite file."""
    value = _number(gold18)
    chart = {}
    for period in ("hourly", "daily", "monthly"):
        bucket = _local_bucket(captured_at, period)
        chart[period] = {
            "labels": [_chart_label(bucket, period)],
            "values": [value],
            "data": [value],
        }
    return chart


def _get_vercel_live_market_data(previous):
    """Fetch a transient live payload when Vercel has no long-running worker."""
    provider_payload = _fetch_provider_payload()
    prices = _convert_to_display_unit(_extract_prices(provider_payload))
    captured_at = timezone.now()
    provider = str(_setting("MARKET_PROVIDER", "tgju_scrape"))
    try:
        first_today = _first_snapshot_of_day(provider, captured_at)
        baseline_prices = first_today.prices if first_today else {}
    except DatabaseError:
        baseline_prices = {}
    changes = {symbol: _change(prices[symbol], baseline_prices.get(symbol)) for symbol in SYMBOLS}
    snapshot = MarketSnapshot(
        provider=provider,
        unit=str(_setting("MARKET_DISPLAY_UNIT", "toman")),
        prices={symbol: str(prices[symbol]) for symbol in SYMBOLS},
        changes={symbol: str(changes[symbol]) if changes[symbol] is not None else None for symbol in SYMBOLS},
        provider_timestamp=_provider_timestamp(provider_payload),
        captured_at=captured_at,
    )
    try:
        snapshot = MarketSnapshot.objects.create(
            provider=snapshot.provider,
            unit=snapshot.unit,
            prices=snapshot.prices,
            changes=snapshot.changes,
            provider_timestamp=snapshot.provider_timestamp,
            captured_at=snapshot.captured_at,
        )
    except DatabaseError:
        pass
    try:
        chart = build_chart_data()
    except DatabaseError:
        chart = _live_chart_without_database(captured_at, prices["gold18"])
    _append_live_chart_point(chart, captured_at, prices["gold18"])
    return _snapshot_payload(snapshot, stale=False, chart=chart)


def get_market_data(force=False):
    """Read persisted data, with a serverless fallback for Vercel deployments."""
    try:
        snapshot = MarketSnapshot.objects.first()
    except DatabaseError:
        if _is_vercel_runtime():
            return _get_vercel_live_market_data(None)
        raise
    if snapshot is None:
        if _is_vercel_runtime():
            return _get_vercel_live_market_data(None)
        raise ProviderError("No market snapshot has been collected yet")
    stale_default = 10 if _is_vercel_runtime() else 30
    stale_after = int(_setting("MARKET_SNAPSHOT_STALE_AFTER_SECONDS", stale_default))
    stale = timezone.now() - snapshot.captured_at > timedelta(seconds=stale_after)
    if _is_vercel_runtime() and stale:
        try:
            return _get_vercel_live_market_data(snapshot)
        except ProviderError as error:
            return _snapshot_payload(snapshot, stale=True, error=str(error))
    return _snapshot_payload(snapshot, stale=stale)


def clear_market_cache():
    cache.delete(CACHE_KEY)


def _local_bucket(snapshot_time, period):
    local_time = timezone.localtime(snapshot_time, dt_timezone(timedelta(hours=3, minutes=30)))
    if period == "hourly":
        return local_time.replace(minute=0, second=0, microsecond=0)
    if period == "daily":
        return local_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _chart_label(bucket, period):
    if period == "hourly":
        return f"{bucket:%H:%M}".translate(PERSIAN_DIGITS)
    if period == "daily":
        return f"{bucket:%m/%d}".translate(PERSIAN_DIGITS)
    return f"{bucket:%Y/%m}".translate(PERSIAN_DIGITS)


def build_chart_data(periods=("hourly", "daily", "monthly"), limit=7):
    now = timezone.now()
    windows = {"hourly": timedelta(days=7), "daily": timedelta(days=45), "monthly": timedelta(days=730)}
    result = {}
    for period in periods:
        snapshots = MarketSnapshot.objects.filter(captured_at__gte=now - windows[period]).order_by("captured_at")
        buckets = {}
        for snapshot in snapshots:
            value = _as_decimal(snapshot.prices.get("gold18"))
            if value is not None:
                bucket = _local_bucket(snapshot.captured_at, period)
                if period == "hourly" and snapshot.provider == "tgju_history_seed":
                    local_time = timezone.localtime(snapshot.captured_at, TEHRAN_ZONE)
                    bucket = local_time.replace(
                        minute=(local_time.minute // 10) * 10,
                        second=0,
                        microsecond=0,
                    )
                buckets[bucket] = value
        selected = list(buckets.items())[-limit:]
        result[period] = {
            "labels": [_chart_label(bucket, period) for bucket, _ in selected],
            "values": [_number(value) for _, value in selected],
            "data": [_number(value) for _, value in selected],
        }
    return result


def get_history(period="hourly", limit=7):
    if period not in {"hourly", "daily", "monthly"}:
        raise ValueError("period must be hourly, daily or monthly")
    limit = max(1, min(int(limit), 30))
    return build_chart_data((period,), limit=limit)[period]
