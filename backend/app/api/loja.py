from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.loja import LojaService, SituacaoItem, VitrineLoja
from app.domain.tempo import agora
from app.infra.repositorios import RepositorioCarteiraDjango


def _servico() -> LojaService:
    # O relógio é lido a cada chamada, o que permite controlá-lo nos testes.
    return LojaService(RepositorioCarteiraDjango(), relogio=lambda: agora())


def _item_json(situacao: SituacaoItem) -> dict:
    item = situacao.item
    return {
        "codigo": item.codigo,
        "nome": item.tipo.nome,
        "forma": item.forma,
        "cor": item.tipo.cor,
        "preco": item.preco,
        "duracao_minima": item.tipo.duracao_minima,
        "duracao_maxima": item.tipo.duracao_maxima,
        "desbloqueado": situacao.desbloqueado,
        "em_uso": situacao.em_uso,
    }


def _vitrine_json(vitrine: VitrineLoja) -> dict:
    return {"saldo": vitrine.saldo, "tipos": [_item_json(i) for i in vitrine.itens]}


class TipoLojaSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Identificador do tipo, usado na compra.")
    nome = serializers.CharField()
    forma = serializers.ChoiceField(
        choices=["granular", "piramidal", "purkinje"],
        help_text="O desenho do neurônio, que continua ligado à duração da sessão.",
    )
    cor = serializers.CharField(help_text="Cor do neurônio (hexadecimal).")
    preco = serializers.IntegerField(help_text="Em ATP. 0: tipo original, de todos.")
    duracao_minima = serializers.IntegerField(help_text="Em minutos.")
    duracao_maxima = serializers.IntegerField(
        allow_null=True, help_text="Em minutos; null: sem limite."
    )
    desbloqueado = serializers.BooleanField()
    em_uso = serializers.BooleanField(
        help_text="Se as próximas sessões desta faixa criam neurônios deste tipo."
    )


class LojaRespostaSerializer(serializers.Serializer):
    saldo = serializers.IntegerField(help_text="ATP disponível.")
    tipos = TipoLojaSerializer(many=True)


_EXEMPLO_LOJA = {
    "saldo": 120,
    "tipos": [
        {
            "codigo": "piramidal",
            "nome": "Piramidal",
            "forma": "piramidal",
            "cor": "#8B7BFF",
            "preco": 0,
            "duracao_minima": 25,
            "duracao_maxima": 59,
            "desbloqueado": True,
            "em_uso": False,
        },
        {
            "codigo": "piramidal_rosa",
            "nome": "Piramidal Rosa",
            "forma": "piramidal",
            "cor": "#FF6FB5",
            "preco": 250,
            "duracao_minima": 25,
            "duracao_maxima": 59,
            "desbloqueado": True,
            "em_uso": True,
        },
    ],
}

_RESPOSTA_LOJA = OpenApiResponse(
    LojaRespostaSerializer,
    examples=[OpenApiExample("Com uma variação comprada", _EXEMPLO_LOJA)],
)
_404 = OpenApiResponse(description="Tipo que não está à venda.")


@extend_schema(
    summary="Loja de ATP",
    description=(
        "O saldo de ATP e os tipos de neurônio: os originais (preço 0) e as "
        "variações de cor que podem ser compradas. Cada sessão concluída rende 1 "
        "ATP por minuto."
    ),
    responses={200: _RESPOSTA_LOJA, 401: OpenApiResponse(description="Sem login.")},
    tags=["Loja"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def loja(request):
    return Response(_vitrine_json(_servico().consultar(request.user.id)))


@extend_schema(
    summary="Comprar tipo de neurônio",
    description=(
        "Desconta o preço do saldo, desbloqueia o tipo e já passa a usá-lo nas "
        "próximas sessões da faixa de duração dele. Devolve a loja atualizada."
    ),
    request=None,
    responses={
        200: _RESPOSTA_LOJA,
        404: _404,
        409: OpenApiResponse(description="Saldo insuficiente ou tipo já comprado."),
    },
    tags=["Loja"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comprar(request, codigo):
    with transaction.atomic():
        vitrine = _servico().comprar(request.user.id, codigo)
    return Response(_vitrine_json(vitrine))


@extend_schema(
    summary="Usar tipo de neurônio",
    description=(
        "Escolhe o tipo das próximas sessões da faixa de duração dele. Usar um tipo "
        "original volta ao padrão. Devolve a loja atualizada."
    ),
    request=None,
    responses={
        200: _RESPOSTA_LOJA,
        404: _404,
        409: OpenApiResponse(description="Tipo ainda não comprado."),
    },
    tags=["Loja"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def usar(request, codigo):
    with transaction.atomic():
        vitrine = _servico().usar(request.user.id, codigo)
    return Response(_vitrine_json(vitrine))
