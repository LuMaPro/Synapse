from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

UsuarioModel = get_user_model()


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
    senha = serializers.CharField(
        write_only=True,
        required=True,
        min_length=6,
        error_messages={
            "required": "A senha é obrigatória.",
            "blank": "A senha é obrigatória.",
            "min_length": "A senha deve ter no mínimo 6 caracteres.",
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
        400: OpenApiResponse(description="Dados inválidos ou e-mail já cadastrado."),
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

    email = serializer.validated_data["email"].strip().lower()
    nome = serializer.validated_data["nome"].strip()
    senha = serializer.validated_data["senha"]

    if UsuarioModel.objects.filter(email=email).exists():
        return Response(
            {
                "erro": "email_duplicado",
                "mensagem": (
                    "E-mail já cadastrado. Tente fazer login ou use outro e-mail."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    usuario = UsuarioModel.objects.create_user(
        email=email,
        nome=nome,
        password=senha,
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

