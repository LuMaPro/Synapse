from uuid import UUID

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

from app.api.periodo import DESCRICAO_PERIODO, FiltroPeriodoSerializer
from app.application.rede import RedeNeuralService
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sinapse import Sinapse
from app.infra.repositorios import (
    RepositorioMateriaDjango,
    RepositorioRedeNeuralDjango,
)


def _neuronio_json(
    neuronio: Neuronio, cores_materias: dict[UUID, str] | None = None
) -> dict:
    # Vivo com matéria: a cor da matéria (#28). Senão, a do tipo, e o podado é cinza.
    cor_materia = (
        (cores_materias or {}).get(neuronio.materia_id)
        if neuronio.vivo and neuronio.materia_id
        else None
    )
    return {
        "id": str(neuronio.id),
        "tipo": neuronio.tipo.codigo,
        "materia_id": str(neuronio.materia_id) if neuronio.materia_id else None,
        "cor": cor_materia or neuronio.cor,
        "criado_em": neuronio.criado_em.isoformat(),
        "duracao_minutos": neuronio.duracao.minutos,
        "vivo": neuronio.vivo,
    }


def _sinapse_json(sinapse: Sinapse) -> dict:
    return {
        "id": str(sinapse.id),
        "origem_id": str(sinapse.origem_id),
        "destino_id": str(sinapse.destino_id),
        "peso": sinapse.peso,
    }


class FiltrosRedeSerializer(FiltroPeriodoSerializer):
    materia = serializers.UUIDField(required=False)


class NeuronioRedeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tipo = serializers.ChoiceField(
        choices=["granular", "piramidal", "purkinje"],
        help_text="Pela duração: até 24 min granular, 25 a 59 piramidal, 60+ Purkinje.",
    )
    materia_id = serializers.UUIDField(
        allow_null=True, help_text="Matéria da sessão (#27); null se não tiver."
    )
    cor = serializers.CharField(
        help_text="Cor do tipo (hexadecimal); neurônio podado é sempre #4A4F6E."
    )
    criado_em = serializers.DateTimeField(help_text="Quando a sessão terminou.")
    duracao_minutos = serializers.IntegerField()
    vivo = serializers.BooleanField(
        help_text="false: neurônio podado (sessão interrompida), sem sinapses."
    )


class SinapseRedeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    origem_id = serializers.UUIDField(help_text="Neurônio mais antigo.")
    destino_id = serializers.UUIDField(help_text="Neurônio mais novo.")
    peso = serializers.IntegerField(
        help_text="1 a 5. Cresce a cada volta à mesma matéria."
    )


class RedeRespostaSerializer(serializers.Serializer):
    neuronios = NeuronioRedeSerializer(many=True)
    sinapses = SinapseRedeSerializer(many=True)


_EXEMPLO_REDE = {
    "neuronios": [
        {
            "id": "8f1c3e2a-6b7d-4c1e-9a2b-3d4e5f6a7b8c",
            "tipo": "piramidal",
            "materia_id": None,
            "cor": "#8B7BFF",
            "criado_em": "2026-10-20T14:25:00+00:00",
            "duracao_minutos": 25,
            "vivo": True,
        },
        {
            "id": "1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d",
            "tipo": "granular",
            "materia_id": None,
            "cor": "#4A4F6E",
            "criado_em": "2026-10-20T15:03:00+00:00",
            "duracao_minutos": 15,
            "vivo": False,
        },
        {
            "id": "9e8d7c6b-5a4f-4e3d-2c1b-0a9f8e7d6c5b",
            "tipo": "purkinje",
            "materia_id": None,
            "cor": "#FFC857",
            "criado_em": "2026-10-20T17:00:00+00:00",
            "duracao_minutos": 60,
            "vivo": True,
        },
    ],
    "sinapses": [
        {
            "id": "4b5c6d7e-8f9a-4b1c-9d2e-3f4a5b6c7d8e",
            "origem_id": "8f1c3e2a-6b7d-4c1e-9a2b-3d4e5f6a7b8c",
            "destino_id": "9e8d7c6b-5a4f-4e3d-2c1b-0a9f8e7d6c5b",
            "peso": 1,
        }
    ],
}


def _servico() -> RedeNeuralService:
    return RedeNeuralService(RepositorioRedeNeuralDjango())


@extend_schema(
    summary="Rede neural do estudante",
    description=(
        "A rede no formato de grafo: os neurônios (um por sessão terminada) e as "
        "sinapses entre eles. Os filtros escolhem os neurônios; só vêm as sinapses "
        "que ligam dois neurônios escolhidos."
    ),
    parameters=[
        OpenApiParameter(
            "de",
            OpenApiTypes.STR,
            description=f"Início do período (inclusive). {DESCRICAO_PERIODO}",
            examples=[
                OpenApiExample("Data", value="2026-10-01"),
                OpenApiExample("Data e hora", value="2026-10-01T00:00:00-03:00"),
            ],
        ),
        OpenApiParameter(
            "ate",
            OpenApiTypes.STR,
            description=f"Fim do período (inclusive). {DESCRICAO_PERIODO}",
            examples=[OpenApiExample("Data", value="2026-10-31")],
        ),
        OpenApiParameter(
            "materia",
            OpenApiTypes.UUID,
            description="Só os neurônios desta matéria (#27).",
        ),
    ],
    responses={
        200: OpenApiResponse(
            RedeRespostaSerializer,
            examples=[OpenApiExample("Rede com três neurônios", value=_EXEMPLO_REDE)],
        ),
        400: OpenApiResponse(description="Filtro inválido."),
        401: OpenApiResponse(description="Sem autenticação."),
    },
    tags=["Rede neural"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rede(request):
    filtros = FiltrosRedeSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    dados = filtros.validated_data
    recorte = _servico().consultar(
        request.user.id,
        de=dados.get("de"),
        ate=dados.get("ate"),
        materia_id=dados.get("materia"),
    )
    cores_materias = {
        m.id: m.cor
        for m in RepositorioMateriaDjango().listar_por_usuario(request.user.id)
    }
    return Response(
        {
            "neuronios": [_neuronio_json(n, cores_materias) for n in recorte.neuronios],
            "sinapses": [_sinapse_json(s) for s in recorte.sinapses],
        }
    )
