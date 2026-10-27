import importlib
from datetime import UTC, datetime, timedelta

import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from rest_framework.test import APIClient

from app.infra.modelos.carteira import CarteiraModel, CorDesbloqueadaModel
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
    for _ in range(15):
        if cliente.get("/loja").json()["saldo"] >= quantia:
            return
        _concluir(cliente, relogio, duracao=120)
    pytest.fail(f"15 sessões de 2 h não juntaram {quantia} ATP.")


def _cor(corpo: dict, codigo: str) -> dict:
    return next(c for c in corpo["cores"] if c["codigo"] == codigo)


# ------------------------------------------------------------------ loja


def test_exige_autenticacao():
    for metodo, caminho in [("get", "/loja"), ("post", "/loja/lavanda/comprar")]:
        resposta = getattr(APIClient(), metodo)(caminho)
        assert resposta.status_code == 401
        assert resposta.json()["erro"] == "nao_autenticado"


def test_estudante_novo_ve_a_paleta_e_as_cores_da_loja(cliente):
    resposta = cliente.get("/loja")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo"] == 0
    assert len(corpo["cores"]) == 20
    gratuitas = [c for c in corpo["cores"] if c["preco"] == 0]
    assert [c["codigo"] for c in gratuitas][:2] == ["violeta", "ciano"]
    assert len(gratuitas) == 8
    assert all(c["desbloqueada"] for c in gratuitas)
    assert _cor(corpo, "arco_iris") == {
        "codigo": "arco_iris",
        "nome": "Arco-íris",
        "cor": "#FF7AD9",
        "efeito": "arco_iris",
        "preco": 1200,
        "desbloqueada": False,
    }
    assert _cor(corpo, "lavanda")["efeito"] is None


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

    resposta = cliente.post("/loja/magenta_neon/comprar")

    assert resposta.status_code == 409
    assert resposta.json() == {
        "erro": "saldo_insuficiente",
        "mensagem": "Faltam 130 ATP para comprar a cor Magenta neon.",
    }
    assert cliente.get("/loja").json()["saldo"] == 120
    assert not CorDesbloqueadaModel.objects.filter(usuario=cliente.usuario).exists()


def test_criterio_comprar_desconta_e_desbloqueia(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)  # 3 sessões de 2 h: 360 ATP

    resposta = cliente.post("/loja/magenta_neon/comprar")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo"] == 110
    assert _cor(corpo, "magenta_neon")["desbloqueada"] is True
    assert cliente.get("/loja").json() == corpo


def test_nao_compra_duas_vezes(cliente, relogio):
    _juntar_atp(cliente, relogio, 500)
    cliente.post("/loja/magenta_neon/comprar")

    resposta = cliente.post("/loja/magenta_neon/comprar")

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "cor_ja_desbloqueada"
    # 5 sessões de 2 h (600 ATP), uma compra só.
    assert cliente.get("/loja").json()["saldo"] == 600 - 250


def test_cor_fora_da_loja(cliente):
    resposta = cliente.post("/loja/unicornio/comprar")

    assert resposta.status_code == 404
    assert resposta.json()["erro"] == "cor_nao_encontrada"


def test_carteiras_de_estudantes_diferentes_nao_se_misturam(cliente, relogio):
    _juntar_atp(cliente, relogio, 250)
    cliente.post("/loja/magenta_neon/comprar")
    outro = _cliente("outro@synapse.com")

    corpo = outro.get("/loja").json()
    assert corpo["saldo"] == 0
    assert _cor(corpo, "magenta_neon")["desbloqueada"] is False


def test_compra_em_poucas_consultas(cliente, relogio, django_assert_max_num_queries):
    _juntar_atp(cliente, relogio, 250)

    # Garante e reserva a carteira (2), lê as cores compradas, grava o saldo, confere
    # e insere a cor nova, mais o SAVEPOINT e o RELEASE das duas transações. Não
    # cresce com o número de sessões nem de compras.
    with django_assert_max_num_queries(10):
        resposta = cliente.post("/loja/magenta_neon/comprar")

    assert resposta.status_code == 200


# ------------------------------------------------------------------ matérias e rede


def test_criterio_materia_so_aceita_cor_gratuita_ou_comprada(cliente, relogio):
    bloqueada = cliente.post(
        "/materias", {"nome": "Física", "cor": "#FF3DF0"}, format="json"
    )
    fora = cliente.post(
        "/materias", {"nome": "Física", "cor": "#123456"}, format="json"
    )

    assert bloqueada.status_code == 409
    assert bloqueada.json() == {
        "erro": "cor_bloqueada",
        "mensagem": "Compre a cor Magenta neon na loja para usá-la.",
    }
    assert fora.status_code == 400
    assert fora.json()["erro"] == "cor_invalido"

    _juntar_atp(cliente, relogio, 250)
    cliente.post("/loja/magenta_neon/comprar")
    criada = cliente.post(
        "/materias", {"nome": "Física", "cor": "#ff3df0"}, format="json"
    )
    assert criada.status_code == 201
    assert criada.json()["cor"] == "#FF3DF0"
    assert criada.json()["efeito"] is None


def test_cor_com_efeito_vai_para_a_materia_e_para_a_rede(cliente, relogio):
    _juntar_atp(cliente, relogio, 1200)  # 10 sessões de 2 h
    cliente.post("/loja/arco_iris/comprar")
    materia = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#FF7AD9"}, format="json"
    ).json()
    assert materia["efeito"] == "arco_iris"

    neuronio = _concluir(cliente, relogio, duracao=25, materia_id=materia["id"])[
        "neuronio"
    ]

    na_rede = next(
        n for n in cliente.get("/rede").json()["neuronios"] if n["id"] == neuronio["id"]
    )
    assert (na_rede["cor"], na_rede["efeito"]) == ("#FF7AD9", "arco_iris")
    # Os neurônios sem matéria seguem com a cor padrão do tipo, sem efeito.
    sem_materia = [
        n for n in cliente.get("/rede").json()["neuronios"] if not n["materia_id"]
    ]
    assert {(n["cor"], n["efeito"]) for n in sem_materia} == {("#FFC857", None)}


def test_criterio_editar_a_cor_da_materia_muda_os_neuronios_dela(cliente, relogio):
    materia = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json"
    ).json()
    _concluir(cliente, relogio, duracao=30, materia_id=materia["id"])
    _concluir(cliente, relogio, duracao=60, materia_id=materia["id"])
    _juntar_atp(cliente, relogio, 500)
    cliente.post("/loja/pulsar/comprar")

    resposta = cliente.patch(
        f"/materias/{materia['id']}", {"cor": "#7DF9FF"}, format="json"
    )

    assert resposta.status_code == 200
    assert resposta.json()["efeito"] == "pulsar"
    da_materia = [
        n
        for n in cliente.get("/rede").json()["neuronios"]
        if n["materia_id"] == materia["id"]
    ]
    assert len(da_materia) == 2
    assert {(n["cor"], n["efeito"]) for n in da_materia} == {("#7DF9FF", "pulsar")}


def test_editar_para_cor_nao_comprada_e_recusado(cliente):
    materia = cliente.post(
        "/materias", {"nome": "Cálculo", "cor": "#8B7BFF"}, format="json"
    ).json()

    resposta = cliente.patch(
        f"/materias/{materia['id']}", {"cor": "#7DF9FF"}, format="json"
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "cor_bloqueada"
    assert cliente.get(f"/materias/{materia['id']}").json()["cor"] == "#8B7BFF"


# ------------------------------------------------------------------ migrações


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


@pytest.mark.django_db(transaction=True)
def test_a_migracao_devolve_o_atp_das_variacoes_da_loja_anterior():
    executor = MigrationExecutor(connection)
    anterior = [("app", "0007_loja_atp")]
    executor.migrate(anterior)
    estado = executor.loader.project_state(anterior).apps
    usuario = estado.get_model("app", "UsuarioModel").objects.create(
        email="antigo@synapse.com", nome="Antigo"
    )
    estado.get_model("app", "CarteiraModel").objects.create(usuario=usuario, saldo=40)
    compras = estado.get_model("app", "TipoDesbloqueadoModel")
    for codigo in ("piramidal_rosa", "granular_lima"):
        compras.objects.create(usuario=usuario, codigo=codigo, desbloqueado_em=INICIO)

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert CarteiraModel.objects.get(usuario_id=usuario.id).saldo == 40 + 250 + 100


def test_swagger_documenta_a_loja(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    caminhos = schema["paths"]
    assert caminhos["/loja"]["get"]["tags"] == ["Loja"]
    assert caminhos["/loja/{codigo}/comprar"]["post"]["responses"].keys() >= {
        "200",
        "404",
        "409",
    }
    assert "/loja/{codigo}/usar" not in caminhos
    componentes = schema["components"]["schemas"]
    assert set(componentes["LojaResposta"]["properties"]) == {"saldo", "cores"}
    assert "efeito" in componentes["MateriaResposta"]["properties"]
    assert "efeito" in componentes["NeuronioRede"]["properties"]
    assert "atp" in componentes["ConclusaoResposta"]["properties"]
