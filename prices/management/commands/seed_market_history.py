from django.core.management.base import BaseCommand

from prices.services import seed_market_history


class Command(BaseCommand):
    help = "Seed chart history from TGJU's official daily and intraday data."

    def handle(self, *args, **options):
        counts = seed_market_history()
        self.stdout.write(
            self.style.SUCCESS(
                "Saved TGJU history: "
                f"{counts['intraday']} intraday, {counts['daily']} daily, "
                f"{counts['monthly']} monthly points."
            )
        )
