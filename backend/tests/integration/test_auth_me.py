from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

UsuarioModel = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario():
    return UsuarioModel.objects.create_user(
        email="estudante@synapse.com",
        nome="Estudante Dedicado",
        password="senha-segura-123",
    )


@pytest.fixture
def token_acesso(usuario):
    refresh = RefreshToken.for_user(usuario)
    return str(refresh.access_token)


def test_me_sucesso_com_token_valido(usuario, token_acesso):
    cliente = APIClient()
    resposta = cliente.get(
        "/me",
        HTTP_AUTHORIZATION=f"Bearer {token_acesso}",
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["id"] == str(usuario.id)
    assert dados["nome"] == "Estudante Dedicado"
    assert dados["email"] == "estudante@synapse.com"
    assert "password" not in dados
    assert "senha" not in dados


def test_me_sem_token_retorna_401():
    cliente = APIClient()
    resposta = cliente.get("/me")

    assert resposta.status_code == 401


def test_me_com_token_invalido_retorna_401():
    cliente = APIClient()
    resposta = cliente.get(
        "/me",
        HTTP_AUTHORIZATION="Bearer token-jwt-completamente-invalido",
    )

    assert resposta.status_code == 401


def test_me_com_token_expirado_retorna_401(usuario):
    refresh = RefreshToken.for_user(usuario)
    token_expirado = refresh.access_token
    token_expirado.set_exp(lifetime=-timedelta(minutes=1))

    cliente = APIClient()
    resposta = cliente.get(
        "/me",
        HTTP_AUTHORIZATION=f"Bearer {token_expirado}",
    )

    assert resposta.status_code == 401


def test_me_com_usuario_inativo_retorna_401(usuario, token_acesso):
    usuario.is_active = False
    usuario.save()

    cliente = APIClient()
    resposta = cliente.get(
        "/me",
        HTTP_AUTHORIZATION=f"Bearer {token_acesso}",
    )

    assert resposta.status_code == 401


@pytest.mark.parametrize(
    "header_invalido",
    [
        "Token abc123",
        "Basic dXNlcjpwYXNz",
        "Bearer",
        "Bearer   ",
        "Bearer token1 token2",
    ],
)
def test_me_com_header_authorization_malformado(header_invalido):
    cliente = APIClient()
    resposta = cliente.get(
        "/me",
        HTTP_AUTHORIZATION=header_invalido,
    )

    assert resposta.status_code == 401
