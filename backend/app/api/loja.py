from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.loja import LojaService, SituacaoCor, VitrineLoja
from app.domain.loja import Efeito
from app.domain.tempo import agora
from app.infra.repositorios import RepositorioCarteiraDjango


def _servico() -> LojaService:
    # O relógio é lido a cada chamada, o que permite controlá-lo nos testes.
    return LojaService(RepositorioCarteiraDjango(), relogio=lambda: agora())


def _cor_json(situacao: SituacaoCor) -> dict:
    cor = situacao.cor
    return {
        "codigo": cor.codigo,
        "nome": cor.nome,
        "cor": cor.hex,
        "efeito": cor.efeito.value if cor.efeito else None,
        "preco": cor.preco,
        "desbloqueada": situacao.desbloqueada,
    }


def _vitrine_json(vitrine: VitrineLoja) -> dict:
    return {"saldo": vitrine.saldo, "cores": [_cor_json(c) for c in vitrine.cores]}


class CorLojaSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Identificador da cor, usado na compra.")
    nome = serializers.CharField()
    cor = serializers.CharField(
        help_text="Hexadecimal #RRGGBB: vai na matéria; é o que se vê sem animação."
    )
    efeito = serializers.ChoiceField(
        choices=[e.value for e in Efeito],
        allow_null=True,
        help_text="Animação da cor; null nas cores lisas.",
    )
    preco = serializers.IntegerField(help_text="Em ATP. 0: cor da paleta, de todos.")
    desbloqueada = serializers.BooleanField(
        help_text="Se o estudante pode dar esta cor a uma matéria."
    )


class LojaRespostaSerializer(serializers.Serializer):
    saldo = serializers.IntegerField(help_text="ATP disponível.")
    cores = CorLojaSerializer(many=True)


_EXEMPLO_LOJA = {
    "saldo": 120,
    "cores": [
        {
            "codigo": "violeta",
            "nome": "Violeta",
            "cor": "#8B7BFF",
            "efeito": None,
            "preco": 0,
            "desbloqueada": True,
        },
        {
            "codigo": "magenta_neon",
            "nome": "Magenta neon",
            "cor": "#FF3DF0",
            "efeito": None,
            "preco": 250,
            "desbloqueada": True,
        },
        {
            "codigo": "arco_iris",
            "nome": "Arco-íris",
            "cor": "#FF7AD9",
            "efeito": "arco_iris",
            "preco": 1200,
            "desbloqueada": False,
        },
    ],
}

_RESPOSTA_LOJA = OpenApiResponse(
    LojaRespostaSerializer,
    examples=[OpenApiExample("Com uma cor comprada", _EXEMPLO_LOJA)],
)


@extend_schema(
    summary="Loja de ATP",
    description=(
        "O saldo de ATP e todas as cores das matérias: as 8 da paleta (preço 0) e as "
        "exclusivas da loja, algumas com efeitos animados. Cada sessão concluída "
        "rende 1 ATP por minuto."
    ),
    responses={200: _RESPOSTA_LOJA, 401: OpenApiResponse(description="Sem login.")},
    tags=["Loja"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def loja(request):
    return Response(_vitrine_json(_servico().consultar(request.user.id)))


@extend_schema(
    summary="Comprar cor",
    description=(
        "Desconta o preço do saldo e desbloqueia a cor para as matérias do "
        "estudante. Devolve a loja atualizada."
    ),
    request=None,
    responses={
        200: _RESPOSTA_LOJA,
        404: OpenApiResponse(description="Cor que não está à venda."),
        409: OpenApiResponse(description="Saldo insuficiente ou cor já comprada."),
    },
    tags=["Loja"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comprar(request, codigo):
    with transaction.atomic():
        vitrine = _servico().comprar(request.user.id, codigo)
    return Response(_vitrine_json(vitrine))
