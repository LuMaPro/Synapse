import importlib
from datetime import UTC, datetime, timedelta

import pytest
from django.apps import apps
from rest_framework.test import APIClient

from app.infra.modelos.carteira import CarteiraModel, TipoDesbloqueadoModel
from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db

INICIO = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)


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
    monkeypatch.setattr("app.api.loja.agora", relogio)
    return relogio


def _cliente(email: str) -> APIClient:
    usuario = UsuarioModel.objects.create_user(email=email, nome="Estudante")
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    cliente.usuario = usuario
    return cliente


@pytest.fixture
def cliente(relogio):
    return _cliente("loja@synapse.com")


def _concluir(cliente, relogio, duracao=25, materia_id=None) -> dict:
    corpo = {"duracao_minutos": duracao}
    if materia_id:
        corpo["materia_id"] = materia_id
    sessao = cliente.post("/sessoes", corpo, format="json").json()
    relogio.avancar(minutes=duracao)
    resposta = cliente.post(f"/sessoes/{sessao['id']}/concluir")
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()


def _juntar_atp(cliente, relogio, quantia):
    """Conclui sessões de 2 h até juntar pelo menos `quantia` ATP."""
    for _ in range(10):
        if cliente.get("/loja").json()["saldo"] >= quantia:
            return
        _concluir(cliente, relogio, duracao=120)
    pytest.fail(f"10 sessões de 2 h não juntaram {quantia} ATP.")


def _tipo(corpo: dict, codigo: str) -> dict:
    return next(t for t in corpo["tipos"] if t["codigo"] == codigo)


# ------------------------------------------------------------------ loja


def test_exige_autenticacao():
    for metodo, caminho in [
        ("get", "/loja"),
        ("post", "/loja/piramidal_rosa/comprar"),
        ("post", "/loja/piramidal_rosa/usar"),
    ]:
        resposta = getattr(APIClient(), metodo)(caminho)
        assert resposta.status_code == 401
        assert resposta.json()["erro"] == "nao_autenticado"


def test_estudante_novo_ve_o_catalogo_com_saldo_zero(cliente):
    resposta = cliente.get("/loja")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo"] == 0
    assert [t["codigo"] for t in corpo["tipos"]] == [
        "granular",
        "granular_lima",
        "granular_esmeralda",
        "piramidal",
        "piramidal_rosa",
        "piramidal_safira",
        "purkinje",
        "purkinje_coral",
        "purkinje_lunar",
    ]
    assert _tipo(corpo, "piramidal_rosa") == {
        "codigo": "piramidal_rosa",
        "nome": "Piramidal Rosa",
        "forma": "piramidal",
        "cor": "#FF6FB5",
        "preco": 250,
        "duracao_minima": 25,
        "duracao_maxima": 59,
        "desbloqueado": False,
        "em_uso": False,
    }
    assert _tipo(corpo, "purkinje")["duracao_maxima"] is None
    assert _tipo(corpo, "purkinje")["em_uso"] is True
    assert _tipo(corpo, "purkinje")["desbloqueado"] is True


def test_criterio_sessao_concluida_rende_atp_proporcional_a_duracao(cliente, relogio):
    primeira = _concluir(cliente, relogio, duracao=45)
    segunda = _concluir(cliente, relogio, duracao=25)

    assert primeira["atp"] == 45
    assert segunda["atp"] == 25
    assert cliente.get("/loja").json()["saldo"] == 70


def test_sessao_podada_nao_rende_atp(cliente, relogio):
    sessao = cliente.post("/sessoes", {"duracao_minutos": 60}, format="json").json()
    relogio.avancar(minutes=50)
    cliente.post(f"/sessoes/{sessao['id']}/desistir")

    assert cliente.get("/loja").json()["saldo"] == 0


def test_criterio_comprar_valida_o_saldo(cliente, relogio):
    _concluir(cliente, relogio, duracao=120)

    resposta = cliente.post("/loja/piramidal_rosa/comprar")

    assert resposta.status_code == 409
    assert resposta.json() == {
        "erro": "saldo_insuficiente",
        "mensagem": "Faltam 130 ATP para comprar o Piramidal Rosa.",
    }
    assert cliente.get("/loja").json()["saldo"] == 120
    assert not TipoDesbloqueadoModel.objects.filter(usuario=cliente.usuario).exists()


def test_criterio_comprar_desconta_desbloqueia_e_passa_a_usar(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)  # 3 sessões de 2 h: 360 ATP

    resposta = cliente.post("/loja/piramidal_rosa/comprar")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo"] == 110
    assert _tipo(corpo, "piramidal_rosa")["desbloqueado"] is True
    assert _tipo(corpo, "piramidal_rosa")["em_uso"] is True
    assert _tipo(corpo, "piramidal")["em_uso"] is False
    assert cliente.get("/loja").json() == corpo


def test_nao_compra_duas_vezes(cliente, relogio):
    _juntar_atp(cliente, relogio, 500)
    cliente.post("/loja/piramidal_rosa/comprar")

    resposta = cliente.post("/loja/piramidal_rosa/comprar")

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "tipo_ja_desbloqueado"
    # 5 sessões de 2 h (600 ATP), uma compra só.
    assert cliente.get("/loja").json()["saldo"] == 600 - 250


def test_tipo_fora_da_loja(cliente):
    for acao in ("comprar", "usar"):
        resposta = cliente.post(f"/loja/unicornio/{acao}")
        assert resposta.status_code == 404
        assert resposta.json()["erro"] == "tipo_nao_encontrado"


def test_usar_tipo_nao_comprado(cliente):
    resposta = cliente.post("/loja/piramidal_rosa/usar")

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "tipo_bloqueado"


def test_usar_o_original_volta_ao_padrao(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)
    cliente.post("/loja/piramidal_rosa/comprar")

    corpo = cliente.post("/loja/piramidal/usar").json()

    assert _tipo(corpo, "piramidal")["em_uso"] is True
    assert _tipo(corpo, "piramidal_rosa")["em_uso"] is False
    assert _tipo(corpo, "piramidal_rosa")["desbloqueado"] is True
    # Voltar a usar a variação não cobra de novo.
    saldo = corpo["saldo"]
    assert cliente.post("/loja/piramidal_rosa/usar").json()["saldo"] == saldo


def test_carteiras_de_estudantes_diferentes_nao_se_misturam(cliente, relogio):
    _concluir(cliente, relogio, duracao=60)
    outro = _cliente("outro@synapse.com")

    assert outro.get("/loja").json()["saldo"] == 0


# ------------------------------------------------------------------ fábrica


def test_criterio_proximas_sessoes_usam_o_tipo_escolhido(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)
    antes = _concluir(cliente, relogio, duracao=30)["neuronio"]
    cliente.post("/loja/piramidal_rosa/comprar")

    rosa = _concluir(cliente, relogio, duracao=30)["neuronio"]
    granular = _concluir(cliente, relogio, duracao=15)["neuronio"]

    assert (antes["tipo"], antes["variante"], antes["cor"]) == (
        "piramidal",
        "piramidal",
        "#8B7BFF",
    )
    assert (rosa["tipo"], rosa["variante"], rosa["cor"]) == (
        "piramidal",
        "piramidal_rosa",
        "#FF6FB5",
    )
    assert granular["variante"] == "granular"

    # A rede mostra cada neurônio com o tipo com que nasceu, e a forma não muda.
    neuronios = {n["id"]: n for n in cliente.get("/rede").json()["neuronios"]}
    assert neuronios[antes["id"]]["cor"] == "#8B7BFF"
    assert neuronios[rosa["id"]]["tipo"] == "piramidal"
    assert neuronios[rosa["id"]]["variante"] == "piramidal_rosa"
    assert neuronios[rosa["id"]]["cor"] == "#FF6FB5"
    assert NeuronioModel.objects.get(id=rosa["id"]).tipo == "piramidal_rosa"


def test_a_cor_da_materia_continua_valendo_na_rede(cliente, relogio):
    materia = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#C3E86B"}, format="json"
    ).json()
    _juntar_atp(cliente, relogio, 250)
    cliente.post("/loja/piramidal_rosa/comprar")

    neuronio = _concluir(cliente, relogio, duracao=30, materia_id=materia["id"])[
        "neuronio"
    ]

    na_rede = next(
        n for n in cliente.get("/rede").json()["neuronios"] if n["id"] == neuronio["id"]
    )
    assert na_rede["variante"] == "piramidal_rosa"
    assert na_rede["cor"] == "#C3E86B"


def test_neuronio_podado_guarda_o_tipo_e_fica_cinza(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)
    cliente.post("/loja/piramidal_rosa/comprar")
    sessao = cliente.post("/sessoes", {"duracao_minutos": 30}, format="json").json()
    relogio.avancar(minutes=10)
    cliente.post(f"/sessoes/{sessao['id']}/desistir")

    podado = next(n for n in cliente.get("/rede").json()["neuronios"] if not n["vivo"])

    assert podado["variante"] == "piramidal_rosa"
    assert podado["cor"] == "#4A4F6E"


def test_compra_em_poucas_consultas(cliente, relogio, django_assert_max_num_queries):
    _juntar_atp(cliente, relogio, 250)

    # Garante e reserva a carteira (2), lê os tipos comprados, grava o saldo, confere
    # e insere o tipo novo, mais o SAVEPOINT e o RELEASE das duas transações. Não
    # cresce com o número de sessões nem de compras.
    with django_assert_max_num_queries(10):
        resposta = cliente.post("/loja/piramidal_rosa/comprar")

    assert resposta.status_code == 200


# ------------------------------------------------------------------ migração


def test_a_migracao_credita_o_atp_de_quem_ja_tinha_sessoes(cliente, relogio):
    # Neurônios de antes da loja: 25 + 60 min vivos e um podado, que não conta.
    for duracao, vivo in [(25, True), (60, True), (45, False)]:
        sessao = SessaoFocoModel.objects.create(
            usuario=cliente.usuario,
            duracao_minutos=duracao,
            inicio=INICIO,
            estado="concluida" if vivo else "podada",
        )
        NeuronioModel.objects.create(
            usuario=cliente.usuario,
            sessao=sessao,
            duracao_minutos=duracao,
            vivo=vivo,
            criado_em=INICIO,
        )
    sem_sessoes = _cliente("sem@synapse.com")
    migracao = importlib.import_module("app.migrations.0007_loja_atp")

    migracao.creditar_sessoes_ja_concluidas(apps, None)

    assert CarteiraModel.objects.get(usuario=cliente.usuario).saldo == 85
    assert not CarteiraModel.objects.filter(usuario=sem_sessoes.usuario).exists()
    assert cliente.get("/loja").json()["saldo"] == 85


def test_swagger_documenta_a_loja(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    caminhos = schema["paths"]
    assert caminhos["/loja"]["get"]["tags"] == ["Loja"]
    assert caminhos["/loja/{codigo}/comprar"]["post"]["responses"].keys() >= {
        "200",
        "404",
        "409",
    }
    assert "409" in caminhos["/loja/{codigo}/usar"]["post"]["responses"]
    componentes = schema["components"]["schemas"]
    assert set(componentes["LojaResposta"]["properties"]) == {"saldo", "tipos"}
    assert {"atp"} <= set(componentes["ConclusaoResposta"]["properties"])
    assert {"tipo", "variante", "cor"} <= set(
        componentes["NeuronioResposta"]["properties"]
    )
