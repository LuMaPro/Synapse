from collections.abc import Callable
from typing import Any

from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.api.periodo import DESCRICAO_PERIODO, FiltroPeriodoSerializer
from app.application.conquistas import ConquistaService
from app.application.loja import FabricaDoEstudante, LojaService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.carteira import atp_da_sessao
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.excecoes import (
    DuracaoInvalida,
    ErroDominio,
    HorarioInvalido,
    MateriaNaoEncontrada,
    PoliticaInvalida,
    SessaoAtivaExistente,
    SessaoNaoEncontrada,
    TransicaoInvalida,
)
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

# Provisório até o tratamento de erros nas bordas da API (#12): status e código de
# cada erro de domínio, aplicados num único lugar (`_responder`).
ERROS_SESSAO: dict[type[ErroDominio], tuple[int, str]] = {
    SessaoNaoEncontrada: (status.HTTP_404_NOT_FOUND, "sessao_nao_encontrada"),
    MateriaNaoEncontrada: (status.HTTP_404_NOT_FOUND, "materia_nao_encontrada"),
    SessaoAtivaExistente: (status.HTTP_409_CONFLICT, "sessao_ativa_existente"),
    TransicaoInvalida: (status.HTTP_409_CONFLICT, "transicao_invalida"),
    DuracaoInvalida: (status.HTTP_400_BAD_REQUEST, "duracao_invalida"),
    HorarioInvalido: (status.HTTP_400_BAD_REQUEST, "horario_invalido"),
    PoliticaInvalida: (status.HTTP_400_BAD_REQUEST, "modo_invalido"),
}


def _servico() -> SessaoService:
    # Configura a rede e o observador
    redes = RepositorioRedeNeuralDjango()
    rede_service = RedeNeuralService(redes)
    atualizador = AtualizadorRede(rede_service)
    avaliador = AvaliadorConquistas(
        ConquistaService(RepositorioConquistaDjango(), redes)
    )
    loja = LojaService(RepositorioCarteiraDjango())

    # Configura o publicador e inscreve os observadores. O avaliador de conquistas
    # vem depois do atualizador da rede: ele olha a rede já com o neurônio novo.
    publicador = PublicadorEventos()
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    publicador.inscrever(SessaoConcluida, avaliador)
    publicador.inscrever(SessaoConcluida, CreditadorATP(loja))

    # O relógio é lido a cada chamada, o que permite controlá-lo nos testes.
    return SessaoService(
        RepositorioSessaoDjango(),
        publicador,  # <-- Injetamos o publicador aqui
        relogio=lambda: agora(),
        materias=RepositorioMateriaDjango(),
        # Os neurônios saem com os tipos que o estudante escolheu na loja (#34).
        fabrica=FabricaDoEstudante(loja),
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
        "materia_id": str(sessao.materia_id) if sessao.materia_id else None,
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
        "materia_id": str(neuronio.materia_id) if neuronio.materia_id else None,
        "criado_em": neuronio.criado_em.isoformat(),
        "tipo": neuronio.tipo.forma,
        "variante": neuronio.tipo.codigo,
        "cor": neuronio.cor,
    }


class IniciarSessaoSerializer(serializers.Serializer):
    duracao_minutos = serializers.IntegerField(
        help_text="De 10 a 120 minutos, de 5 em 5."
    )
    modo = serializers.ChoiceField(
        choices=["estrito", "tolerante"], default="estrito", required=False
    )
    materia_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Identificador da matéria associada à sessão (opcional).",
    )


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
    materia_id = serializers.UUIDField(allow_null=True)
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
    materia_id = serializers.UUIDField(allow_null=True, required=False)
    criado_em = serializers.DateTimeField()
    tipo = serializers.ChoiceField(
        choices=["granular", "piramidal", "purkinje"],
        help_text="A forma do neurônio, pela duração.",
    )
    variante = serializers.CharField(
        help_text="Código do tipo usado (ex.: piramidal ou piramidal_rosa, da loja)."
    )
    cor = serializers.CharField(help_text="Cor do tipo (hexadecimal).")


class ConclusaoRespostaSerializer(serializers.Serializer):
    sessao = SessaoRespostaSerializer()
    neuronio = NeuronioRespostaSerializer()
    atp = serializers.IntegerField(help_text="ATP ganho: 1 por minuto da sessão.")


_404 = OpenApiResponse(description="Sessão inexistente ou de outro estudante.")

TAMANHO_PADRAO = 20
TAMANHO_MAXIMO = 100


class FiltrosHistoricoSerializer(FiltroPeriodoSerializer):
    status = serializers.ChoiceField(
        choices=["em_andamento", "concluida", "podada"], required=False
    )
    pagina = serializers.IntegerField(min_value=1, default=1, required=False)
    tamanho = serializers.IntegerField(
        min_value=1, max_value=TAMANHO_MAXIMO, default=TAMANHO_PADRAO, required=False
    )


class HistoricoRespostaSerializer(serializers.Serializer):
    total = serializers.IntegerField(help_text="Sessões que atendem aos filtros.")
    pagina = serializers.IntegerField()
    tamanho = serializers.IntegerField()
    paginas = serializers.IntegerField()
    resultados = SessaoRespostaSerializer(many=True)


_EXEMPLO_HISTORICO = {
    "total": 2,
    "pagina": 1,
    "tamanho": 20,
    "paginas": 1,
    "resultados": [
        {
            "id": "3f2b8c1e-5d4a-4e6f-9a1b-2c3d4e5f6a7b",
            "duracao_minutos": 25,
            "modo": "estrito",
            "materia_id": "8a7b6c5d-4e3f-4a1b-9c2d-1e0f9a8b7c6d",
            "estado": "concluida",
            "inicio": "2026-10-26T14:00:00+00:00",
            "fim_previsto": "2026-10-26T14:25:00+00:00",
            "encerrada_em": "2026-10-26T14:25:00+00:00",
            "restante_segundos": 0.0,
            "tempo_fora_segundos": 0.0,
        },
        {
            "id": "9e8d7c6b-5a4f-4e3d-8c1b-0a9f8e7d6c5b",
            "duracao_minutos": 50,
            "modo": "tolerante",
            "materia_id": None,
            "estado": "podada",
            "inicio": "2026-10-25T09:00:00+00:00",
            "fim_previsto": "2026-10-25T09:50:00+00:00",
            "encerrada_em": "2026-10-25T09:12:30+00:00",
            "restante_segundos": 0.0,
            "tempo_fora_segundos": 120.0,
        },
    ],
}


def _iniciar(request) -> Response:
    serializer = IniciarSessaoSerializer(data=request.data)
    if not serializer.is_valid():
        return _erro_de_validacao(serializer)
    dados = serializer.validated_data
    return _responder(
        lambda: _sessao_json(
            _servico().iniciar(
                request.user.id,
                dados["duracao_minutos"],
                dados["modo"],
                materia_id=dados.get("materia_id"),
            )
        ),
        status.HTTP_201_CREATED,
    )


def _historico(request) -> Response:
    filtros = FiltrosHistoricoSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    dados = filtros.validated_data

    def listar():
        pagina = _servico().historico(
            request.user.id,
            de=dados.get("de"),
            ate=dados.get("ate"),
            estado=dados.get("status"),
            pagina=dados["pagina"],
            tamanho=dados["tamanho"],
        )
        return {
            "total": pagina.total,
            "pagina": pagina.pagina,
            "tamanho": pagina.tamanho,
            "paginas": pagina.paginas,
            "resultados": [_sessao_json(s) for s in pagina.sessoes],
        }

    return _responder(listar, status.HTTP_200_OK)


@extend_schema(
    methods=["GET"],
    summary="Histórico de sessões",
    description=(
        "As sessões do estudante, da mais recente para a mais antiga, em páginas. "
        "O período filtra pelo início da sessão."
    ),
    parameters=[
        OpenApiParameter(
            "de",
            OpenApiTypes.STR,
            description=f"Início do período (inclusive). {DESCRICAO_PERIODO}",
            examples=[OpenApiExample("Data", value="2026-10-01")],
        ),
        OpenApiParameter(
            "ate",
            OpenApiTypes.STR,
            description=f"Fim do período (inclusive). {DESCRICAO_PERIODO}",
            examples=[OpenApiExample("Data", value="2026-10-31")],
        ),
        OpenApiParameter(
            "status",
            OpenApiTypes.STR,
            enum=["em_andamento", "concluida", "podada"],
            description="Só as sessões neste estado.",
        ),
        OpenApiParameter(
            "pagina", OpenApiTypes.INT, description="Começa em 1 (padrão: 1)."
        ),
        OpenApiParameter(
            "tamanho",
            OpenApiTypes.INT,
            description=(
                f"Sessões por página, de 1 a {TAMANHO_MAXIMO} "
                f"(padrão: {TAMANHO_PADRAO})."
            ),
        ),
    ],
    responses={
        200: OpenApiResponse(
            HistoricoRespostaSerializer,
            examples=[OpenApiExample("Uma página", value=_EXEMPLO_HISTORICO)],
        ),
        400: OpenApiResponse(description="Filtro inválido."),
    },
    tags=["Sessões de foco"],
)
@extend_schema(
    methods=["POST"],
    summary="Iniciar sessão de foco",
    request=IniciarSessaoSerializer,
    responses={
        201: SessaoRespostaSerializer,
        400: OpenApiResponse(description="Duração ou modo inválidos."),
        404: OpenApiResponse(description="Matéria inexistente ou de outro estudante."),
        409: OpenApiResponse(description="Já existe uma sessão em andamento."),
    },
    tags=["Sessões de foco"],
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def sessoes(request):
    """`GET`: histórico (#29). `POST`: inicia uma sessão (#16)."""
    return _historico(request) if request.method == "GET" else _iniciar(request)


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
        return {
            "sessao": _sessao_json(sessao),
            "neuronio": _neuronio_json(neuronio),
            # O mesmo valor que o CreditadorATP acabou de creditar (#34).
            "atp": atp_da_sessao(sessao.duracao.minutos),
        }

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
