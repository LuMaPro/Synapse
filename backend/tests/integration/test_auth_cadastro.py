import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

UsuarioModel = get_user_model()
pytestmark = pytest.mark.django_db


def test_cadastro_sucesso():
    cliente = APIClient()
    resposta = cliente.post(
        "/auth/cadastro",
        {
            "nome": "Mariana Souza",
            "email": "mariana@synapse.com",
            "senha": "senha-segura-123",
        },
        format="json",
    )

    assert resposta.status_code == 201
    dados = resposta.json()
    assert "id" in dados
    assert dados["nome"] == "Mariana Souza"
    assert dados["email"] == "mariana@synapse.com"
    assert "senha" not in dados
    assert "password" not in dados

    # Verifica persistência no banco e senha hasheada com Argon2
    usuario = UsuarioModel.objects.get(email="mariana@synapse.com")
    assert usuario.nome == "Mariana Souza"
    assert usuario.password.startswith("argon2")
    assert usuario.check_password("senha-segura-123")


def test_cadastro_email_duplicado():
    cliente = APIClient()
    # Primeiro cadastro
    cliente.post(
        "/auth/cadastro",
        {
            "nome": "Primeiro",
            "email": "duplicado@synapse.com",
            "senha": "senha-123456",
        },
        format="json",
    )

    # Tentativa com o mesmo e-mail (em maiúsculas)
    resposta = cliente.post(
        "/auth/cadastro",
        {
            "nome": "Segundo",
            "email": "DUPLICADO@synapse.com",
            "senha": "outra-senha-123",
        },
        format="json",
    )

    assert resposta.status_code == 400
    dados = resposta.json()
    assert dados["erro"] == "email_duplicado"
    assert "já cadastrado" in dados["mensagem"].lower()


@pytest.mark.parametrize(
    ("payload", "campo_esperado"),
    [
        ({"email": "a@b.com", "senha": "senha-123"}, "nome"),
        ({"nome": "   ", "email": "a@b.com", "senha": "senha-123"}, "nome"),
        ({"nome": "Ana", "senha": "senha-123"}, "email"),
        ({"nome": "Ana", "email": "invalido", "senha": "senha-123"}, "email"),
        ({"nome": "Ana", "email": "a@b.com"}, "senha"),
        ({"nome": "Ana", "email": "a@b.com", "senha": "123"}, "senha"),
    ],
)
def test_cadastro_validacao_campos_invalidos(payload, campo_esperado):
    cliente = APIClient()
    resposta = cliente.post("/auth/cadastro", payload, format="json")

    assert resposta.status_code == 400
    dados = resposta.json()
    assert campo_esperado in dados["erro"]


@pytest.mark.parametrize(
    ("senha", "trecho_da_mensagem"),
    [
        ("Ab1-xyz", "muito curta"),
        ("12345678", "inteiramente numérica"),
        ("password123", "muito comum"),
        ("mariana@synapse.com", "muito parecida"),
    ],
)
def test_cadastro_recusa_senha_fraca(senha, trecho_da_mensagem):
    resposta = APIClient().post(
        "/auth/cadastro",
        {"nome": "Mariana", "email": "mariana@synapse.com", "senha": senha},
        format="json",
    )

    assert resposta.status_code == 400
    dados = resposta.json()
    assert dados["erro"] == "senha_invalido"
    assert trecho_da_mensagem in dados["mensagem"]
    assert not UsuarioModel.objects.filter(email="mariana@synapse.com").exists()
