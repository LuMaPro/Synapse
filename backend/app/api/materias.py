from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.application.materias import MateriaService
from app.domain.entidades.materia import Materia
from app.domain.excecoes import (
    CorInvalida,
    ErroDominio,
    MateriaJaExiste,
    MateriaNaoEncontrada,
    NomeMateriaInvalido,
)
from app.infra.repositorios import RepositorioMateriaDjango

ERROS_MATERIA: dict[type[ErroDominio], tuple[int, str]] = {
    MateriaNaoEncontrada: (status.HTTP_404_NOT_FOUND, "materia_nao_encontrada"),
    MateriaJaExiste: (status.HTTP_409_CONFLICT, "materia_ja_existe"),
    NomeMateriaInvalido: (status.HTTP_400_BAD_REQUEST, "nome_invalido"),
    CorInvalida: (status.HTTP_400_BAD_REQUEST, "cor_invalido"),
}


def _servico() -> MateriaService:
    return MateriaService(RepositorioMateriaDjango())


def _materia_json(materia: Materia) -> dict[str, Any]:
    return {
        "id": str(materia.id),
        "nome": materia.nome,
        "cor": materia.cor,
        "criada_em": materia.criada_em.isoformat(),
    }


def _responder(acao: Callable[[], Any], status_sucesso: int) -> Response:
    with transaction.atomic():
        try:
            corpo = acao()
        except ErroDominio as erro:
            codigo_http, codigo = ERROS_MATERIA.get(
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


class MateriaRespostaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    cor = serializers.CharField()
    criada_em = serializers.DateTimeField()


class CriarMateriaSerializer(serializers.Serializer):
    nome = serializers.CharField(
        max_length=100,
        required=True,
        error_messages={
            "required": "O nome é obrigatório.",
            "blank": "O nome é obrigatório.",
        },
    )
    cor = serializers.CharField(
        max_length=7,
        required=True,
        error_messages={
            "required": "A cor é obrigatória.",
            "blank": "A cor é obrigatória.",
        },
    )


class AtualizarMateriaSerializer(serializers.Serializer):
    nome = serializers.CharField(
        max_length=100,
        required=False,
        error_messages={
            "blank": "O nome não pode ser vazio.",
        },
    )
    cor = serializers.CharField(
        max_length=7,
        required=False,
        error_messages={
            "blank": "A cor não pode ser vazia.",
        },
    )


_404 = OpenApiResponse(description="Matéria inexistente ou de outro estudante.")


@extend_schema(
    methods=["GET"],
    summary="Listar matérias",
    description="Devolve a lista de todas as matérias cadastradas pelo estudante.",
    responses={200: MateriaRespostaSerializer(many=True)},
    tags=["Matérias"],
)
@extend_schema(
    methods=["POST"],
    summary="Criar matéria",
    description=(
        "Cadastra uma nova matéria com nome e código hexadecimal de cor (#RRGGBB)."
    ),
    request=CriarMateriaSerializer,
    responses={
        201: MateriaRespostaSerializer,
        400: OpenApiResponse(description="Nome ou cor inválidos."),
        409: OpenApiResponse(description="Matéria com este nome já cadastrada."),
    },
    tags=["Matérias"],
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def materias(request) -> Response:
    if request.method == "GET":
        return _responder(
            lambda: [_materia_json(m) for m in _servico().listar(request.user.id)],
            status.HTTP_200_OK,
        )

    serializer = CriarMateriaSerializer(data=request.data)
    if not serializer.is_valid():
        return _erro_de_validacao(serializer)
    dados = serializer.validated_data
    return _responder(
        lambda: _materia_json(
            _servico().criar(request.user.id, dados["nome"], dados["cor"])
        ),
        status.HTTP_201_CREATED,
    )


@extend_schema(
    methods=["GET"],
    summary="Buscar matéria",
    description="Devolve os dados de uma matéria específica do estudante.",
    responses={200: MateriaRespostaSerializer, 404: _404},
    tags=["Matérias"],
)
@extend_schema(
    methods=["PATCH"],
    summary="Atualizar matéria",
    description="Atualiza o nome e/ou cor de uma matéria existente.",
    request=AtualizarMateriaSerializer,
    responses={
        200: MateriaRespostaSerializer,
        400: OpenApiResponse(description="Dados inválidos."),
        404: _404,
        409: OpenApiResponse(description="Nome em conflito com outra matéria."),
    },
    tags=["Matérias"],
)
@extend_schema(
    methods=["DELETE"],
    summary="Remover matéria",
    description="Exclui a matéria do estudante. Não apaga as sessões vinculadas.",
    responses={204: None, 404: _404},
    tags=["Matérias"],
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def detalhe_materia(request, materia_id: UUID) -> Response:
    if request.method == "GET":
        return _responder(
            lambda: _materia_json(_servico().buscar(request.user.id, materia_id)),
            status.HTTP_200_OK,
        )

    if request.method == "PATCH":
        serializer = AtualizarMateriaSerializer(data=request.data)
        if not serializer.is_valid():
            return _erro_de_validacao(serializer)
        dados = serializer.validated_data
        return _responder(
            lambda: _materia_json(
                _servico().atualizar(
                    request.user.id,
                    materia_id,
                    nome=dados.get("nome"),
                    cor=dados.get("cor"),
                )
            ),
            status.HTTP_200_OK,
        )

    return _responder(
        lambda: _servico().remover(request.user.id, materia_id),
        status.HTTP_204_NO_CONTENT,
    )
