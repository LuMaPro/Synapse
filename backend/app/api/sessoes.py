from collections.abc import Callable
from typing import Any

from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.excecoes import (
    DuracaoInvalida,
    ErroDominio,
    HorarioInvalido,
    PoliticaInvalida,
    SessaoAtivaExistente,
    SessaoNaoEncontrada,
    TransicaoInvalida,
)
from app.domain.tempo import agora
from app.infra.repositorios import (
    RepositorioRedeNeuralDjango,
    RepositorioSessaoDjango,
)

# Provisório até o tratamento de erros nas bordas da API (#12): status e código de
# cada erro de domínio, aplicados num único lugar (`_responder`).
ERROS_SESSAO: dict[type[ErroDominio], tuple[int, str]] = {
    SessaoNaoEncontrada: (status.HTTP_404_NOT_FOUND, "sessao_nao_encontrada"),
    SessaoAtivaExistente: (status.HTTP_409_CONFLICT, "sessao_ativa_existente"),
    TransicaoInvalida: (status.HTTP_409_CONFLICT, "transicao_invalida"),
    DuracaoInvalida: (status.HTTP_400_BAD_REQUEST, "duracao_invalida"),
    HorarioInvalido: (status.HTTP_400_BAD_REQUEST, "horario_invalido"),
    PoliticaInvalida: (status.HTTP_400_BAD_REQUEST, "modo_invalido"),
}


def _servico() -> SessaoService:
    # O relógio é lido a cada chamada, o que permite controlá-lo nos testes.
    return SessaoService(
        RepositorioSessaoDjango(),
        RedeNeuralService(RepositorioRedeNeuralDjango()),
        relogio=lambda: agora(),
    )


def _responder(acao: Callable[[], Any], status_sucesso: int) -> Response:
    """Executa o caso de uso numa transação e traduz erros de domínio para HTTP.

    O erro é tratado dentro da transação de propósito: os casos de uso só lançam
    erro de domínio antes das gravações principais, e o que já foi gravado (ex.: a
    poda de uma sessão abandonada, feita ao carregá-la) precisa ser mantido.
    """
    with transaction.atomic():
        try:
            corpo = acao()
        except ErroDominio as erro:
            codigo_http, codigo = ERROS_SESSAO.get(
                type(erro), (status.HTTP_400_BAD_REQUEST, "dados_invalidos")
            )
            return Response({"erro": codigo, "mensagem": str(erro)}, status=codigo_http)
    if corpo is None:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(corpo, status=status_sucesso)


def _erro_de_validacao(serializer: serializers.Serializer) -> Response:
    campo, erros = next(iter(serializer.errors.items()))
    return Response(
        {"erro": f"{campo}_invalido", "mensagem": str(erros[0])},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _sessao_json(sessao: SessaoFoco) -> dict:
    return {
        "id": str(sessao.id),
        "duracao_minutos": sessao.duracao.minutos,
        "modo": sessao.politica.codigo,
        "estado": sessao.codigo_estado,
        "inicio": sessao.inicio.isoformat(),
        "fim_previsto": sessao.fim_previsto.isoformat(),
        "encerrada_em": sessao.encerrada_em.isoformat()
        if sessao.encerrada_em
        else None,
        # Calculado com o relógio do servidor, não com o do cliente.
        "restante_segundos": sessao.restante_em(agora()).total_seconds(),
        "tempo_fora_segundos": sessao.tempo_fora.total_seconds(),
    }


def _neuronio_json(neuronio: Neuronio) -> dict:
    return {
        "id": str(neuronio.id),
        "sessao_id": str(neuronio.sessao_id),
        "duracao_minutos": neuronio.duracao.minutos,
        "criado_em": neuronio.criado_em.isoformat(),
    }


class IniciarSessaoSerializer(serializers.Serializer):
    duracao_minutos = serializers.IntegerField(
        help_text="De 10 a 120 minutos, de 5 em 5."
    )
    modo = serializers.ChoiceField(
        choices=["estrito", "tolerante"], default="estrito", required=False
    )
    # A matéria opcional entra com as matérias (#27).


class InterrupcaoSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField(help_text="Quando o estudante saiu da tela.")
    fim = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Quando voltou. Vazio se o aviso foi enviado no momento da saída.",
    )


class SessaoRespostaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    duracao_minutos = serializers.IntegerField()
    modo = serializers.CharField()
    estado = serializers.CharField(help_text="em_andamento, concluida ou podada")
    inicio = serializers.DateTimeField()
    fim_previsto = serializers.DateTimeField()
    encerrada_em = serializers.DateTimeField(allow_null=True)
    restante_segundos = serializers.FloatField()
    tempo_fora_segundos = serializers.FloatField()


class NeuronioRespostaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sessao_id = serializers.UUIDField()
    duracao_minutos = serializers.IntegerField()
    criado_em = serializers.DateTimeField()


class ConclusaoRespostaSerializer(serializers.Serializer):
    sessao = SessaoRespostaSerializer()
    neuronio = NeuronioRespostaSerializer()


_404 = OpenApiResponse(description="Sessão inexistente ou de outro estudante.")


@extend_schema(
    summary="Iniciar sessão de foco",
    request=IniciarSessaoSerializer,
    responses={
        201: SessaoRespostaSerializer,
        400: OpenApiResponse(description="Duração ou modo inválidos."),
        409: OpenApiResponse(description="Já existe uma sessão em andamento."),
    },
    tags=["Sessões de foco"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def iniciar(request):
    serializer = IniciarSessaoSerializer(data=request.data)
    if not serializer.is_valid():
        return _erro_de_validacao(serializer)
    dados = serializer.validated_data
    return _responder(
        lambda: _sessao_json(
            _servico().iniciar(request.user.id, dados["duracao_minutos"], dados["modo"])
        ),
        status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="Sessão em andamento",
    description="Devolve a sessão em andamento do estudante, ou 204 se não houver.",
    responses={200: SessaoRespostaSerializer, 204: None},
    tags=["Sessões de foco"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ativa(request):
    def buscar():
        sessao = _servico().buscar_ativa(request.user.id)
        return _sessao_json(sessao) if sessao else None

    return _responder(buscar, status.HTTP_200_OK)


@extend_schema(
    summary="Registrar saída da tela",
    description=(
        "A política da sessão decide se ela é podada: no modo estrito, qualquer "
        "saída; no tolerante, quando a soma das saídas passa de 10% da duração."
    ),
    request=InterrupcaoSerializer,
    responses={
        200: SessaoRespostaSerializer,
        400: OpenApiResponse(description="Horários inválidos."),
        404: _404,
        409: OpenApiResponse(description="A sessão já terminou."),
    },
    tags=["Sessões de foco"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def interrupcoes(request, sessao_id):
    serializer = InterrupcaoSerializer(data=request.data)
    if not serializer.is_valid():
        return _erro_de_validacao(serializer)
    dados = serializer.validated_data
    return _responder(
        lambda: _sessao_json(
            _servico().registrar_interrupcao(
                request.user.id, sessao_id, dados["inicio"], dados.get("fim")
            )
        ),
        status.HTTP_200_OK,
    )


@extend_schema(
    summary="Concluir sessão",
    description=(
        "Aceito só depois do tempo planejado (tolerância de 2 s). "
        "Cria o neurônio da sessão."
    ),
    request=None,
    responses={
        200: ConclusaoRespostaSerializer,
        404: _404,
        409: OpenApiResponse(description="Antes da hora ou sessão já encerrada."),
    },
    tags=["Sessões de foco"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def concluir(request, sessao_id):
    def executar():
        sessao, neuronio = _servico().concluir(request.user.id, sessao_id)
        return {"sessao": _sessao_json(sessao), "neuronio": _neuronio_json(neuronio)}

    return _responder(executar, status.HTTP_200_OK)


@extend_schema(
    summary="Desistir da sessão",
    description="A desistência conta como poda.",
    request=None,
    responses={
        200: SessaoRespostaSerializer,
        404: _404,
        409: OpenApiResponse(description="A sessão já terminou."),
    },
    tags=["Sessões de foco"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def desistir(request, sessao_id):
    return _responder(
        lambda: _sessao_json(_servico().desistir(request.user.id, sessao_id)),
        status.HTTP_200_OK,
    )
