"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse
from django.urls import path
from django.views.static import serve

from prices.catalog_views import (
    product_image,
    products_list,
    studio_login,
    studio_logout,
    studio_product_create,
    studio_product_detail,
    studio_products,
    studio_session,
)
from prices.views import create_price, market_data, market_history, prices_list, scrape_proxy, update_price


MIME_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".json": "application/json",
}


def frontend_page(filename):
    def view(request):
        return FileResponse(
            open(Path(settings.BASE_DIR) / "frontend" / filename, "rb"),
            content_type="text/html; charset=utf-8",
        )

    return view


def frontend_static(subdir):
    def view(request, path):
        full_path = Path(settings.BASE_DIR) / "frontend" / subdir / path
        ext = full_path.suffix.lower()
        content_type = MIME_TYPES.get(ext, "application/octet-stream")
        return FileResponse(open(full_path, "rb"), content_type=content_type)

    return view


urlpatterns = [
    path("", frontend_page("index.html")),
    path("products/", frontend_page("products.html")),
    path("panel/", frontend_page("panel.html")),
    path("admin/", admin.site.urls),
    path("api/market/", market_data),
    path("api/market/history/", market_history),
    path("api/scrape-proxy/", scrape_proxy),
    path("api/prices/", prices_list),
    path("api/prices/create/", create_price),
    path("api/prices/<int:id>/", update_price),
    path("api/products/", products_list),
    path("api/products/images/<int:image_id>/", product_image, name="product-image"),
    path("api/studio/session/", studio_session),
    path("api/studio/login/", studio_login),
    path("api/studio/logout/", studio_logout),
    path("api/studio/products/", studio_products),
    path("api/studio/products/create/", studio_product_create),
    path("api/studio/products/<int:product_id>/", studio_product_detail),
    path("css/<path:path>", frontend_static("css")),
    path("js/<path:path>", frontend_static("js")),
    path("assets/<path:path>", frontend_static("assets")),
]
