from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.conquistas import ConquistaService
from app.application.estatisticas import EstatisticasService
from app.application.loja import LojaService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.estatisticas import (
    EstatisticasFoco,
    PeriodoEstatisticas,
    TempoDia,
    TempoMateria,
)
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.loja import Efeito
from app.domain.observadores import (
    AtualizadorRede,
    AvaliadorConquistas,
    CreditadorATP,
)
from app.domain.tempo import agora
from app.infra.repositorios import (
    RepositorioCarteiraDjango,
    RepositorioConquistaDjango,
    RepositorioMateriaDjango,
    RepositorioRedeNeuralDjango,
    RepositorioSessaoDjango,
)


def _servico() -> EstatisticasService:
    sessoes = RepositorioSessaoDjango()
    materias = RepositorioMateriaDjango()
    redes = RepositorioRedeNeuralDjango()

    publicador = PublicadorEventos()
    atualizador = AtualizadorRede(RedeNeuralService(redes))
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    publicador.inscrever(
        SessaoConcluida,
        AvaliadorConquistas(ConquistaService(RepositorioConquistaDjango(), redes)),
    )
    publicador.inscrever(
        SessaoConcluida, CreditadorATP(LojaService(RepositorioCarteiraDjango()))
    )

    sessao_service = SessaoService(
        sessoes, publicador, relogio=lambda: agora(), materias=materias
    )
    return EstatisticasService(
        sessoes,
        materias,
        sessao_service=sessao_service,
        relogio=lambda: agora(),
    )


def _dia_json(dia: TempoDia) -> dict:
    return {
        "data": dia.data.isoformat(),
        "minutos": dia.minutos,
        "por_materia": [
            {
                "materia_id": str(item.materia_id) if item.materia_id else None,
                "minutos": item.minutos,
            }
            for item in dia.por_materia
        ],
    }


def _materia_json(item: TempoMateria) -> dict:
    return {
        "materia_id": str(item.materia_id) if item.materia_id else None,
        "nome": item.nome,
        "cor": item.cor,
        "efeito": item.efeito.value if item.efeito else None,
        "minutos": item.minutos,
        "percentual": item.percentual,
    }


def _estatisticas_json(resumo: EstatisticasFoco) -> dict:
    return {
        "periodo": resumo.periodo.value,
        "inicio": resumo.inicio.isoformat(),
        "fim": resumo.fim.isoformat(),
        "tempo_total_minutos": resumo.tempo_total_minutos,
        "sessoes_concluidas": resumo.sessoes_concluidas,
        "sessoes_podadas": resumo.sessoes_podadas,
        "total_sessoes": resumo.total_sessoes,
        "taxa_sucesso": resumo.taxa_sucesso,
        "melhor_horario": resumo.melhor_horario,
        "por_dia": [_dia_json(d) for d in resumo.por_dia],
        "por_materia": [_materia_json(m) for m in resumo.por_materia],
    }


class FiltroEstatisticasSerializer(serializers.Serializer):
    periodo = serializers.ChoiceField(
        choices=[p.value for p in PeriodoEstatisticas],
        default=PeriodoEstatisticas.SEMANA.value,
        required=False,
    )


class TempoMateriaDiaSerializer(serializers.Serializer):
    materia_id = serializers.UUIDField(
        allow_null=True,
        help_text="Identificador da matéria; null para sessões sem matéria.",
    )
    minutos = serializers.IntegerField(
        help_text="Minutos focados nesta matéria no dia."
    )


class TempoDiaSerializer(serializers.Serializer):
    data = serializers.DateField(help_text="Dia do período no horário de Brasília.")
    minutos = serializers.IntegerField(
        help_text="Total de minutos de sessões concluídas no dia."
    )
    por_materia = TempoMateriaDiaSerializer(many=True)


class TempoMateriaSerializer(serializers.Serializer):
    materia_id = serializers.UUIDField(
        allow_null=True,
        help_text="Identificador da matéria; null para sessões sem matéria.",
    )
    nome = serializers.CharField(
        allow_null=True,
        help_text="Nome da matéria; null quando a sessão não teve matéria.",
    )
    cor = serializers.CharField(
        allow_null=True,
        help_text="Cor hexadecimal (#RRGGBB) da matéria; null sem matéria.",
    )
    efeito = serializers.ChoiceField(
        choices=[e.value for e in Efeito],
        allow_null=True,
        help_text="Animação da cor da matéria, quando comprada na loja.",
    )
    minutos = serializers.IntegerField(
        help_text="Minutos focados nesta matéria no período."
    )
    percentual = serializers.FloatField(
        help_text="Fração do tempo total focado no período (de 0.0 a 1.0)."
    )


class EstatisticasRespostaSerializer(serializers.Serializer):
    periodo = serializers.ChoiceField(choices=[p.value for p in PeriodoEstatisticas])
    inicio = serializers.DateField(help_text="Primeiro dia coberto pelo período.")
    fim = serializers.DateField(help_text="Último dia coberto pelo período (hoje).")
    tempo_total_minutos = serializers.IntegerField(
        help_text="Minutos somados das sessões concluídas no período."
    )
    sessoes_concluidas = serializers.IntegerField()
    sessoes_podadas = serializers.IntegerField()
    total_sessoes = serializers.IntegerField(
        help_text="Sessões encerradas no período (concluídas + podadas)."
    )
    taxa_sucesso = serializers.FloatField(
        help_text="Proporção concluídas / total_sessoes (0.0 quando não há sessões)."
    )
    melhor_horario = serializers.IntegerField(
        allow_null=True,
        help_text=(
            "Hora do dia (0 a 23, horário de Brasília) com mais minutos concluídos; "
            "null se não houver sessões concluídas no período."
        ),
    )
    por_dia = TempoDiaSerializer(many=True)
    por_materia = TempoMateriaSerializer(many=True)


_EXEMPLO_ESTATISTICAS = {
    "periodo": "semana",
    "inicio": "2026-10-14",
    "fim": "2026-10-20",
    "tempo_total_minutos": 75,
    "sessoes_concluidas": 2,
    "sessoes_podadas": 1,
    "total_sessoes": 3,
    "taxa_sucesso": 0.6667,
    "melhor_horario": 19,
    "por_dia": [
        {"data": "2026-10-14", "minutos": 0, "por_materia": []},
        {"data": "2026-10-15", "minutos": 0, "por_materia": []},
        {"data": "2026-10-16", "minutos": 0, "por_materia": []},
        {"data": "2026-10-17", "minutos": 0, "por_materia": []},
        {"data": "2026-10-18", "minutos": 0, "por_materia": []},
        {
            "data": "2026-10-19",
            "minutos": 25,
            "por_materia": [
                {
                    "materia_id": "8a7b6c5d-4e3f-4a1b-9c2d-1e0f9a8b7c6d",
                    "minutos": 25,
                }
            ],
        },
        {
            "data": "2026-10-20",
            "minutos": 50,
            "por_materia": [
                {
                    "materia_id": "8a7b6c5d-4e3f-4a1b-9c2d-1e0f9a8b7c6d",
                    "minutos": 50,
                }
            ],
        },
    ],
    "por_materia": [
        {
            "materia_id": "8a7b6c5d-4e3f-4a1b-9c2d-1e0f9a8b7c6d",
            "nome": "Cálculo",
            "cor": "#8B7BFF",
            "efeito": None,
            "minutos": 75,
            "percentual": 1.0,
        }
    ],
}


@extend_schema(
    summary="Estatísticas de foco",
    description=(
        "Resumo das sessões de foco do estudante no período escolhido (`dia`: hoje, "
        "`semana`: últimos 7 dias, `mes`: últimos 30 dias, no horário de Brasília): "
        "tempo total focado, distribuição por dia e por matéria, taxa de sucesso "
        "(`concluídas / total`) e horário do dia em que o estudante mais foca."
    ),
    parameters=[
        OpenApiParameter(
            "periodo",
            OpenApiTypes.STR,
            enum=[p.value for p in PeriodoEstatisticas],
            default=PeriodoEstatisticas.SEMANA.value,
            description=(
                "Janela de tempo: `dia` (hoje), `semana` (7 dias) ou `mes` (30 dias)."
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            EstatisticasRespostaSerializer,
            examples=[OpenApiExample("Resumo semanal", _EXEMPLO_ESTATISTICAS)],
        ),
        400: OpenApiResponse(description="Parâmetro `periodo` inválido."),
        401: OpenApiResponse(description="Sem autenticação."),
    },
    tags=["Estatísticas"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def estatisticas(request):
    filtros = FiltroEstatisticasSerializer(data=request.query_params.dict())
    filtros.is_valid(raise_exception=True)
    periodo = filtros.validated_data["periodo"]

    with transaction.atomic():
        resumo = _servico().consultar(request.user.id, periodo=periodo)
    return Response(_estatisticas_json(resumo))
