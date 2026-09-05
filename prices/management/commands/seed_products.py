from django.core.management.base import BaseCommand
from prices.models import Product


PRODUCTS = [
    # Rings (انگشتر)
    {"name": "انگشتر مهتاب", "sku": "R-001", "category": "ring", "weight": 4.20, "making_charge": 3500000, "profit": 7, "note": "انگشتر طلای ۱۸ عیار با نگین ماه‌تاب", "is_featured": True},
    {"name": "انگشتر ستاره سحر", "sku": "R-002", "category": "ring", "weight": 3.80, "making_charge": 3200000, "profit": 7, "note": "انگشتر ظریف با طرح ستاره"},
    {"name": "انگشتر کلاسیک", "sku": "R-003", "category": "ring", "weight": 5.10, "making_charge": 4000000, "profit": 7, "note": "انگشتر ساده و کلاسیک طلای ۱۸ عیار"},

    # Earrings (گوشواره)
    {"name": "گوشواره ستاره سحر", "sku": "E-001", "category": "earring", "weight": 2.40, "making_charge": 2800000, "profit": 7, "note": "گوشواره طلای رزگلد با طرح ستاره", "is_featured": True},
    {"name": "گوشواره قطره نور", "sku": "E-002", "category": "earring", "weight": 1.90, "making_charge": 2400000, "profit": 7, "note": "گوشواره ظریف با نگین قطره‌ای"},
    {"name": "گوشواره حلقه‌ای", "sku": "E-003", "category": "earring", "weight": 2.80, "making_charge": 3000000, "profit": 7, "note": "گوشواره حلقه‌ای طلای ۱۸ عیار"},

    # Necklaces (گردنبند)
    {"name": "گردنبند دو ردیفه", "sku": "N-001", "category": "necklace", "weight": 8.50, "making_charge": 6500000, "profit": 7, "note": "گردنبند دو ردیفه طلای زرد و سفید", "is_featured": True},
    {"name": "گردنبند پرنسس", "sku": "N-002", "category": "necklace", "weight": 6.20, "making_charge": 5200000, "profit": 7, "note": "گردنبند ظریف با نگین درشت"},
    {"name": "گردنبند زنجیره‌ای", "sku": "N-003", "category": "necklace", "weight": 7.80, "making_charge": 5800000, "profit": 7, "note": "گردنبند زنجیره‌ای طلای ۱۸ عیار"},

    # Bracelets (دستبند)
    {"name": "دستبند رشته زرین", "sku": "B-001", "category": "bracelet", "weight": 12.00, "making_charge": 7500000, "profit": 7, "note": "دستبند طلای ۱۸ عیار با طرح رشته‌ای", "is_featured": True},
    {"name": "دستبند خط نور", "sku": "B-002", "category": "bracelet", "weight": 9.50, "making_charge": 6000000, "profit": 7, "note": "دستبند ظریف با خطوط نورانی"},
    {"name": "دستبند کلاسیک", "sku": "B-003", "category": "bracelet", "weight": 10.80, "making_charge": 6800000, "profit": 7, "note": "دستبند کلاسیک طلای ۱۸ عیار"},
]


class Command(BaseCommand):
    help = "ایجاد محصولات نمونه برای هر دسته‌بندی"

    def handle(self, *args, **options):
        created_count = 0
        for data in PRODUCTS:
            product, created = Product.objects.get_or_create(
                sku=data["sku"],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f" Created: {product.name} ({product.category})"))
            else:
                self.stdout.write(f"  Exists: {product.name}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created_count} products created."))
