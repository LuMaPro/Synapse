from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from app.infra.modelos.materia import MateriaModel
from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db

INICIO = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)


class Relogio:
    """Relógio do servidor controlado pelo teste."""

    def __init__(self):
        self.instante = INICIO

    def __call__(self) -> datetime:
        return self.instante

    def avancar(self, **delta) -> None:
        self.instante += timedelta(**delta)


@pytest.fixture
def relogio(monkeypatch):
    relogio = Relogio()
    monkeypatch.setattr("app.api.sessoes.agora", relogio)
    return relogio


def _cliente(email: str) -> tuple[APIClient, UsuarioModel]:
    usuario = UsuarioModel.objects.create_user(email=email, nome="Estudante")
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente, usuario


@pytest.fixture
def auth(relogio):
    return _cliente("julia@synapse.com")


@pytest.fixture
def cliente(auth):
    return auth[0]


@pytest.fixture
def usuario(auth):
    return auth[1]


@pytest.fixture
def materia(usuario):
    return MateriaModel.objects.create(
        usuario=usuario, nome="Cálculo I", cor="#8B7BFF"
    )


def test_iniciar_sessao_com_materia_associa_materia(cliente, materia):
    resposta = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia.id)},
        format="json",
    )

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["materia_id"] == str(materia.id)

    modelo = SessaoFocoModel.objects.get(id=dados["id"])
    assert modelo.materia_id == materia.id


def test_sessao_ativa_retorna_materia_id(cliente, materia):
    cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia.id)},
        format="json",
    )

    resposta = cliente.get("/sessoes/ativa")

    assert resposta.status_code == 200
    assert resposta.json()["materia_id"] == str(materia.id)


def test_iniciar_sessao_com_materia_inexistente_retorna_404(cliente):
    resposta = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(uuid4())},
        format="json",
    )

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


def test_iniciar_sessao_com_materia_de_outro_usuario_retorna_404(cliente):
    _outro_cliente, outro_usuario = _cliente("outro@synapse.com")
    materia_outro = MateriaModel.objects.create(
        usuario=outro_usuario, nome="Física", cor="#3EE6E0"
    )

    resposta = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia_outro.id)},
        format="json",
    )

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "materia_nao_encontrada"


def test_concluir_sessao_cria_neuronio_com_materia(cliente, materia, relogio):
    inicio_resp = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia.id)},
        format="json",
    )
    sessao_id = inicio_resp.json()["id"]

    relogio.avancar(minutes=25)
    resposta = cliente.post(f"/sessoes/{sessao_id}/concluir")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["sessao"]["materia_id"] == str(materia.id)
    assert dados["neuronio"]["materia_id"] == str(materia.id)

    neuronio = NeuronioModel.objects.get(sessao_id=sessao_id)
    assert neuronio.materia_id == materia.id


def test_desistir_sessao_cria_neuronio_podado_com_materia(cliente, materia, relogio):
    inicio_resp = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia.id)},
        format="json",
    )
    sessao_id = inicio_resp.json()["id"]
    relogio.avancar(minutes=5)

    resposta = cliente.post(f"/sessoes/{sessao_id}/desistir")

    assert resposta.status_code == 200
    neuronio = NeuronioModel.objects.get(sessao_id=sessao_id)
    assert neuronio.vivo is False
    assert neuronio.materia_id == materia.id


def test_deletar_materia_define_materia_id_como_null_em_sessoes_e_neuronios(
    cliente, materia, relogio
):
    inicio_resp = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": str(materia.id)},
        format="json",
    )
    sessao_id = inicio_resp.json()["id"]
    relogio.avancar(minutes=25)
    cliente.post(f"/sessoes/{sessao_id}/concluir")

    # Deleta a matéria através da API
    del_resp = cliente.delete(f"/materias/{materia.id}")
    assert del_resp.status_code == 204

    # A sessão permanece no banco, com matéria nula (ON DELETE SET NULL)
    sessao_banco = SessaoFocoModel.objects.get(id=sessao_id)
    assert sessao_banco.materia is None
    assert sessao_banco.materia_id is None

    # O neurônio gerado permanece no banco, com materia_id nulo
    neuronio_banco = NeuronioModel.objects.get(sessao_id=sessao_id)
    assert neuronio_banco.materia_id is None

    # A rede neural ainda pode ser consultada e lista o neurônio
    rede_resp = cliente.get("/rede")
    assert rede_resp.status_code == 200
    neuronios = rede_resp.json()["neuronios"]
    assert len(neuronios) == 1
    assert neuronios[0]["id"] == str(neuronio_banco.id)
    assert neuronios[0]["materia_id"] is None
