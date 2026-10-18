from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from app.application.cadastro import CadastroUsuario
from app.domain.excecoes import (
    EmailInvalido,
    EmailJaCadastrado,
    ErroDominio,
    NomeInvalido,
    SenhaInvalida,
)
from app.infra.repositorios import RepositorioUsuarioDjango
from app.infra.senhas import ServicoSenhasDjango

UsuarioModel = get_user_model()

CODIGOS_ERRO_CADASTRO = {
    EmailJaCadastrado: "email_duplicado",
    SenhaInvalida: "senha_invalido",
    EmailInvalido: "email_invalido",
    NomeInvalido: "nome_invalido",
}


class CadastroSerializer(serializers.Serializer):
    nome = serializers.CharField(
        max_length=150,
        required=True,
        error_messages={
            "required": "O nome é obrigatório.",
            "blank": "O nome é obrigatório.",
        },
    )
    email = serializers.EmailField(
        max_length=254,
        required=True,
        error_messages={
            "required": "O e-mail é obrigatório.",
            "blank": "O e-mail é obrigatório.",
            "invalid": "Digite um e-mail válido.",
        },
    )
    # As regras de senha (tamanho, senhas comuns...) ficam nos AUTH_PASSWORD_VALIDATORS,
    # aplicados pelo caso de uso CadastroUsuario.
    senha = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": "A senha é obrigatória.",
            "blank": "A senha é obrigatória.",
        },
    )


class UsuarioRespostaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    email = serializers.EmailField()


@extend_schema(
    summary="Cadastro de novo usuário",
    description=(
        "Cria um novo estudante com nome, e-mail e senha hasheada com Argon2."
    ),
    request=CadastroSerializer,
    responses={
        201: UsuarioRespostaSerializer,
        400: OpenApiResponse(
            description="Dados inválidos, senha fraca ou e-mail já cadastrado."
        ),
    },
    tags=["Autenticação"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def cadastro(request):
    """Endpoint para cadastro de novo usuário com e-mail único."""
    dados = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
    if "email" not in dados and "e-mail" in dados:
        dados["email"] = dados["e-mail"]

    serializer = CadastroSerializer(data=dados)
    if not serializer.is_valid():
        primeiro_campo, erros = next(iter(serializer.errors.items()))
        mensagem_erro = erros[0] if isinstance(erros, list) else str(erros)
        codigo = f"{primeiro_campo}_invalido"
        return Response(
            {"erro": codigo, "mensagem": mensagem_erro},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cadastro_usuario = CadastroUsuario(
        RepositorioUsuarioDjango(), ServicoSenhasDjango()
    )
    try:
        # Salvar o usuário e definir a senha são duas escritas: ou as duas, ou nenhuma.
        with transaction.atomic():
            usuario = cadastro_usuario.executar(
                nome=serializer.validated_data["nome"],
                email=serializer.validated_data["email"],
                senha=serializer.validated_data["senha"],
            )
    except ErroDominio as erro:
        # Provisório até o tratamento de erros nas bordas da API (#12).
        codigo = CODIGOS_ERRO_CADASTRO.get(type(erro), "dados_invalidos")
        return Response(
            {"erro": codigo, "mensagem": str(erro)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
        },
        status=status.HTTP_201_CREATED,
    )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        max_length=254,
        required=True,
        error_messages={
            "required": "O e-mail é obrigatório.",
            "blank": "O e-mail é obrigatório.",
            "invalid": "Digite um e-mail válido.",
        },
    )
    senha = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={
            "required": "A senha é obrigatória.",
            "blank": "A senha é obrigatória.",
        },
    )


class TokenRespostaSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Token JWT de acesso (15 minutos)")
    refresh = serializers.CharField(help_text="Token JWT de renovação (7 dias)")


@extend_schema(
    summary="Login de usuário",
    description=(
        "Autentica o estudante com e-mail e senha, "
        "retornando os tokens JWT (access e refresh)."
    ),
    request=LoginSerializer,
    responses={
        200: TokenRespostaSerializer,
        400: OpenApiResponse(
            description="Dados inválidos ou campos obrigatórios ausentes."
        ),
        401: OpenApiResponse(
            description="Credenciais inválidas ou usuário inativo."
        ),
    },
    tags=["Autenticação"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Endpoint para autenticação de usuário com tokens JWT."""
    dados = (
        request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
    )
    if "email" not in dados and "e-mail" in dados:
        dados["email"] = dados["e-mail"]
    if "senha" not in dados and "password" in dados:
        dados["senha"] = dados["password"]

    serializer = LoginSerializer(data=dados)
    if not serializer.is_valid():
        primeiro_campo, erros = next(iter(serializer.errors.items()))
        mensagem_erro = erros[0] if isinstance(erros, list) else str(erros)
        codigo = f"{primeiro_campo}_invalido"
        return Response(
            {"erro": codigo, "mensagem": mensagem_erro},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = serializer.validated_data["email"].strip().lower()
    senha = serializer.validated_data["senha"]

    usuario = UsuarioModel.objects.filter(email=email).first()
    if usuario is None or not usuario.check_password(senha):
        return Response(
            {
                "erro": "credenciais_invalidas",
                "mensagem": "E-mail ou senha incorretos.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not usuario.is_active:
        return Response(
            {
                "erro": "usuario_inativo",
                "mensagem": "Esta conta de usuário está desativada.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(usuario)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Dados do estudante logado",
    description="Retorna os dados do estudante autenticado via Bearer JWT.",
    responses={
        200: UsuarioRespostaSerializer,
        401: OpenApiResponse(description="Token ausente, inválido ou expirado."),
    },
    tags=["Autenticação"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Endpoint para recuperar os dados do estudante autenticado."""
    usuario = request.user
    return Response(
        {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
        },
        status=status.HTTP_200_OK,
    )


class RenovarTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        error_messages={
            "required": "O token de renovação é obrigatório.",
            "blank": "O token de renovação é obrigatório.",
        },
        help_text="Token JWT de renovação",
    )


class RenovarTokenRespostaSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Novo token JWT de acesso (15 minutos)")
    refresh = serializers.CharField(
        required=False,
        help_text="Novo token de renovação (caso rotação esteja ativada)",
    )


@extend_schema(
    summary="Renovação de token de acesso",
    description=(
        "Emite um novo token JWT de acesso a partir de um refresh token válido."
    ),
    request=RenovarTokenSerializer,
    responses={
        200: RenovarTokenRespostaSerializer,
        400: OpenApiResponse(description="Token de renovação ausente ou inválido."),
        401: OpenApiResponse(
            description="Token de renovação expirado, inválido ou usuário inativo."
        ),
    },
    tags=["Autenticação"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def renovar(request):
    """Endpoint para renovar token JWT de acesso usando o token de refresh."""
    serializer = RenovarTokenSerializer(data=request.data)
    if not serializer.is_valid():
        primeiro_campo, erros = next(iter(serializer.errors.items()))
        mensagem_erro = erros[0] if isinstance(erros, list) else str(erros)
        codigo = f"{primeiro_campo}_invalido"
        return Response(
            {"erro": codigo, "mensagem": mensagem_erro},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token_str = serializer.validated_data["refresh"]
    try:
        refresh = RefreshToken(token_str)
    except TokenError:
        return Response(
            {
                "erro": "token_invalido",
                "mensagem": "Token de renovação inválido ou expirado.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
    usuario = UsuarioModel.objects.filter(id=user_id).first()
    if usuario is None or not usuario.is_active:
        return Response(
            {
                "erro": (
                    "usuario_inativo"
                    if usuario and not usuario.is_active
                    else "token_invalido"
                ),
                "mensagem": (
                    "Esta conta de usuário está desativada."
                    if usuario and not usuario.is_active
                    else "Usuário associado ao token não encontrado."
                ),
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    dados_resposta = {
        "access": str(refresh.access_token),
    }

    if api_settings.ROTATE_REFRESH_TOKENS:
        if api_settings.BLACKLIST_AFTER_ROTATION:
            try:
                refresh.blacklist()
            except AttributeError:
                pass
        refresh.set_jti()
        refresh.set_exp()
        dados_resposta["refresh"] = str(refresh)

    return Response(dados_resposta, status=status.HTTP_200_OK)



