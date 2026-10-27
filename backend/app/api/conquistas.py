from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.conquistas import ConquistaService, SituacaoConquista
from app.domain.tempo import agora
from app.infra.repositorios import (
    RepositorioConquistaDjango,
    RepositorioRedeNeuralDjango,
)


def _servico() -> ConquistaService:
    # O relógio é lido a cada chamada, o que permite controlá-lo nos testes.
    return ConquistaService(
        RepositorioConquistaDjango(),
        RepositorioRedeNeuralDjango(),
        relogio=lambda: agora(),
    )


def _conquista_json(situacao: SituacaoConquista) -> dict:
    regra = situacao.regra
    return {
        "codigo": regra.codigo,
        "nome": regra.nome,
        "descricao": regra.descricao,
        "desbloqueada": situacao.desbloqueada,
        "desbloqueada_em": situacao.desbloqueada_em.isoformat()
        if situacao.desbloqueada_em
        else None,
        "progresso": situacao.progresso,
        "meta": regra.meta,
        "unidade": regra.unidade,
    }


class SequenciaSerializer(serializers.Serializer):
    atual = serializers.IntegerField(
        help_text=(
            "Dias seguidos com sessão concluída, até hoje ou ontem (horário de "
            "Brasília). Zera quando um dia inteiro passa sem sessão concluída."
        )
    )
    recorde = serializers.IntegerField(help_text="A maior sequência até hoje.")


class ConquistaSerializer(serializers.Serializer):
    codigo = serializers.CharField(help_text="Identificador estável da conquista.")
    nome = serializers.CharField()
    descricao = serializers.CharField(help_text="Como desbloquear.")
    desbloqueada = serializers.BooleanField()
    desbloqueada_em = serializers.DateTimeField(
        allow_null=True,
        help_text=(
            "Quando foi desbloqueada: o instante em que terminou a sessão que "
            "cumpriu a meta. null se ainda está bloqueada."
        ),
    )
    progresso = serializers.IntegerField(help_text="De 0 até a meta.")
    meta = serializers.IntegerField()
    unidade = serializers.CharField(
        help_text="Em que meta e progresso são contados: neurônios, minutos, dias..."
    )


class ConquistasRespostaSerializer(serializers.Serializer):
    sequencia = SequenciaSerializer()
    desbloqueadas = serializers.IntegerField()
    total = serializers.IntegerField()
    conquistas = ConquistaSerializer(many=True)


_EXEMPLO_CONQUISTAS = {
    "sequencia": {"atual": 3, "recorde": 5},
    "desbloqueadas": 1,
    "total": 5,
    "conquistas": [
        {
            "codigo": "primeiro_neuronio",
            "nome": "Primeiro neurônio",
            "descricao": "Conclua sua primeira sessão de foco.",
            "desbloqueada": True,
            "desbloqueada_em": "2026-10-20T14:25:00+00:00",
            "progresso": 1,
            "meta": 1,
            "unidade": "neurônios",
        },
        {
            "codigo": "dias_seguidos_7",
            "nome": "7 dias seguidos",
            "descricao": "Conclua pelo menos uma sessão por dia, 7 dias seguidos.",
            "desbloqueada": False,
            "desbloqueada_em": None,
            "progresso": 5,
            "meta": 7,
            "unidade": "dias",
        },
    ],
}


@extend_schema(
    summary="Conquistas e sequência de dias",
    description=(
        "Todas as conquistas, bloqueadas e desbloqueadas, com o progresso de cada "
        "uma, e a sequência de dias seguidos com sessão concluída. As conquistas são "
        "desbloqueadas ao fim de cada sessão concluída."
    ),
    responses={
        200: OpenApiResponse(
            ConquistasRespostaSerializer,
            examples=[
                OpenApiExample("Uma conquista desbloqueada", _EXEMPLO_CONQUISTAS)
            ],
        ),
        401: OpenApiResponse(description="Sem autenticação."),
    },
    tags=["Conquistas"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conquistas(request):
    # Numa transação: a consulta também desbloqueia o que já estiver cumprido.
    with transaction.atomic():
        painel = _servico().consultar(request.user.id)
    return Response(
        {
            "sequencia": {
                "atual": painel.sequencia.atual,
                "recorde": painel.sequencia.recorde,
            },
            "desbloqueadas": sum(c.desbloqueada for c in painel.conquistas),
            "total": len(painel.conquistas),
            "conquistas": [_conquista_json(c) for c in painel.conquistas],
        }
    )
