from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db

INICIO = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


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
    return _cliente("historico@synapse.com")


def _iniciar(cliente, duracao=10, modo="estrito") -> dict:
    resposta = cliente.post(
        "/sessoes", {"duracao_minutos": duracao, "modo": modo}, format="json"
    )
    assert resposta.status_code == 201, resposta.json()
    return resposta.json()


def _concluida(cliente, relogio, duracao=10) -> str:
    sessao = _iniciar(cliente, duracao)
    relogio.avancar(minutes=duracao)
    assert cliente.post(f"/sessoes/{sessao['id']}/concluir").status_code == 200
    relogio.avancar(hours=1)
    return sessao["id"]


def _desistida(cliente, relogio) -> str:
    sessao = _iniciar(cliente)
    relogio.avancar(minutes=5)
    assert cliente.post(f"/sessoes/{sessao['id']}/desistir").status_code == 200
    relogio.avancar(hours=1)
    return sessao["id"]


def _ids(resposta) -> list[str]:
    assert resposta.status_code == 200, resposta.json()
    return [s["id"] for s in resposta.json()["resultados"]]


# ------------------------------------------------------------------ formato


def test_exige_autenticacao():
    resposta = APIClient().get("/sessoes")

    assert resposta.status_code == 401
    assert resposta.json()["erro"] == "nao_autenticado"


def test_historico_vazio(cliente):
    resposta = cliente.get("/sessoes")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "total": 0,
        "pagina": 1,
        "tamanho": 20,
        "paginas": 1,
        "resultados": [],
    }


def test_criterio_lista_as_sessoes_com_data_duracao_materia_e_resultado(
    cliente, relogio
):
    materia = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json"
    ).json()
    com_materia = cliente.post(
        "/sessoes",
        {"duracao_minutos": 25, "materia_id": materia["id"]},
        format="json",
    ).json()
    relogio.avancar(minutes=25)
    cliente.post(f"/sessoes/{com_materia['id']}/concluir")
    relogio.avancar(hours=1)
    podada = _desistida(cliente, relogio)
    ativa = _iniciar(cliente, duracao=45, modo="tolerante")

    corpo = cliente.get("/sessoes").json()

    assert corpo["total"] == 3
    assert [s["id"] for s in corpo["resultados"]] == [
        ativa["id"],
        podada,
        com_materia["id"],
    ]
    mais_antiga = corpo["resultados"][2]
    assert mais_antiga["estado"] == "concluida"
    assert mais_antiga["duracao_minutos"] == 25
    assert mais_antiga["materia_id"] == materia["id"]
    assert mais_antiga["inicio"] == "2026-10-20T12:00:00+00:00"
    assert mais_antiga["encerrada_em"] == "2026-10-20T12:25:00+00:00"
    assert corpo["resultados"][1]["estado"] == "podada"
    assert corpo["resultados"][0]["estado"] == "em_andamento"
    # Mesmo formato do restante da API de sessões.
    assert set(mais_antiga) == set(ativa)


# ------------------------------------------------------------------ filtros


@pytest.mark.parametrize(
    ("status", "esperado"),
    [
        ("concluida", ["recente", "antiga"]),
        ("podada", ["podada"]),
        ("em_andamento", ["ativa"]),
    ],
)
def test_filtra_por_status(cliente, relogio, status, esperado):
    ids = {
        "antiga": _concluida(cliente, relogio),
        "podada": _desistida(cliente, relogio),
        "recente": _concluida(cliente, relogio),
        "ativa": _iniciar(cliente)["id"],
    }

    resposta = cliente.get("/sessoes", {"status": status})

    assert _ids(resposta) == [ids[nome] for nome in esperado]
    assert resposta.json()["total"] == len(esperado)


def test_filtra_por_periodo_pelo_inicio_da_sessao(cliente, relogio):
    dia_20 = _concluida(cliente, relogio)
    relogio.instante = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    dia_21 = _concluida(cliente, relogio)
    relogio.instante = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    dia_22 = _concluida(cliente, relogio)

    assert _ids(cliente.get("/sessoes", {"de": "2026-10-21", "ate": "2026-10-21"})) == [
        dia_21
    ]
    assert _ids(cliente.get("/sessoes", {"de": "2026-10-21"})) == [dia_22, dia_21]
    assert _ids(cliente.get("/sessoes", {"ate": "2026-10-20"})) == [dia_20]
    # Data e hora com fuso: 21/10 às 08:00 em Brasília é 11:00 em UTC.
    assert _ids(
        cliente.get(
            "/sessoes",
            {"de": "2026-10-21T08:00:00-03:00", "ate": "2026-10-21T10:00:00-03:00"},
        )
    ) == [dia_21]


def test_filtros_combinados(cliente, relogio):
    _concluida(cliente, relogio)
    relogio.instante = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
    podada_recente = _desistida(cliente, relogio)
    _concluida(cliente, relogio)

    resposta = cliente.get("/sessoes", {"de": "2026-10-25", "status": "podada"})

    assert _ids(resposta) == [podada_recente]


# ------------------------------------------------------------------ paginação


def test_criterio_paginado(cliente, relogio):
    ids = [_concluida(cliente, relogio) for _ in range(5)]

    primeira = cliente.get("/sessoes", {"tamanho": 2})
    segunda = cliente.get("/sessoes", {"tamanho": 2, "pagina": 2})
    ultima = cliente.get("/sessoes", {"tamanho": 2, "pagina": 3})
    depois = cliente.get("/sessoes", {"tamanho": 2, "pagina": 4})

    assert _ids(primeira) == [ids[4], ids[3]]
    assert _ids(segunda) == [ids[2], ids[1]]
    assert _ids(ultima) == [ids[0]]
    assert _ids(depois) == []
    assert {
        k: segunda.json()[k] for k in ("total", "pagina", "tamanho", "paginas")
    } == {
        "total": 5,
        "pagina": 2,
        "tamanho": 2,
        "paginas": 3,
    }


def test_carrega_cada_pagina_em_poucas_consultas(
    cliente, relogio, django_assert_max_num_queries
):
    # Sessões com interrupções: sem o prefetch, seria uma consulta a mais por sessão.
    for _ in range(15):
        sessao = _iniciar(cliente, modo="tolerante")
        relogio.avancar(minutes=2)
        saida = relogio.instante - timedelta(minutes=1)
        cliente.post(
            f"/sessoes/{sessao['id']}/interrupcoes",
            {
                "inicio": saida.isoformat(),
                "fim": (saida + timedelta(seconds=10)).isoformat(),
            },
            format="json",
        )
        relogio.avancar(minutes=8)
        cliente.post(f"/sessoes/{sessao['id']}/concluir")
        relogio.avancar(hours=1)

    # Sessão ativa, contagem, página e interrupções, mais o SAVEPOINT e o RELEASE da
    # transação: 6, com 15 sessões ou com 1500 (sem o prefetch, seriam 21 aqui).
    with django_assert_max_num_queries(6):
        resposta = cliente.get("/sessoes")

    assert len(resposta.json()["resultados"]) == 15
    assert all(s["tempo_fora_segundos"] == 10 for s in resposta.json()["resultados"])


# ------------------------------------------------------------------ regras


def test_cada_estudante_ve_so_as_suas_sessoes(cliente, relogio):
    outro = _cliente("outro@synapse.com")
    _concluida(outro, relogio)
    minha = _concluida(cliente, relogio)

    assert _ids(cliente.get("/sessoes")) == [minha]


def test_sessao_abandonada_aparece_como_podada(cliente, relogio):
    abandonada = _iniciar(cliente)
    relogio.avancar(minutes=20)

    corpo = cliente.get("/sessoes").json()

    assert corpo["resultados"][0]["id"] == abandonada["id"]
    assert corpo["resultados"][0]["estado"] == "podada"


@pytest.mark.parametrize(
    ("filtros", "campo"),
    [
        ({"status": "pausada"}, "status"),
        ({"pagina": 0}, "pagina"),
        ({"tamanho": 101}, "tamanho"),
        ({"tamanho": "muitos"}, "tamanho"),
        ({"de": "ontem"}, "de"),
        ({"de": "2026-10-25", "ate": "2026-10-20"}, "ate"),
    ],
)
def test_recusa_filtro_invalido(cliente, filtros, campo):
    resposta = cliente.get("/sessoes", filtros)

    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "validacao"
    assert campo in resposta.json()["detalhes"]


def test_iniciar_sessao_continua_no_mesmo_endereco(cliente):
    resposta = cliente.post("/sessoes", {"duracao_minutos": 25}, format="json")

    assert resposta.status_code == 201
    assert resposta.json()["estado"] == "em_andamento"


def test_swagger_documenta_o_historico_e_o_inicio_da_sessao(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    caminho = schema["paths"]["/sessoes"]
    assert {p["name"] for p in caminho["get"]["parameters"]} == {
        "de",
        "ate",
        "status",
        "pagina",
        "tamanho",
    }
    assert caminho["get"]["responses"]["200"]["content"]["application/json"]["examples"]
    assert "201" in caminho["post"]["responses"]
    resposta = schema["components"]["schemas"]["HistoricoResposta"]["properties"]
    assert set(resposta) == {"total", "pagina", "tamanho", "paginas", "resultados"}
