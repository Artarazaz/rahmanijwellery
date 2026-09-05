from django.contrib import admin

from .models import GoldPrice, MarketSnapshot, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "weight", "making_charge", "is_published", "is_featured")
    list_filter = ("category", "is_published", "is_featured")
    search_fields = ("name", "sku")
    inlines = [ProductImageInline]


admin.site.register(GoldPrice)
admin.site.register(MarketSnapshot)
