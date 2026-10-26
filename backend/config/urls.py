from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.api import materias, rede, sessoes
from app.api.auth import cadastro, login, me, renovar
from app.api.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("auth/cadastro", cadastro),
    path("auth/login", login),
    path("auth/renovar", renovar),
    path("me", me),
    path("materias", materias.materias),
    path("materias/<uuid:materia_id>", materias.detalhe_materia),
    path("rede", rede.rede),
    path("sessoes", sessoes.sessoes),
    path("sessoes/ativa", sessoes.ativa),
    path("sessoes/<uuid:sessao_id>/interrupcoes", sessoes.interrupcoes),
    path("sessoes/<uuid:sessao_id>/concluir", sessoes.concluir),
    path("sessoes/<uuid:sessao_id>/desistir", sessoes.desistir),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
