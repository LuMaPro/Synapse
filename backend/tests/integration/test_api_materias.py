from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from app.infra.modelos.materia import MateriaModel

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
def cliente(usuario):
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente


@pytest.fixture
def outro_usuario():
    return UsuarioModel.objects.create_user(
        email="outro@synapse.com",
        nome="Outro Estudante",
        password="senha-segura-123",
    )


@pytest.fixture
def outro_cliente(outro_usuario):
    cliente = APIClient()
    cliente.force_authenticate(user=outro_usuario)
    return cliente


# ------------------------------------------------------------------ Autenticação


@pytest.mark.parametrize(
    ("metodo", "url"),
    [
        ("get", "/materias"),
        ("post", "/materias"),
        ("get", f"/materias/{uuid4()}"),
        ("patch", f"/materias/{uuid4()}"),
        ("delete", f"/materias/{uuid4()}"),
    ],
)
def test_rotas_de_materias_exigem_autenticacao(metodo, url):
    cliente_anonimo = APIClient()
    resposta = getattr(cliente_anonimo, metodo)(url)
    assert resposta.status_code == 401


# ------------------------------------------------------------------ Listagem e Criação


def test_listar_materias_vazio(cliente):
    resposta = cliente.get("/materias")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_criar_materia_sucesso(cliente, usuario):
    resposta = cliente.post(
        "/materias",
        {"nome": "Cálculo I", "cor": "#8B7BFF"},
        format="json",
    )

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["nome"] == "Cálculo I"
    assert dados["cor"] == "#8B7BFF"
    assert "id" in dados
    assert "criada_em" in dados

    assert MateriaModel.objects.filter(id=dados["id"], usuario=usuario).exists()


def test_criar_materia_normaliza_cor_para_maiuscula(cliente):
    resposta = cliente.post(
        "/materias",
        {"nome": "POO", "cor": "#3ee6e0"},
        format="json",
    )
    assert resposta.status_code == 201
    assert resposta.json()["cor"] == "#3EE6E0"


@pytest.mark.parametrize("nome", ["", "   ", None, "a" * 101])
def test_criar_materia_recusa_nome_invalido(cliente, nome):
    resposta = cliente.post(
        "/materias",
        {"nome": nome, "cor": "#8B7BFF"},
        format="json",
    )
    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "nome_invalido"


@pytest.mark.parametrize("cor", ["", "   ", None, "#123", "azul", "#GGGGGG", "8B7BFF"])
def test_criar_materia_recusa_cor_invalida(cliente, cor):
    resposta = cliente.post(
        "/materias",
        {"nome": "Cálculo", "cor": cor},
        format="json",
    )
    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "cor_invalido"



def test_criar_materia_recusa_nome_duplicado_para_mesmo_estudante(cliente):
    cliente.post("/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json")

    resposta = cliente.post(
        "/materias",
        {"nome": "cálculo", "cor": "#3EE6E0"},
        format="json",
    )
    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "materia_ja_existe"


def test_permite_mesmo_nome_para_estudantes_diferentes(cliente, outro_cliente):
    r1 = cliente.post("/materias", {"nome": "POO", "cor": "#3EE6E0"}, format="json")
    r2 = outro_cliente.post(
        "/materias", {"nome": "POO", "cor": "#8B7BFF"}, format="json"
    )

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


def test_listar_materias_do_estudante(cliente, outro_cliente):
    cliente.post("/materias", {"nome": "POO", "cor": "#3EE6E0"}, format="json")
    cliente.post("/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json")
    outro_cliente.post("/materias", {"nome": "Física", "cor": "#5BE49B"}, format="json")

    resposta = cliente.get("/materias")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados) == 2
    assert [m["nome"] for m in dados] == ["Cálculo", "POO"]


# ----------------------------------------------- Detalhes, Atualização e Exclusão



def test_buscar_materia_por_id_sucesso(cliente):
    criada = cliente.post(
        "/materias", {"nome": "POO", "cor": "#3EE6E0"}, format="json"
    ).json()

    resposta = cliente.get(f"/materias/{criada['id']}")
    assert resposta.status_code == 200
    assert resposta.json() == criada


def test_buscar_materia_inexistente_retorna_404(cliente):
    resposta = cliente.get(f"/materias/{uuid4()}")
    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


def test_buscar_materia_de_outro_estudante_retorna_404(cliente, outro_cliente):
    materia_outro = outro_cliente.post(
        "/materias", {"nome": "Segurança", "cor": "#FFC857"}, format="json"
    ).json()

    resposta = cliente.get(f"/materias/{materia_outro['id']}")
    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


def test_atualizar_materia_sucesso(cliente):
    materia = cliente.post(
        "/materias", {"nome": "Cálculo I", "cor": "#8B7BFF"}, format="json"
    ).json()

    resposta = cliente.patch(
        f"/materias/{materia['id']}",
        {"nome": "Cálculo Avançado", "cor": "#3EE6E0"},
        format="json",
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["nome"] == "Cálculo Avançado"
    assert dados["cor"] == "#3EE6E0"


def test_atualizar_materia_recusa_nome_duplicado(cliente):
    cliente.post("/materias", {"nome": "POO", "cor": "#3EE6E0"}, format="json")
    calculo = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json"
    ).json()

    resposta = cliente.patch(
        f"/materias/{calculo['id']}",
        {"nome": "poo"},
        format="json",
    )
    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "materia_ja_existe"


def test_atualizar_materia_de_outro_estudante_retorna_404(cliente, outro_cliente):
    materia_outro = outro_cliente.post(
        "/materias", {"nome": "Algoritmos", "cor": "#FFC857"}, format="json"
    ).json()

    resposta = cliente.patch(
        f"/materias/{materia_outro['id']}",
        {"nome": "Novo Nome"},
        format="json",
    )
    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


def test_remover_materia_sucesso(cliente):
    materia = cliente.post(
        "/materias", {"nome": "POO", "cor": "#3EE6E0"}, format="json"
    ).json()

    resposta = cliente.delete(f"/materias/{materia['id']}")
    assert resposta.status_code == 204

    resposta_get = cliente.get(f"/materias/{materia['id']}")
    assert resposta_get.status_code == 404


def test_remover_materia_de_outro_estudante_retorna_404(cliente, outro_cliente):
    materia_outro = outro_cliente.post(
        "/materias", {"nome": "Sistemas", "cor": "#FF6FB5"}, format="json"
    ).json()

    resposta = cliente.delete(f"/materias/{materia_outro['id']}")
    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


# ------------------------------------------------------------------ Swagger / OpenAPI


def test_swagger_inclui_endpoints_de_materias(cliente):
    resposta = cliente.get("/schema/", HTTP_ACCEPT="application/json")
    assert resposta.status_code == 200
    schema = resposta.json()

    assert "/materias" in schema["paths"]
    assert "/materias/{materia_id}" in schema["paths"]
    assert "get" in schema["paths"]["/materias"]
    assert "post" in schema["paths"]["/materias"]
    assert "get" in schema["paths"]["/materias/{materia_id}"]
    assert "patch" in schema["paths"]["/materias/{materia_id}"]
    assert "delete" in schema["paths"]["/materias/{materia_id}"]
