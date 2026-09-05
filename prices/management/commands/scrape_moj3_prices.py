from django.core.management.base import BaseCommand

from prices.services import ProviderError, refresh_market_snapshot


class Command(BaseCommand):
    help = "Scrape https://moj3.ir/price/ and store the prices in the database."

    def handle(self, *args, **options):
        try:
            snapshot = refresh_market_snapshot()
        except ProviderError as error:
            self.stderr.write(self.style.ERROR(str(error)))
            raise SystemExit(1) from error
        prices = ", ".join(f"{key}={value}" for key, value in snapshot.prices.items())
        self.stdout.write(self.style.SUCCESS(f"Saved Moj3 snapshot #{snapshot.pk}: {prices}"))
