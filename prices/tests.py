from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from .models import MarketSnapshot
from .services import (
    ProviderError,
    _TGJUPriceTableParser,
    _change,
    _extract_tgju_market_list,
    clear_market_cache,
    refresh_market_snapshot,
)


@override_settings(
    MARKET_PROVIDER_URL="https://provider.test/market",
    MARKET_PROVIDER_UNIT="toman",
    MARKET_DISPLAY_UNIT="toman",
    MARKET_PRICE_CACHE_SECONDS=10,
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
            ]
        }

    @patch("prices.services._fetch_provider_payload")
    def test_market_endpoint_calculates_change_from_previous_snapshot(self, fetch):
        fetch.return_value = self.provider_payload()
        refresh_market_snapshot()
        first = self.client.get("/api/market/")
        self.assertEqual(first.status_code, 200)
        self.assertIsNone(first.json()["prices"]["gold18"]["change_percent"])

        fetch.return_value = self.provider_payload("10500000")
        refresh_market_snapshot()
        second = self.client.get("/api/market/")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["prices"]["gold18"]["value"], 10500000)
        self.assertEqual(second.json()["prices"]["gold18"]["change_percent"], 5.0)

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

    def test_change_does_not_return_negative_zero(self):
        self.assertEqual(_change(Decimal("100000"), Decimal("100001")), Decimal("0.00"))
