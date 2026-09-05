"""Market snapshots built from the TGJU price data (tgju.org)."""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.utils import timezone

from .models import MarketSnapshot
from .tgju import GLOBAL_SYMBOLS, SYMBOLS, ProviderError, as_decimal, scrape_tgju_prices

CACHE_KEY = "rahmani:market:latest:v2"
TEHRAN_ZONE = ZoneInfo("Asia/Tehran")
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _setting(name: str, default):
    return getattr(settings, name, default)


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


def _display_unit_for_symbol(symbol):
    return "usd" if symbol in GLOBAL_SYMBOLS else str(_setting("MARKET_DISPLAY_UNIT", "toman"))


def _change(current: Decimal, previous) -> Decimal | None:
    previous = as_decimal(previous)
    if previous in (None, Decimal("0")):
        return None
    change = ((current - previous) / previous * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return Decimal("0.00") if change == Decimal("0") else change


def _local_bucket(snapshot_time, period):
    local_time = timezone.localtime(snapshot_time, TEHRAN_ZONE)
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


def _first_snapshot_of_day(provider, captured_at):
    day_start = _local_bucket(captured_at, "daily")
    return (
        MarketSnapshot.objects.filter(provider=provider, captured_at__gte=day_start)
        .order_by("captured_at")
        .first()
    )


def _is_vercel_runtime():
    return str(os.getenv("VERCEL", "")).strip().lower() in {"1", "true", "yes", "on"}


def clear_market_cache():
    cache.delete(CACHE_KEY)


def build_chart_data(periods=("hourly", "daily", "monthly"), limit=7):
    now = timezone.now()
    windows = {"hourly": timedelta(days=7), "daily": timedelta(days=45), "monthly": timedelta(days=730)}
    result = {}
    for period in periods:
        snapshots = MarketSnapshot.objects.filter(captured_at__gte=now - windows[period]).order_by("captured_at")
        buckets = {}
        for snapshot in snapshots:
            value = as_decimal(snapshot.prices.get("gold18"))
            if value is None:
                continue
            buckets[_local_bucket(snapshot.captured_at, period)] = value
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


def _snapshot_payload(snapshot: MarketSnapshot, stale=False, error=None, chart=None):
    prices = {}
    for symbol in SYMBOLS:
        value = as_decimal(snapshot.prices.get(symbol))
        change = as_decimal(snapshot.changes.get(symbol))
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


def _persist_scrape(scraped: dict) -> MarketSnapshot:
    captured_at = timezone.now()
    provider = "tgju_scrape"
    prices = scraped["prices"]
    first_today = _first_snapshot_of_day(provider, captured_at)
    baseline = first_today.prices if first_today else {}
    changes = {}
    for symbol, value in prices.items():
        scraped_change = scraped["changes"].get(symbol)
        baseline_change = _change(value, baseline.get(symbol)) if baseline else None
        changes[symbol] = scraped_change if scraped_change is not None else baseline_change
    snapshot = MarketSnapshot.objects.create(
        provider=provider,
        unit=str(_setting("MARKET_DISPLAY_UNIT", "toman")),
        prices={symbol: str(prices[symbol]) for symbol in prices},
        changes={symbol: str(changes[symbol]) if changes.get(symbol) is not None else None for symbol in prices},
        provider_timestamp=captured_at,
        captured_at=captured_at,
    )
    clear_market_cache()
    return snapshot


def refresh_market_snapshot():
    """Scrape TGJU once and persist a market snapshot."""
    return _persist_scrape(scrape_tgju_prices())


def get_market_data(force=False):
    """Return the latest stored TGJU snapshot, scraping again when it is stale."""
    stale_default = 10 if _is_vercel_runtime() else 30
    stale_after = int(_setting("MARKET_SNAPSHOT_STALE_AFTER_SECONDS", stale_default))
    try:
        snapshot = MarketSnapshot.objects.first()
    except DatabaseError:
        snapshot = None

    stale = True
    if snapshot is not None:
        stale = timezone.now() - snapshot.captured_at > timedelta(seconds=stale_after)
    if force or snapshot is None or stale:
        try:
            snapshot = refresh_market_snapshot()
            stale = False
        except ProviderError as error:
            if snapshot is None:
                raise
            return _snapshot_payload(snapshot, stale=True, error=str(error))
        except DatabaseError:
            scraped = scrape_tgju_prices()
            captured_at = timezone.now()
            snapshot = MarketSnapshot(
                provider="tgju_scrape",
                unit=str(_setting("MARKET_DISPLAY_UNIT", "toman")),
                prices={symbol: str(value) for symbol, value in scraped["prices"].items()},
                changes={
                    symbol: str(value) if value is not None else None
                    for symbol, value in scraped["changes"].items()
                },
                provider_timestamp=captured_at,
                captured_at=captured_at,
            )
            chart = {
                period: {
                    "labels": [_chart_label(_local_bucket(captured_at, period), period)],
                    "values": [_number(scraped["prices"]["gold18"])],
                    "data": [_number(scraped["prices"]["gold18"])],
                }
                for period in ("hourly", "daily", "monthly")
            }
            return _snapshot_payload(snapshot, stale=False, chart=chart)
    return _snapshot_payload(snapshot, stale=stale)
