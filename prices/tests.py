import json
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import MarketSnapshot
from .services import (
    ProviderError,
    _TGJUPriceTableParser,
    _change,
    _extract_tgju_global_market_rows,
    _extract_prices,
    _extract_tgju_market_rows,
    _extract_tgju_market_list,
    _fetch_provider_payload,
    _fetch_tgju_local_tether_current,
    clear_market_cache,
    get_market_data,
    refresh_market_snapshot,
)


@override_settings(
    MARKET_PROVIDER_URL="https://provider.test/market",
    MARKET_PROVIDER_UNIT="toman",
    MARKET_DISPLAY_UNIT="toman",
    MARKET_PRICE_CACHE_SECONDS=5,
)
class MarketApiTests(TestCase):
    def setUp(self):
        clear_market_cache()

    @staticmethod
    def provider_payload(gold18="10000000"):
        return {
            "data": [
                {"symbol": "geram18", "price": gold18},
                {"symbol": "geram24", "price": "13333333"},
                {"symbol": "usd", "price": "59200"},
                {"symbol": "eur", "price": "64500"},
                {"symbol": "silver_999", "price": "58000"},
                {"symbol": "tether", "price": "60000"},
                {"symbol": "coin_full", "price": "170000000"},
                {"symbol": "coin_half", "price": "90000000"},
                {"symbol": "coin_quarter", "price": "50000000"},
                {"symbol": "ounce", "price": "2500.25"},
                {"symbol": "oil", "price": "75.50"},
            ]
        }

    @patch("prices.services._fetch_provider_payload")
    def test_market_endpoint_calculates_change_from_first_complete_snapshot_of_day(self, fetch):
        fetch.return_value = self.provider_payload()
        MarketSnapshot.objects.create(
            provider="tgju_scrape",
            unit="toman",
            prices={"gold18": "9900000", "gold24": "13200000", "usd": "59000", "eur": "64000", "silver": "57000"},
            changes={},
            captured_at=timezone.now() - timedelta(minutes=5),
        )
        refresh_market_snapshot()
        first = self.client.get("/api/market/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["Cache-Control"], "no-store, max-age=0")
        self.assertIsNone(first.json()["prices"]["gold18"]["change_percent"])

        fetch.return_value = self.provider_payload("10500000")
        refresh_market_snapshot()
        second = self.client.get("/api/market/")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["prices"]["gold18"]["value"], 10500000)
        self.assertEqual(second.json()["prices"]["gold18"]["change_percent"], 5.0)

        fetch.return_value = self.provider_payload("11000000")
        refresh_market_snapshot()
        third = self.client.get("/api/market/")
        self.assertEqual(third.json()["prices"]["gold18"]["change_percent"], 10.0)
        self.assertEqual(third.json()["prices"]["ounce"]["unit"], "usd")

    @patch("prices.services._fetch_provider_payload")
    def test_provider_failure_returns_last_snapshot_as_stale(self, fetch):
        fetch.return_value = self.provider_payload()
        refresh_market_snapshot()
        fetch.side_effect = ProviderError("provider offline")
        with self.assertRaises(ProviderError):
            refresh_market_snapshot()
        MarketSnapshot.objects.update(captured_at=timezone.now() - timedelta(seconds=60))
        response = self.client.get("/api/market/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["stale"])
        self.assertEqual(response.json()["prices"]["gold18"]["value"], 10000000)

    @patch("prices.services._fetch_provider_payload")
    def test_history_endpoint_returns_saved_chart_values(self, fetch):
        fetch.return_value = self.provider_payload("10000000")
        refresh_market_snapshot()
        fetch.return_value = self.provider_payload("10100000")
        refresh_market_snapshot()
        response = self.client.get("/api/market/history/?period=hourly&limit=7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["period"], "hourly")
        self.assertEqual(response.json()["values"][-1], 10100000)

    def test_history_rejects_unknown_period(self):
        response = self.client.get("/api/market/history/?period=weekly")
        self.assertEqual(response.status_code, 400)

    def test_tgju_html_parser_reads_profile_rows(self):
        parser = _TGJUPriceTableParser()
        parser.feed(
            '<table><tr><th>طلای 18</th><td>10,000,000</td><td>(1%)</td>'
            '<td><a href="profile/geram18">نمودار</a></td></tr></table>'
        )
        self.assertEqual(parser.rows[0]["href"], "geram18")
        self.assertEqual(parser.rows[0]["cells"][1], "10,000,000")

    def test_tgju_market_list_parser_uses_the_current_value_column(self):
        payload = {
            "data": [
                ['<a href="profile/geram18">طلای 18</a>', '<span>193,500,000</span>', '18:00'],
                ['<a href="profile/price_eur">یورو</a>', '<span>2,169,000</span>', '18:00'],
            ]
        }
        self.assertEqual(
            _extract_tgju_market_list(payload, {"geram18", "price_eur"}),
            {"geram18": Decimal("193500000"), "price_eur": Decimal("2169000")},
        )

    def test_tgju_html_market_row_parser_reads_current_values(self):
        html = (
            '<tr data-market-row="sekeb" data-title="<div>1</div>" data-price="1,909,300,000"><td>سکه</td></tr>'
            '<tr data-market-row="nim" data-price="980,000,000"><td>نیم</td></tr>'
        )
        self.assertEqual(
            _extract_tgju_market_rows(html, {"sekeb", "nim"}),
            {"sekeb": Decimal("1909300000"), "nim": Decimal("980000000")},
        )

    def test_tgju_global_market_parser_reads_ticker_values(self):
        html = '<li id="l-oil_brent"><span class="info-price">91.932</span></li>'
        self.assertEqual(
            _extract_tgju_global_market_rows(html, {"oil_brent"}),
            {"oil_brent": Decimal("91.932")},
        )

    @patch("prices.services._fetch_tgju_json")
    def test_tgju_tether_parser_uses_json_api_first(self, fetch_json):
        """Primary path: reads USDT/IRR from JSON summary API (works on Vercel)."""
        fetch_json.return_value = {
            "data": [["274,000", "270,000", "274,000", "273,000"]],
            "recordsTotal": 45,
        }
        self.assertEqual(_fetch_tgju_local_tether_current(), Decimal("273000"))

    @patch("prices.services._scrape_tgju_page")
    @patch("prices.services._fetch_tgju_json", side_effect=ProviderError("JSON API unavailable"))
    def test_tgju_tether_parser_falls_back_to_local_usdt_quote(self, _fetch_json, scrape):
        """Fallback path: reads USDT/IRR from HTML scraping (works on local server)."""
        scrape.return_value = [
            {"cells": ["ارزاینجا", "USDT / IRR", "1,894,500", "1,894,500"]},
        ]
        self.assertEqual(_fetch_tgju_local_tether_current(), Decimal("1894500"))

    @override_settings(
        MARKET_PROVIDER="tgju",
        MARKET_PROVIDER_URL="https://provider.test/market",
    )
    @patch("prices.services._fetch_tgju_scrape_payload")
    @patch("prices.services.urlopen")
    def test_official_provider_response_is_enriched_with_new_symbols(self, urlopen, scrape):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"data": [
            {"symbol": "geram18", "price": "10000000"},
            {"symbol": "geram24", "price": "13333333"},
            {"symbol": "usd", "price": "59200"},
            {"symbol": "eur", "price": "64500"},
            {"symbol": "silver_999", "price": "58000"},
        ]}).encode("utf-8")
        urlopen.return_value = response
        scrape.return_value = self.provider_payload()

        payload = _fetch_provider_payload()

        self.assertEqual(set(_extract_prices(payload)), {
            "gold18", "gold24", "usd", "eur", "silver", "tether",
            "coin_full", "coin_half", "coin_quarter", "ounce", "oil",
        })

    def test_change_does_not_return_negative_zero(self):
        self.assertEqual(_change(Decimal("100000"), Decimal("100001")), Decimal("0.00"))

    @patch.dict(os.environ, {"VERCEL": "1"})
    @patch("prices.services._fetch_provider_payload")
    def test_vercel_reads_live_data_when_saved_snapshot_is_stale(self, fetch):
        fetch.return_value = self.provider_payload("10500000")
        MarketSnapshot.objects.create(
            provider="tgju_scrape",
            unit="toman",
            prices={
                "gold18": "10000000",
                "gold24": "13333333",
                "usd": "59200",
                "eur": "64500",
                "silver": "58000",
            },
            changes={symbol: None for symbol in (
                "gold18", "gold24", "usd", "eur", "silver", "tether",
                "coin_full", "coin_half", "coin_quarter", "ounce", "oil",
            )},
            captured_at=timezone.now() - timedelta(seconds=60),
        )
        payload = get_market_data()
        self.assertFalse(payload["stale"])
        self.assertEqual(payload["prices"]["gold18"]["value"], 10500000)

    @patch.dict(os.environ, {"VERCEL": "1"})
    @patch("prices.services.MarketSnapshot.objects.first", side_effect=OperationalError("no such table"))
    @patch("prices.services._fetch_provider_payload")
    def test_vercel_reads_live_data_without_a_database_table(self, fetch, _first):
        fetch.return_value = self.provider_payload("10500000")
        payload = get_market_data()
        self.assertFalse(payload["stale"])
        self.assertEqual(payload["prices"]["gold18"]["value"], 10500000)
        self.assertEqual(len(payload["chart"]["hourly"]["data"]), 1)
