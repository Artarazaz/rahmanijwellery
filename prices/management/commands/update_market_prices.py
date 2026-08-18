import time

from django.conf import settings
from django.core.management.base import BaseCommand

from prices.services import ProviderError, refresh_market_snapshot


class Command(BaseCommand):
    help = "Fetch market prices and persist a normalized snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Keep running and refresh repeatedly.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=int(getattr(settings, "MARKET_UPDATE_INTERVAL_SECONDS", 10)),
            help="Seconds between refreshes when --watch is enabled.",
        )

    def handle(self, *args, **options):
        interval = max(1, options["interval"])
        while True:
            started = time.monotonic()
            try:
                snapshot = refresh_market_snapshot()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Saved market snapshot #{snapshot.pk} at {snapshot.captured_at.isoformat()}"
                    )
                )
            except ProviderError as error:
                self.stderr.write(self.style.ERROR(f"Market refresh failed: {error}"))
            except Exception as error:  # Keep a transient network/parser error from killing the worker.
                self.stderr.write(self.style.ERROR(f"Unexpected market refresh error: {error}"))

            if not options["watch"]:
                break
            time.sleep(max(0, interval - (time.monotonic() - started)))
