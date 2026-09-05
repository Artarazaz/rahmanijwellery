import time

from django.conf import settings
from django.core.management.base import BaseCommand

from prices.services import ProviderError, refresh_market_snapshot


class Command(BaseCommand):
    help = "Scrape TGJU prices and persist a snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Keep running and refresh repeatedly.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=int(getattr(settings, "MARKET_UPDATE_INTERVAL_SECONDS", 30)),
            help="Seconds between refreshes when --watch is enabled.",
        )

    def handle(self, *args, **options):
        interval = max(5, options["interval"])
        while True:
            started = time.monotonic()
            try:
                snapshot = refresh_market_snapshot()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Saved Moj3 snapshot #{snapshot.pk} at {snapshot.captured_at.isoformat()}"
                    )
                )
            except ProviderError as error:
                self.stderr.write(self.style.ERROR(f"Moj3 scrape failed: {error}"))
            except Exception as error:
                self.stderr.write(self.style.ERROR(f"Unexpected scrape error: {error}"))

            if not options["watch"]:
                break
            time.sleep(max(0, interval - (time.monotonic() - started)))
