from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.api.auth import cadastro
from app.api.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("auth/cadastro", cadastro),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
