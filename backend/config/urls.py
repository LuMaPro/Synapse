from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.api.views import health

urlpatterns = [
    path("health", health),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
