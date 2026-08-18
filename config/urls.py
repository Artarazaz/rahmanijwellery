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

from prices.views import create_price, market_data, market_history, prices_list, update_price


def frontend_index(request):
    return FileResponse(
        open(Path(settings.BASE_DIR) / "frontend" / "index.html", "rb"),
        content_type="text/html; charset=utf-8",
    )


urlpatterns = [
    path("", frontend_index),
    path("admin/", admin.site.urls),
    path("api/market/", market_data),
    path("api/market/history/", market_history),
    path("api/prices/", prices_list),
    path("api/prices/create/", create_price),
    path("api/prices/<int:id>/", update_price),
    path("css/<path:path>", serve, {"document_root": Path(settings.BASE_DIR) / "frontend" / "css"}),
    path("js/<path:path>", serve, {"document_root": Path(settings.BASE_DIR) / "frontend" / "js"}),
    path("assets/<path:path>", serve, {"document_root": Path(settings.BASE_DIR) / "frontend" / "assets"}),
]
