from django.db import models
from django.utils import timezone


class Product(models.Model):
    class Category(models.TextChoices):
        RING = "ring", "انگشتر"
        NECKLACE = "necklace", "گردنبند"
        BRACELET = "bracelet", "دستبند"
        EARRING = "earring", "گوشواره"
        OTHER = "other", "سایر"

    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=40, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2)
    making_charge = models.DecimalField(max_digits=15, decimal_places=0)
    profit = models.DecimalField(max_digits=5, decimal_places=2, default=7)
    note = models.CharField(max_length=180, blank=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_featured", "-created_at")

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    file = models.BinaryField(blank=True, null=True)
    content_type = models.CharField(max_length=40, default="image/jpeg")
    external_url = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"Image {self.pk} for {self.product_id}"


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
