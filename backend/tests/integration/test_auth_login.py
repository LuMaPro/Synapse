import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

UsuarioModel = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario_existente():
    return UsuarioModel.objects.create_user(
        email="aluno@synapse.com",
        nome="Aluno Focado",
        password="senha-super-secreta",
    )


def test_login_sucesso(usuario_existente):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "email": "aluno@synapse.com",
            "senha": "senha-super-secreta",
        },
        format="json",
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert "access" in dados
    assert "refresh" in dados

    token = AccessToken(dados["access"])
    assert token["user_id"] == str(usuario_existente.id)


def test_login_email_case_insensitive(usuario_existente):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "email": "  ALUNO@synapse.com  ",
            "senha": "senha-super-secreta",
        },
        format="json",
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert "access" in dados
    assert "refresh" in dados


def test_login_suporta_alias_email_e_password(usuario_existente):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "e-mail": "aluno@synapse.com",
            "password": "senha-super-secreta",
        },
        format="json",
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert "access" in dados
    assert "refresh" in dados


def test_login_senha_incorreta(usuario_existente):
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "email": "aluno@synapse.com",
            "senha": "senha-errada",
        },
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "credenciais_invalidas"
    assert "incorretos" in dados["mensagem"].lower()


def test_login_usuario_inexistente():
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "email": "naoexiste@synapse.com",
            "senha": "qualquer-senha",
        },
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "credenciais_invalidas"
    assert "incorretos" in dados["mensagem"].lower()


def test_login_usuario_inativo():
    usuario = UsuarioModel.objects.create_user(
        email="inativo@synapse.com",
        nome="Aluno Inativo",
        password="senha-valida-123",
    )
    usuario.is_active = False
    usuario.save()

    cliente = APIClient()
    resposta = cliente.post(
        "/auth/login",
        {
            "email": "inativo@synapse.com",
            "senha": "senha-valida-123",
        },
        format="json",
    )

    assert resposta.status_code == 401
    dados = resposta.json()
    assert dados["erro"] == "usuario_inativo"
    assert "desativada" in dados["mensagem"].lower()


@pytest.mark.parametrize(
    ("payload", "campo_esperado"),
    [
        ({"senha": "senha-123"}, "email"),
        ({"email": "   ", "senha": "senha-123"}, "email"),
        ({"email": "email-invalido", "senha": "senha-123"}, "email"),
        ({"email": "aluno@synapse.com"}, "senha"),
        ({"email": "aluno@synapse.com", "senha": ""}, "senha"),
    ],
)
def test_login_validacao_campos(payload, campo_esperado):
    cliente = APIClient()
    resposta = cliente.post("/auth/login", payload, format="json")

    assert resposta.status_code == 400
    dados = resposta.json()
    assert campo_esperado in dados["erro"]
