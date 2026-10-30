from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import Concluida, SessaoFoco
from app.infra.modelos.conquista import ConquistaModel
from app.infra.modelos.usuario import UsuarioModel
from app.infra.repositorios import RepositorioRedeNeuralDjango, RepositorioSessaoDjango

pytestmark = pytest.mark.django_db

# 14h em Brasília.
INICIO = datetime(2026, 10, 20, 17, 0, tzinfo=UTC)

CODIGOS = [
    "primeiro_neuronio",
    "neuronios_5",
    "sessao_sem_poda_30",
    "horas_focadas_1",
    "dias_seguidos_3",
    "sinapses_5",
    "horas_focadas_10",
    "dias_seguidos_7",
    "sinapses_100",
    "sessao_sem_poda_120",
]


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
    monkeypatch.setattr("app.api.conquistas.agora", relogio)
    return relogio


def _cliente(email: str) -> APIClient:
    usuario = UsuarioModel.objects.create_user(email=email, nome="Estudante")
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    cliente.usuario = usuario
    return cliente


@pytest.fixture
def cliente(relogio):
    return _cliente("conquistas@synapse.com")


def _concluir(cliente, relogio, duracao=25) -> dict:
    sessao = cliente.post(
        "/sessoes", {"duracao_minutos": duracao}, format="json"
    ).json()
    relogio.avancar(minutes=duracao)
    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["sessao"]


def _por_codigo(corpo: dict) -> dict[str, dict]:
    return {c["codigo"]: c for c in corpo["conquistas"]}


# ------------------------------------------------------------------ formato


def test_exige_autenticacao():
    resposta = APIClient().get("/conquistas")

    assert resposta.status_code == 401
    assert resposta.json()["erro"] == "nao_autenticado"


def test_criterio_estudante_novo_ve_todas_as_conquistas_bloqueadas(cliente):
    resposta = cliente.get("/conquistas")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["sequencia"] == {"atual": 0, "recorde": 0}
    assert corpo["desbloqueadas"] == 0
    assert corpo["total"] == 10
    assert [c["codigo"] for c in corpo["conquistas"]] == CODIGOS
    assert corpo["conquistas"][7] == {
        "codigo": "dias_seguidos_7",
        "nome": "7 dias seguidos",
        "descricao": "Conclua pelo menos uma sessão por dia, 7 dias seguidos.",
        "desbloqueada": False,
        "desbloqueada_em": None,
        "progresso": 0,
        "meta": 7,
        "unidade": "dias",
    }


# ------------------------------------------------------------------ desbloqueio


def test_criterio_concluir_a_primeira_sessao_desbloqueia_o_primeiro_neuronio(
    cliente, relogio
):
    sessao = _concluir(cliente, relogio)

    # Desbloqueada ao concluir, pelo observador, e não só ao consultar.
    assert list(
        ConquistaModel.objects.filter(usuario=cliente.usuario).values_list(
            "codigo", flat=True
        )
    ) == ["primeiro_neuronio"]

    corpo = cliente.get("/conquistas").json()

    primeira = _por_codigo(corpo)["primeiro_neuronio"]
    assert primeira["desbloqueada"] is True
    # O instante da conclusão: a tela de sucesso sabe o que a sessão desbloqueou.
    assert primeira["desbloqueada_em"] == sessao["encerrada_em"]
    assert primeira["progresso"] == 1
    assert corpo["desbloqueadas"] == 1
    assert corpo["sequencia"] == {"atual": 1, "recorde": 1}


def test_sessao_podada_nao_desbloqueia_nada(cliente, relogio):
    sessao = cliente.post("/sessoes", {"duracao_minutos": 120}, format="json").json()
    relogio.avancar(minutes=110)
    cliente.post(f"/sessoes/{sessao['id']}/desistir")

    corpo = cliente.get("/conquistas").json()

    assert corpo["desbloqueadas"] == 0
    assert _por_codigo(corpo)["sessao_sem_poda_120"]["progresso"] == 0


def test_criterio_sessao_de_duas_horas_sem_poda(cliente, relogio):
    _concluir(cliente, relogio, duracao=115)
    assert not _por_codigo(cliente.get("/conquistas").json())["sessao_sem_poda_120"][
        "desbloqueada"
    ]

    _concluir(cliente, relogio, duracao=120)

    conquista = _por_codigo(cliente.get("/conquistas").json())["sessao_sem_poda_120"]
    assert conquista["desbloqueada"] is True
    assert conquista["progresso"] == 120


def test_criterio_dez_horas_focadas(cliente, relogio):
    for _ in range(5):
        _concluir(cliente, relogio, duracao=120)

    conquista = _por_codigo(cliente.get("/conquistas").json())["horas_focadas_10"]

    assert conquista["desbloqueada"] is True
    assert conquista["progresso"] == conquista["meta"] == 600


def test_criterio_sete_dias_seguidos_e_a_sequencia(cliente, relogio):
    for dia in range(7):
        _concluir(cliente, relogio)
        relogio.avancar(days=1)
        corpo = cliente.get("/conquistas").json()
        # No dia seguinte, antes da próxima sessão, a sequência ainda vale.
        assert corpo["sequencia"] == {"atual": dia + 1, "recorde": dia + 1}

    assert _por_codigo(corpo)["dias_seguidos_7"]["desbloqueada"] is True

    # Um dia inteiro sem sessão: a sequência zera, a conquista e o recorde ficam.
    relogio.avancar(days=1)
    corpo = cliente.get("/conquistas").json()
    assert corpo["sequencia"] == {"atual": 0, "recorde": 7}
    assert _por_codigo(corpo)["dias_seguidos_7"]["desbloqueada"] is True


def test_os_dias_sao_os_de_brasilia(cliente, relogio):
    # Sessões concluídas às 10h e às 22h do dia 20 em Brasília. Em UTC, a segunda
    # já seria do dia 21, e contaria como dois dias seguidos.
    relogio.instante = datetime(2026, 10, 20, 12, 35, tzinfo=UTC)
    _concluir(cliente, relogio)
    relogio.instante = datetime(2026, 10, 21, 0, 35, tzinfo=UTC)
    _concluir(cliente, relogio)

    assert cliente.get("/conquistas").json()["sequencia"] == {
        "atual": 1,
        "recorde": 1,
    }


def test_conquistas_de_um_estudante_nao_aparecem_para_outro(cliente, relogio):
    _concluir(cliente, relogio)
    outro = _cliente("outro@synapse.com")

    assert outro.get("/conquistas").json()["desbloqueadas"] == 0


def test_quem_ja_focava_antes_encontra_as_conquistas_desbloqueadas(cliente, relogio):
    # Sessão e neurônio de antes de as conquistas existirem: nada foi avaliado.
    sessao = SessaoFoco(
        cliente.usuario.id, 120, inicio=INICIO - timedelta(days=30), estado=Concluida()
    )
    RepositorioSessaoDjango().salvar(sessao)
    redes = RepositorioRedeNeuralDjango()
    rede = redes.carregar(cliente.usuario.id)
    rede.adicionar(
        Neuronio(
            cliente.usuario.id,
            sessao.id,
            120,
            criado_em=INICIO - timedelta(days=30) + timedelta(minutes=120),
        )
    )
    redes.salvar(rede)

    corpo = cliente.get("/conquistas").json()

    conquistas = _por_codigo(corpo)
    assert conquistas["primeiro_neuronio"]["desbloqueada"] is True
    assert conquistas["sessao_sem_poda_120"]["desbloqueada"] is True
    assert conquistas["primeiro_neuronio"]["desbloqueada_em"] == INICIO.isoformat()


def test_cada_conquista_e_desbloqueada_uma_vez(cliente, relogio):
    _concluir(cliente, relogio)
    _concluir(cliente, relogio)
    cliente.get("/conquistas")

    assert ConquistaModel.objects.filter(usuario=cliente.usuario).count() == 1


def test_consulta_em_poucas_consultas_ao_banco(
    cliente, relogio, django_assert_max_num_queries
):
    for _ in range(10):
        _concluir(cliente, relogio, duracao=10)

    # Neurônios, sinapses e conquistas, mais o SAVEPOINT e o RELEASE da transação.
    with django_assert_max_num_queries(5):
        resposta = cliente.get("/conquistas")

    assert resposta.json()["desbloqueadas"] == 4


def test_swagger_documenta_as_conquistas(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    operacao = schema["paths"]["/conquistas"]["get"]
    assert operacao["tags"] == ["Conquistas"]
    assert operacao["responses"]["200"]["content"]["application/json"]["examples"]
    componentes = schema["components"]["schemas"]
    assert set(componentes["ConquistasResposta"]["properties"]) == {
        "sequencia",
        "desbloqueadas",
        "total",
        "conquistas",
    }
    assert set(componentes["Conquista"]["properties"]) == {
        "codigo",
        "nome",
        "descricao",
        "desbloqueada",
        "desbloqueada_em",
        "progresso",
        "meta",
        "unidade",
    }
