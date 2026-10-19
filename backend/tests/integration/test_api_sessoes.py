from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sessao_foco import InterrupcaoModel, SessaoFocoModel
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


def _cliente(email: str) -> APIClient:
    usuario = UsuarioModel.objects.create_user(email=email, nome="Estudante")
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente


@pytest.fixture
def cliente(relogio):
    return _cliente("julia@synapse.com")


def _iniciar(cliente, duracao=25, modo="estrito"):
    resposta = cliente.post(
        "/sessoes", {"duracao_minutos": duracao, "modo": modo}, format="json"
    )
    assert resposta.status_code == 201, resposta.json()
    return resposta.json()


def _iso(instante: datetime) -> str:
    return instante.isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------------ iniciar


def test_inicia_sessao(cliente):
    sessao = _iniciar(cliente, duracao=25, modo="tolerante")

    assert sessao["estado"] == "em_andamento"
    assert sessao["modo"] == "tolerante"
    assert sessao["inicio"] == INICIO.isoformat()
    assert sessao["restante_segundos"] == 25 * 60
    assert SessaoFocoModel.objects.get(id=sessao["id"]).modo == "tolerante"


def test_segunda_sessao_simultanea_retorna_409(cliente):
    _iniciar(cliente)

    resposta = cliente.post("/sessoes", {"duracao_minutos": 25}, format="json")

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "sessao_ativa_existente"


@pytest.mark.parametrize(
    ("corpo", "erro"),
    [
        ({"duracao_minutos": 7}, "duracao_invalida"),
        ({"duracao_minutos": 25, "modo": "relaxado"}, "modo_invalido"),
        ({}, "duracao_minutos_invalido"),
    ],
)
def test_recusa_dados_invalidos_ao_iniciar(cliente, corpo, erro):
    resposta = cliente.post("/sessoes", corpo, format="json")

    assert resposta.status_code == 400
    assert resposta.json()["erro"] == erro


def test_exige_autenticacao():
    assert APIClient().post("/sessoes", {"duracao_minutos": 25}).status_code == 401
    assert APIClient().get("/sessoes/ativa").status_code == 401


# ------------------------------------------------------------------ ativa


def test_sem_sessao_ativa_retorna_204(cliente):
    assert cliente.get("/sessoes/ativa").status_code == 204


def test_sessao_ativa_com_tempo_restante_calculado_no_servidor(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=10)

    resposta = cliente.get("/sessoes/ativa")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == sessao["id"]
    assert resposta.json()["restante_segundos"] == 15 * 60


# ------------------------------------------------------------------ concluir


def test_criterio_de_aceite_concluir_antes_da_hora_retorna_409(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=20)

    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "transicao_invalida"
    assert SessaoFocoModel.objects.get(id=sessao["id"]).estado == "em_andamento"


def test_concluir_no_tempo_cria_o_neuronio(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=25, seconds=-1)  # dentro da tolerância de 2 s

    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["sessao"]["estado"] == "concluida"
    assert dados["neuronio"]["sessao_id"] == sessao["id"]
    neuronio = NeuronioModel.objects.get(sessao_id=sessao["id"])
    assert str(neuronio.id) == dados["neuronio"]["id"]
    assert neuronio.duracao_minutos == 25


# ------------------------------------------------------------------ interrupções


def test_interrupcao_no_modo_estrito_poda(cliente, relogio):
    sessao = _iniciar(cliente, modo="estrito")
    relogio.avancar(minutes=6)

    resposta = cliente.post(
        f"/sessoes/{sessao['id']}/interrupcoes",
        {"inicio": _iso(INICIO + timedelta(minutes=5))},
        format="json",
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "podada"
    assert (
        resposta.json()["encerrada_em"] == (INICIO + timedelta(minutes=5)).isoformat()
    )


def test_interrupcoes_no_tolerante_somam_entre_requisicoes(cliente, relogio):
    # 10 min: saldo de 60 s. O histórico precisa sobreviver entre as requisições.
    sessao = _iniciar(cliente, duracao=10, modo="tolerante")
    url = f"/sessoes/{sessao['id']}/interrupcoes"
    relogio.avancar(minutes=5)

    primeira = cliente.post(
        url,
        {
            "inicio": _iso(INICIO + timedelta(minutes=1)),
            "fim": _iso(INICIO + timedelta(minutes=1, seconds=40)),
        },
        format="json",
    )
    assert primeira.json()["estado"] == "em_andamento"
    assert primeira.json()["tempo_fora_segundos"] == 40
    assert InterrupcaoModel.objects.filter(sessao_id=sessao["id"]).count() == 1

    segunda = cliente.post(
        url,
        {
            "inicio": _iso(INICIO + timedelta(minutes=3)),
            "fim": _iso(INICIO + timedelta(minutes=3, seconds=30)),
        },
        format="json",
    )
    assert segunda.json()["estado"] == "podada"
    # 20 s de saldo restante a partir dos 3 min.
    assert (
        segunda.json()["encerrada_em"]
        == (INICIO + timedelta(minutes=3, seconds=20)).isoformat()
    )


def test_reenviar_a_mesma_interrupcao_nao_desconta_o_saldo_de_novo(cliente, relogio):
    # O app reenvia quando a rede falha; a mesma saída não pode contar duas vezes.
    sessao = _iniciar(cliente, duracao=10, modo="tolerante")
    url = f"/sessoes/{sessao['id']}/interrupcoes"
    relogio.avancar(minutes=5)
    corpo = {
        "inicio": _iso(INICIO + timedelta(minutes=1)),
        "fim": _iso(INICIO + timedelta(minutes=1, seconds=40)),
    }

    cliente.post(url, corpo, format="json")
    resposta = cliente.post(url, corpo, format="json")

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "em_andamento"
    assert resposta.json()["tempo_fora_segundos"] == 40
    assert InterrupcaoModel.objects.filter(sessao_id=sessao["id"]).count() == 1


def test_interrupcao_sem_inicio_e_recusada(cliente):
    sessao = _iniciar(cliente)

    resposta = cliente.post(f"/sessoes/{sessao['id']}/interrupcoes", {}, format="json")

    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "inicio_invalido"


# ------------------------------------------------------------------ desistir


def test_desistir_conta_como_poda(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=3)

    resposta = cliente.post(f"/sessoes/{sessao['id']}/desistir")

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "podada"
    assert not NeuronioModel.objects.filter(sessao_id=sessao["id"]).exists()


# ------------------------------------------------------------------ outro usuário


@pytest.mark.parametrize("acao", ["concluir", "desistir", "interrupcoes"])
def test_criterio_de_aceite_sessao_de_outro_usuario_retorna_404(cliente, relogio, acao):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=30)
    intrusa = _cliente("intrusa@synapse.com")

    resposta = intrusa.post(
        f"/sessoes/{sessao['id']}/{acao}",
        {"inicio": _iso(INICIO + timedelta(minutes=1))},
        format="json",
    )

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "sessao_nao_encontrada"
    assert SessaoFocoModel.objects.get(id=sessao["id"]).estado == "em_andamento"


# ------------------------------------------------------------------ órfãs


def test_sessao_abandonada_e_podada_ao_ser_acessada(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=31)

    assert cliente.get("/sessoes/ativa").status_code == 204
    model = SessaoFocoModel.objects.get(id=sessao["id"])
    assert model.estado == "podada"
    assert model.encerrada_em == INICIO + timedelta(minutes=30)


def test_concluir_sessao_abandonada_retorna_409_e_mantem_a_poda(cliente, relogio):
    sessao = _iniciar(cliente)
    relogio.avancar(hours=2)

    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")

    assert resposta.status_code == 409
    assert SessaoFocoModel.objects.get(id=sessao["id"]).estado == "podada"


def test_comando_podar_sessoes_orfas(cliente, relogio):
    sessao = _iniciar(cliente, duracao=10)
    # O comando usa o relógio real: a sessão começou bem antes disso.
    SessaoFocoModel.objects.filter(id=sessao["id"]).update(
        inicio=datetime.now(UTC) - timedelta(hours=1)
    )

    call_command("podar_sessoes_orfas")

    assert SessaoFocoModel.objects.get(id=sessao["id"]).estado == "podada"
