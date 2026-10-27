import logging
import re

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as handler_padrao_drf

from app.domain import excecoes as dominio

logger = logging.getLogger(__name__)

# Tabela: qual exceção vira qual código HTTP
STATUS_POR_ERRO_DOMINIO = {
    dominio.SessaoNaoEncontrada: status.HTTP_404_NOT_FOUND,
    dominio.MateriaNaoEncontrada: status.HTTP_404_NOT_FOUND,
    dominio.TipoNaoEncontrado: status.HTTP_404_NOT_FOUND,
    dominio.EmailJaCadastrado: status.HTTP_409_CONFLICT,
    dominio.SessaoAtivaExistente: status.HTTP_409_CONFLICT,
    dominio.TransicaoInvalida: status.HTTP_409_CONFLICT,
    dominio.MateriaJaExiste: status.HTTP_409_CONFLICT,
    dominio.SaldoInsuficiente: status.HTTP_409_CONFLICT,
    dominio.TipoJaDesbloqueado: status.HTTP_409_CONFLICT,
    dominio.TipoBloqueado: status.HTTP_409_CONFLICT,
    dominio.DuracaoInvalida: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.NomeInvalido: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.NomeMateriaInvalido: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.CorInvalida: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.EmailInvalido: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.HorarioInvalido: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.SenhaInvalida: status.HTTP_422_UNPROCESSABLE_ENTITY,
    dominio.PoliticaInvalida: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def _codigo(exc: Exception) -> str:
    """Transforma o nome da classe em texto legível.

    Exemplo: SessaoNaoEncontrada -> sessao_nao_encontrada.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()


def _resposta(status_http: int, codigo: str, mensagem: str, detalhes=None) -> Response:
    corpo = {"erro": codigo, "mensagem": mensagem}
    if detalhes is not None:
        corpo["detalhes"] = detalhes
    return Response(corpo, status=status_http)


def exception_handler(exc, context):
    # Parte 1: erros de domínio
    if isinstance(exc, dominio.ErroDominio):
        status_http = STATUS_POR_ERRO_DOMINIO.get(
            type(exc), status.HTTP_400_BAD_REQUEST
        )
        mensagem = str(exc) or "Erro de regra de negócio."
        return _resposta(status_http, _codigo(exc), mensagem)

    # Parte 2: erros que o DRF já conhece
    resposta = handler_padrao_drf(exc, context)
    if resposta is not None:
        if isinstance(exc, ValidationError):
            return _resposta(
                resposta.status_code,
                "validacao",
                "Os dados enviados são inválidos.",
                detalhes=resposta.data,
            )
        if isinstance(exc, NotAuthenticated | AuthenticationFailed):
            return _resposta(
                resposta.status_code,
                "nao_autenticado",
                "Credenciais ausentes ou inválidas.",
            )
        if isinstance(exc, PermissionDenied):
            return _resposta(
                resposta.status_code,
                "sem_permissao",
                "Você não tem permissão para esta ação.",
            )
        return _resposta(
            resposta.status_code,
            "erro_requisicao",
            str(getattr(exc, "detail", "Erro na requisição.")),
        )

    # Parte 3: erro inesperado -> 500 genérico, detalhe só no log
    logger.exception("Erro inesperado na view %s", context.get("view"))
    return _resposta(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "erro_interno",
        "Ocorreu um erro interno. Tente novamente mais tarde.",
    )
