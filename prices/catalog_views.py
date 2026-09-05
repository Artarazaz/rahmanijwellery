import json

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .catalog import (
    category_payload,
    parse_decimal,
    save_uploaded_images,
    serialize_product,
)
from .models import Product, ProductImage


def _json_body(request):
    if not request.body:
        return {}
    return json.loads(request.body)


def _staff_required(request):
    if request.user.is_authenticated and request.user.is_staff:
        return None
    return JsonResponse({"error": "ورود ادمین لازم است.", "code": "unauthorized"}, status=401)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "on", "yes"}


def _product_from_request(data, product=None):
    name = str(data.get("name") or "").strip()
    sku = str(data.get("sku") or "").strip()
    category = str(data.get("category") or "").strip()
    note = str(data.get("note") or "").strip()
    if not name:
        raise ValueError("نام محصول لازم است.")
    if category not in Product.Category.values:
        raise ValueError("دسته‌بندی نامعتبر است.")
    weight = parse_decimal(data.get("weight"), "وزن")
    making_charge = parse_decimal(data.get("making_charge"), "اجرت", allow_zero=True)
    profit = parse_decimal(data.get("profit") or 7, "سود", allow_zero=True)
    is_published = _as_bool(data.get("is_published"), True if product is None else product.is_published)
    is_featured = _as_bool(data.get("is_featured"), False if product is None else product.is_featured)
    fields = {
        "name": name,
        "sku": sku,
        "category": category,
        "weight": weight,
        "making_charge": making_charge,
        "profit": profit,
        "note": note,
        "is_published": is_published,
        "is_featured": is_featured,
    }
    if product is None:
        return Product.objects.create(**fields)
    for key, value in fields.items():
        setattr(product, key, value)
    product.save()
    return product


def _files_from_request(request):
    files = request.FILES.getlist("images") or request.FILES.getlist("images[]")
    if not files:
        uploaded = request.FILES.get("image")
        files = [uploaded] if uploaded else []
    return files


@require_GET
def products_list(request):
    category = request.GET.get("category", "").strip()
    featured = request.GET.get("featured")
    queryset = Product.objects.filter(is_published=True).prefetch_related("images")
    if category in Product.Category.values:
        queryset = queryset.filter(category=category)
    if str(featured).lower() in {"1", "true"}:
        queryset = queryset.filter(is_featured=True)
    limit = request.GET.get("limit")
    products = list(queryset)
    if limit:
        try:
            products = products[: max(1, int(limit))]
        except (TypeError, ValueError):
            pass
    return JsonResponse({
        "categories": category_payload(),
        "products": [serialize_product(product) for product in products],
    })


@require_GET
def product_image(request, image_id):
    image = get_object_or_404(ProductImage, pk=image_id)
    if image.external_url and not image.file:
        from django.shortcuts import redirect
        return redirect(image.external_url)
    if not image.file:
        return JsonResponse({"error": "تصویر پیدا نشد."}, status=404)
    response = HttpResponse(bytes(image.file), content_type=image.content_type or "image/jpeg")
    response["Cache-Control"] = "public, max-age=86400"
    return response


@ensure_csrf_cookie
@require_GET
def studio_session(request):
    authenticated = request.user.is_authenticated and request.user.is_staff
    return JsonResponse({
        "authenticated": authenticated,
        "username": request.user.get_username() if authenticated else "",
    })


@require_POST
def studio_login(request):
    try:
        body = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "درخواست نامعتبر است."}, status=400)
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff or not user.is_active:
        return JsonResponse({"error": "نام کاربری یا رمز عبور نادرست است."}, status=400)
    login(request, user)
    return JsonResponse({"authenticated": True, "username": user.get_username()})


@require_POST
def studio_logout(request):
    logout(request)
    return JsonResponse({"authenticated": False})


@require_GET
def studio_products(request):
    unauthorized = _staff_required(request)
    if unauthorized:
        return unauthorized
    products = Product.objects.all().prefetch_related("images")
    return JsonResponse({
        "categories": [{"id": choice.value, "label": choice.label} for choice in Product.Category],
        "products": [serialize_product(product) for product in products],
    })


@require_http_methods(["POST"])
def studio_product_create(request):
    unauthorized = _staff_required(request)
    if unauthorized:
        return unauthorized
    data = request.POST if request.POST else _json_body(request)
    try:
        product = _product_from_request(data)
        save_uploaded_images(product, _files_from_request(request))
    except (ValueError, json.JSONDecodeError, KeyError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(serialize_product(product), status=201)


@require_http_methods(["POST", "PATCH", "DELETE"])
def studio_product_detail(request, product_id):
    unauthorized = _staff_required(request)
    if unauthorized:
        return unauthorized
    product = get_object_or_404(Product.objects.prefetch_related("images"), pk=product_id)
    if request.method == "DELETE":
        product.delete()
        return JsonResponse({"ok": True})
    data = request.POST if request.method == "POST" else _json_body(request)
    try:
        product = _product_from_request(data, product)
        keep_ids = data.get("keep_image_ids")
        if keep_ids is not None:
            if isinstance(keep_ids, str):
                keep_ids = [item for item in keep_ids.split(",") if item.strip()]
            keep_ids = {int(item) for item in keep_ids}
            product.images.exclude(id__in=keep_ids).delete()
        save_uploaded_images(product, _files_from_request(request))
    except (ValueError, json.JSONDecodeError, KeyError, TypeError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    product = Product.objects.prefetch_related("images").get(pk=product.pk)
    return JsonResponse(serialize_product(product))
