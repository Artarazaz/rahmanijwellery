from io import BytesIO

from django.urls import reverse

from .models import Product, ProductImage

MAX_IMAGES_PER_PRODUCT = 8
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def category_payload():
    counts = {
        choice.value: Product.objects.filter(is_published=True, category=choice.value).count()
        for choice in Product.Category
    }
    return [
        {"id": choice.value, "label": choice.label, "count": counts[choice.value]}
        for choice in Product.Category
    ]


def image_url(image):
    if image.external_url:
        return image.external_url
    return reverse("product-image", args=[image.pk])


def serialize_product(product):
    images = list(product.images.all())
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": product.category,
        "category_label": product.get_category_display(),
        "weight": float(product.weight),
        "making_charge": float(product.making_charge),
        "profit": float(product.profit),
        "note": product.note,
        "is_published": product.is_published,
        "is_featured": product.is_featured,
        "images": [{"id": image.id, "url": image_url(image)} for image in images],
    }


def compress_upload(uploaded_file):
    data = uploaded_file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("حجم هر عکس باید کمتر از ۸ مگابایت باشد.")
    try:
        from PIL import Image
    except ImportError:
        content_type = uploaded_file.content_type or "application/octet-stream"
        return data, content_type

    image = Image.open(BytesIO(data))
    image = image.convert("RGB")
    image.thumbnail((1400, 1400))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    return buffer.getvalue(), "image/jpeg"


def save_uploaded_images(product, files):
    current_count = product.images.count()
    uploads = files[: MAX_IMAGES_PER_PRODUCT - current_count]
    created = []
    for index, uploaded in enumerate(uploads):
        payload, content_type = compress_upload(uploaded)
        created.append(
            ProductImage.objects.create(
                product=product,
                file=payload,
                content_type=content_type,
                sort_order=current_count + index,
            )
        )
    return created


def parse_decimal(value, field_name, allow_zero=False):
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} نامعتبر است.")
    if number < 0 or (not allow_zero and number == 0):
        raise ValueError(f"{field_name} باید بزرگ‌تر از صفر باشد.")
    return number
