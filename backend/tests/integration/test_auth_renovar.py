from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

UsuarioModel = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario():
    return UsuarioModel.objects.create_user(
        email="estudante.renovacao@synapse.com",
        nome="Estudante Renovador",
        password="senha-segura-123",
    )


@pytest.fixture
def refresh_token(usuario):
    return RefreshToken.for_user(usuario)


def test_renovar_token_sucesso(usuario, refresh_token):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/renovar",
        {"refresh": str(refresh_token)},
        format="json",
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert "access" in dados

    novo_access = dados["access"]
    token = AccessToken(novo_access)
    assert token["user_id"] == str(usuario.id)

    # Verifica que o novo access token permite autenticar no /me
    resposta_me = cliente.get(
        "/me",
        HTTP_AUTHORIZATION=f"Bearer {novo_access}",
    )
    assert resposta_me.status_code == 200
    assert resposta_me.json()["email"] == usuario.email


def test_renovar_com_token_invalido():
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/renovar",
        {"refresh": "token-totalmente-invalido"},
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "token_invalido"
    assert "inválido ou expirado" in dados["mensagem"].lower()


def test_renovar_com_token_expirado(refresh_token):
    refresh_token.set_exp(lifetime=-timedelta(minutes=1))

    cliente = APIClient()
    resposta = cliente.post(
        "/auth/renovar",
        {"refresh": str(refresh_token)},
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "token_invalido"


def test_renovar_com_access_token_ao_inves_de_refresh(refresh_token):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/renovar",
        {"refresh": str(refresh_token.access_token)},
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "token_invalido"


def test_renovar_com_usuario_inativo(usuario, refresh_token):
    usuario.is_active = False
    usuario.save()

    cliente = APIClient()
    resposta = cliente.post(
        "/auth/renovar",
        {"refresh": str(refresh_token)},
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "usuario_inativo"
    assert "desativada" in dados["mensagem"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"refresh": ""},
        {"refresh": "   "},
    ],
)
def test_renovar_sem_token_no_payload(payload):
    cliente = APIClient()
    resposta = cliente.post("/auth/renovar", payload, format="json")

    assert resposta.status_code == 400
    dados = resposta.json()
    assert dados["erro"] == "refresh_invalido"
