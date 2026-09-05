from django.core.management.base import BaseCommand

from prices.services import refresh_market_snapshot


class Command(BaseCommand):
    help = "Scrape current Moj3 prices so the chart has a first stored point."

    def handle(self, *args, **options):
        snapshot = refresh_market_snapshot()
        self.stdout.write(self.style.SUCCESS(f"Saved Moj3 snapshot #{snapshot.pk}"))
