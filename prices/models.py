from django.db import models
from django.utils import timezone


class GoldPrice(models.Model):
    karat = models.PositiveSmallIntegerField()
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.karat}K - {self.price}"


class MarketSnapshot(models.Model):
    """One verified market read used for deltas and chart history."""

    provider = models.CharField(max_length=40)
    unit = models.CharField(max_length=12, default="toman")
    prices = models.JSONField(default=dict)
    changes = models.JSONField(default=dict)
    provider_timestamp = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-captured_at",)

    def __str__(self):
        return f"Market snapshot {self.captured_at:%Y-%m-%d %H:%M:%S}"
