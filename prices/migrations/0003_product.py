from django.db import migrations, models
import django.db.models.deletion


def seed_sample_products(apps, schema_editor):
    Product = apps.get_model("prices", "Product")
    ProductImage = apps.get_model("prices", "ProductImage")
    samples = [
        {
            "name": "حلقه کلاسیک",
            "sku": "R-018",
            "category": "ring",
            "weight": "5.20",
            "making_charge": "450000",
            "note": "فرمی بی‌زمان برای هر روز",
            "is_featured": True,
            "image": "assets/gold_ring_1786118338142.png",
        },
        {
            "name": "گردنبند پرنسس",
            "sku": "R-024",
            "category": "necklace",
            "weight": "8.50",
            "making_charge": "600000",
            "note": "یک نقطه نور، نزدیک قلب",
            "is_featured": True,
            "image": "assets/gold_necklace_1786118350826.png",
        },
        {
            "name": "دستبند خط نور",
            "sku": "R-031",
            "category": "bracelet",
            "weight": "12.00",
            "making_charge": "800000",
            "note": "تعادل ظریف میان قدرت و سادگی",
            "is_featured": True,
            "image": "assets/gold_bracelet_1786118365180.png",
        },
    ]
    for sample in samples:
        image_url = sample.pop("image")
        product = Product.objects.create(**sample)
        ProductImage.objects.create(product=product, external_url=image_url, sort_order=0)


def unseed_sample_products(apps, schema_editor):
    Product = apps.get_model("prices", "Product")
    Product.objects.filter(sku__in=["R-018", "R-024", "R-031"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("prices", "0002_marketsnapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("sku", models.CharField(blank=True, max_length=40)),
                ("category", models.CharField(choices=[("ring", "انگشتر"), ("necklace", "گردنبند"), ("bracelet", "دستبند"), ("earring", "گوشواره"), ("other", "سایر")], db_index=True, max_length=20)),
                ("weight", models.DecimalField(decimal_places=2, max_digits=8)),
                ("making_charge", models.DecimalField(decimal_places=0, max_digits=15)),
                ("profit", models.DecimalField(decimal_places=2, default=7, max_digits=5)),
                ("note", models.CharField(blank=True, max_length=180)),
                ("is_published", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-is_featured", "-created_at")},
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.BinaryField(blank=True, null=True)),
                ("content_type", models.CharField(default="image/jpeg", max_length=40)),
                ("external_url", models.CharField(blank=True, max_length=255)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="prices.product")),
            ],
            options={"ordering": ("sort_order", "id")},
        ),
        migrations.RunPython(seed_sample_products, unseed_sample_products),
    ]
