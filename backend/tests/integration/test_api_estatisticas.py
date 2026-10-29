from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from app.domain.conquistas import FUSO_DOS_DIAS
from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db

# 20/10/2026 às 10h00 em Brasília (13h00 UTC).
INICIO = datetime(2026, 10, 20, 13, 0, tzinfo=UTC)


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
    monkeypatch.setattr("app.api.estatisticas.agora", relogio)
    return relogio


def _cliente(email: str) -> APIClient:
    usuario = UsuarioModel.objects.create_user(email=email, nome="Estudante")
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    cliente.usuario = usuario
    return cliente


@pytest.fixture
def cliente(relogio):
    return _cliente("estatisticas@synapse.com")


def _criar_materia(cliente: APIClient, nome: str, cor: str) -> dict:
    resposta = cliente.post("/materias", {"nome": nome, "cor": cor}, format="json")
    assert resposta.status_code == 201, resposta.json()
    return resposta.json()


def _concluir(
    cliente: APIClient,
    relogio: Relogio,
    duracao: int = 25,
    materia_id: str | None = None,
) -> dict:
    dados: dict = {"duracao_minutos": duracao}
    if materia_id is not None:
        dados["materia_id"] = materia_id
    sessao = cliente.post("/sessoes", dados, format="json").json()
    relogio.avancar(minutes=duracao)
    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["sessao"]


def _desistir(
    cliente: APIClient,
    relogio: Relogio,
    duracao: int = 25,
    apos_minutos: int = 5,
    materia_id: str | None = None,
) -> dict:
    dados: dict = {"duracao_minutos": duracao}
    if materia_id is not None:
        dados["materia_id"] = materia_id
    sessao = cliente.post("/sessoes", dados, format="json").json()
    relogio.avancar(minutes=apos_minutos)
    resposta = cliente.post(f"/sessoes/{sessao['id']}/desistir")
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()


# --------------------------------------------------------- formato e autenticação


def test_exige_autenticacao():
    resposta = APIClient().get("/estatisticas")

    assert resposta.status_code == 401
    assert resposta.json()["erro"] == "nao_autenticado"


def test_estudante_novo_recebe_estatisticas_zeradas_na_semana_por_padrao(cliente):
    resposta = cliente.get("/estatisticas")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["periodo"] == "semana"
    assert corpo["inicio"] == "2026-10-14"
    assert corpo["fim"] == "2026-10-20"
    assert corpo["tempo_total_minutos"] == 0
    assert corpo["sessoes_concluidas"] == 0
    assert corpo["sessoes_podadas"] == 0
    assert corpo["total_sessoes"] == 0
    assert corpo["taxa_sucesso"] == 0.0
    assert corpo["melhor_horario"] is None
    assert corpo["por_materia"] == []
    assert len(corpo["por_dia"]) == 7
    assert all(d["minutos"] == 0 and d["por_materia"] == [] for d in corpo["por_dia"])


@pytest.mark.parametrize("invalido", ["ano", "hoje", "7", ""])
def test_periodo_invalido_retorna_400_com_detalhes(cliente, invalido):
    resposta = cliente.get(f"/estatisticas?periodo={invalido}")

    assert resposta.status_code == 400
    corpo = resposta.json()
    assert corpo["erro"] == "validacao"
    assert "periodo" in corpo["detalhes"]


# ----------------------------------------------------- cálculos nos três períodos


def test_estatisticas_por_dia_semana_e_mes_pelo_fluxo_real(cliente, relogio):
    calculo = _criar_materia(cliente, "Cálculo", "#8B7BFF")
    poo = _criar_materia(cliente, "POO", "#3EE6E0")

    # Há 15 dias (dentro do mês, fora da semana): 05/10/2026 às 09h em Brasília
    relogio.instante = datetime(2026, 10, 5, 9, 0, tzinfo=FUSO_DOS_DIAS)
    _concluir(cliente, relogio, duracao=60, materia_id=poo["id"])

    # Ontem (dentro da semana, fora do dia): 19/10/2026 às 19h em Brasília
    relogio.instante = datetime(2026, 10, 19, 19, 0, tzinfo=FUSO_DOS_DIAS)
    _concluir(cliente, relogio, duracao=40, materia_id=calculo["id"])

    # Hoje (20/10/2026): duas concluídas às 19h e uma podada às 21h em Brasília
    relogio.instante = datetime(2026, 10, 20, 19, 0, tzinfo=FUSO_DOS_DIAS)
    _concluir(cliente, relogio, duracao=25, materia_id=calculo["id"])
    _concluir(cliente, relogio, duracao=20, materia_id=None)
    relogio.instante = datetime(2026, 10, 20, 21, 0, tzinfo=FUSO_DOS_DIAS)
    _desistir(cliente, relogio, duracao=30, apos_minutos=10, materia_id=poo["id"])

    # --- Período: dia ---
    dia = cliente.get("/estatisticas?periodo=dia").json()
    assert dia["periodo"] == "dia"
    assert len(dia["por_dia"]) == 1
    assert dia["tempo_total_minutos"] == 45
    assert dia["sessoes_concluidas"] == 2
    assert dia["sessoes_podadas"] == 1
    assert dia["total_sessoes"] == 3
    assert dia["taxa_sucesso"] == 0.6667
    assert dia["melhor_horario"] == 19
    assert dia["por_dia"][0] == {
        "data": "2026-10-20",
        "minutos": 45,
        "por_materia": [
            {"materia_id": calculo["id"], "minutos": 25},
            {"materia_id": None, "minutos": 20},
        ],
    }

    # --- Período: semana ---
    semana = cliente.get("/estatisticas?periodo=semana").json()
    assert semana["periodo"] == "semana"
    assert len(semana["por_dia"]) == 7
    assert semana["tempo_total_minutos"] == 85
    assert semana["sessoes_concluidas"] == 3
    assert semana["sessoes_podadas"] == 1
    assert semana["total_sessoes"] == 4
    assert semana["taxa_sucesso"] == 0.75
    assert semana["melhor_horario"] == 19
    assert semana["por_materia"] == [
        {
            "materia_id": calculo["id"],
            "nome": "Cálculo",
            "cor": "#8B7BFF",
            "efeito": None,
            "minutos": 65,
            "percentual": 0.7647,
        },
        {
            "materia_id": None,
            "nome": None,
            "cor": None,
            "efeito": None,
            "minutos": 20,
            "percentual": 0.2353,
        },
    ]

    # --- Período: mês ---
    mes = cliente.get("/estatisticas?periodo=mes").json()
    assert mes["periodo"] == "mes"
    assert len(mes["por_dia"]) == 30
    assert mes["tempo_total_minutos"] == 145
    assert mes["sessoes_concluidas"] == 4
    assert mes["sessoes_podadas"] == 1
    assert mes["total_sessoes"] == 5
    assert mes["taxa_sucesso"] == 0.8
    # Às 19h foram 40 + 25 + 20 = 85 min; às 9h foram 60 min:
    assert mes["melhor_horario"] == 19
    assert [m["nome"] for m in mes["por_materia"]] == ["Cálculo", "POO", None]


def test_cor_da_loja_com_efeito_aparece_em_por_materia(cliente, relogio):
    # Ganha 500 ATP para comprar a cor Pulsar (#7DF9FF, efeito "pulsar"):
    for _ in range(5):
        _concluir(cliente, relogio, duracao=100)
    assert cliente.post("/loja/pulsar/comprar").status_code == 200

    neuro = _criar_materia(cliente, "Neurociência", "#7DF9FF")
    _concluir(cliente, relogio, duracao=30, materia_id=neuro["id"])

    corpo = cliente.get("/estatisticas?periodo=dia").json()
    por_id = {m["materia_id"]: m for m in corpo["por_materia"]}
    assert por_id[neuro["id"]]["cor"] == "#7DF9FF"
    assert por_id[neuro["id"]]["efeito"] == "pulsar"


def test_estatisticas_de_um_estudante_nao_aparecem_para_outro(cliente, relogio):
    _concluir(cliente, relogio, duracao=50)
    outro = _cliente("outro@synapse.com")

    corpo = outro.get("/estatisticas?periodo=dia").json()

    assert corpo["tempo_total_minutos"] == 0
    assert corpo["total_sessoes"] == 0


def test_sessao_abandonada_e_podada_ao_consultar_estatisticas(cliente, relogio):
    cliente.post("/sessoes", {"duracao_minutos": 20}, format="json")
    relogio.avancar(minutes=26)  # passou de 20 + 5 min

    corpo = cliente.get("/estatisticas?periodo=dia").json()

    assert corpo["sessoes_podadas"] == 1
    assert corpo["total_sessoes"] == 1
    assert corpo["taxa_sucesso"] == 0.0
    # E o neurônio morto também foi registrado na rede:
    neuronios = cliente.get("/rede").json()["neuronios"]
    assert len(neuronios) == 1
    assert neuronios[0]["vivo"] is False


def test_consulta_em_numero_constante_de_queries(
    cliente, relogio, django_assert_max_num_queries
):
    materia = _criar_materia(cliente, "POO", "#3EE6E0")
    for _ in range(12):
        sessao = cliente.post(
            "/sessoes",
            {"duracao_minutos": 20, "modo": "tolerante", "materia_id": materia["id"]},
            format="json",
        ).json()
        saida = relogio().isoformat()
        relogio.avancar(seconds=15)
        retorno = relogio().isoformat()
        cliente.post(
            f"/sessoes/{sessao['id']}/interrupcoes",
            {"inicio": saida, "fim": retorno},
            format="json",
        )
        relogio.avancar(minutes=20)
        assert cliente.post(f"/sessoes/{sessao['id']}/concluir").status_code == 200

    # SAVEPOINT + ativa + sessões + interrupções (prefetch) + matérias + RELEASE = 6.
    with django_assert_max_num_queries(6):
        resposta = cliente.get("/estatisticas?periodo=mes")

    assert resposta.status_code == 200
    assert resposta.json()["sessoes_concluidas"] == 12


def test_swagger_documenta_o_endpoint_de_estatisticas(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    operacao = schema["paths"]["/estatisticas"]["get"]
    assert operacao["tags"] == ["Estatísticas"]
    parametros = {p["name"]: p for p in operacao["parameters"]}
    assert set(parametros["periodo"]["schema"]["enum"]) == {"dia", "semana", "mes"}
    assert operacao["responses"]["200"]["content"]["application/json"]["examples"]
    componentes = schema["components"]["schemas"]
    assert set(componentes["EstatisticasResposta"]["properties"]) == {
        "periodo",
        "inicio",
        "fim",
        "tempo_total_minutos",
        "sessoes_concluidas",
        "sessoes_podadas",
        "total_sessoes",
        "taxa_sucesso",
        "melhor_horario",
        "por_dia",
        "por_materia",
    }
