import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .models import GoldPrice
from .services import ProviderError, get_history, get_market_data


@require_GET
def market_data(request):
    """GET /api/market/ — latest persisted prices, deltas and chart periods."""
    try:
        payload = get_market_data()
    except ProviderError as error:
        response = JsonResponse({"error": str(error), "code": "market_provider_unavailable"}, status=503)
        response["Cache-Control"] = "no-store, max-age=0"
        return response
    response = JsonResponse(payload)
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@require_GET
def market_history(request):
    """GET /api/market/history/?period=hourly&limit=7 — chart points from snapshots."""
    period = request.GET.get("period", "hourly")
    try:
        limit = int(request.GET.get("limit", "7"))
        return JsonResponse({"period": period, **get_history(period, limit)})
    except (ValueError, TypeError) as error:
        return JsonResponse({"error": str(error), "code": "invalid_history_request"}, status=400)


@require_GET
def prices_list(request):
    """Legacy gold-price endpoint kept for existing admin integrations."""
    karat = request.GET.get("karat")
    prices = GoldPrice.objects.filter(karat=karat) if karat else GoldPrice.objects.all()
    data = [
        {
            "id": price.id,
            "karat": price.karat,
            "price": str(price.price),
            "timestamp": price.timestamp.isoformat(),
        }
        for price in prices
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def create_price(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        body = json.loads(request.body)
        gold_price = GoldPrice.objects.create(karat=body["karat"], price=body["price"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return JsonResponse({"error": f"Invalid request: {error}"}, status=400)
    return JsonResponse({"id": gold_price.id, "karat": gold_price.karat, "price": str(gold_price.price)})


@csrf_exempt
def update_price(request, id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Only PATCH allowed"}, status=405)
    try:
        price = GoldPrice.objects.get(id=id)
    except GoldPrice.DoesNotExist:
        return JsonResponse({"error": "Price not found"}, status=404)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as error:
        return JsonResponse({"error": f"Invalid JSON: {error}"}, status=400)
    if "price" in body:
        price.price = body["price"]
        price.save(update_fields=["price"])
    return JsonResponse({"message": "Price updated", "id": price.id, "price": str(price.price)})
