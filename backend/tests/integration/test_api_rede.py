import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from app.api.periodo import DataOuInstanteField
from app.api.rede import _neuronio_json
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import Concluida, Podada, SessaoFoco
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel
from app.infra.repositorios import RepositorioRedeNeuralDjango

pytestmark = pytest.mark.django_db

INICIO = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
CALCULO, FISICA = uuid4(), uuid4()


@pytest.fixture
def usuario():
    return UsuarioModel.objects.create_user(email="rede@synapse.com", nome="Rede")


@pytest.fixture
def cliente(usuario):
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente


def _montar_rede(usuario, neuronios: list[dict]) -> list[str]:
    """Grava a rede do estudante pelo agregado, como o SessaoService faria.

    Cada item tem `criado_em` e, opcionalmente, `vivo`, `materia_id` e `duracao`.
    Devolve os ids dos neurônios, na mesma ordem.
    """
    sessoes = [
        SessaoFoco(
            usuario.id,
            n.get("duracao", 25),
            inicio=INICIO,
            estado=Concluida() if n.get("vivo", True) else Podada(),
        )
        for n in neuronios
    ]
    SessaoFocoModel.objects.bulk_create(
        SessaoFocoModel(
            id=s.id,
            usuario_id=usuario.id,
            duracao_minutos=s.duracao.minutos,
            inicio=s.inicio,
            estado=s.codigo_estado,
        )
        for s in sessoes
    )
    repo = RepositorioRedeNeuralDjango()
    rede = repo.carregar(usuario.id)
    criados = []
    for sessao, dados in zip(sessoes, neuronios, strict=True):
        neuronio = Neuronio(
            usuario.id,
            sessao.id,
            sessao.duracao.minutos,
            vivo=dados.get("vivo", True),
            materia_id=dados.get("materia_id"),
            criado_em=dados["criado_em"],
        )
        rede.adicionar(neuronio)
        criados.append(str(neuronio.id))
    repo.salvar(rede)
    return criados


def _no_dia(dia: int, hora: int = 12) -> datetime:
    return datetime(2026, 10, dia, hora, 0, tzinfo=UTC)


# ------------------------------------------------------------------ formato


def test_exige_autenticacao():
    resposta = APIClient().get("/rede")

    assert resposta.status_code == 401
    assert resposta.json()["erro"] == "nao_autenticado"


def test_rede_vazia(cliente):
    resposta = cliente.get("/rede")

    assert resposta.status_code == 200
    assert resposta.json() == {"neuronios": [], "sinapses": []}


def test_devolve_a_rede_no_formato_de_grafo(cliente, usuario):
    primeiro, segundo, podado, quarto = _montar_rede(
        usuario,
        [
            {"criado_em": _no_dia(1), "duracao": 20, "materia_id": CALCULO},
            {"criado_em": _no_dia(2), "duracao": 25},
            {"criado_em": _no_dia(3), "duracao": 45, "vivo": False},
            {"criado_em": _no_dia(4), "duracao": 60, "materia_id": CALCULO},
        ],
    )

    corpo = cliente.get("/rede").json()

    assert [n["id"] for n in corpo["neuronios"]] == [primeiro, segundo, podado, quarto]
    assert corpo["neuronios"][0] == {
        "id": primeiro,
        "tipo": "granular",
        "variante": "granular",
        "materia_id": str(CALCULO),
        "cor": "#3EE6E0",
        "criado_em": "2026-10-01T12:00:00+00:00",
        "duracao_minutos": 20,
        "vivo": True,
    }
    assert [(n["tipo"], n["cor"], n["vivo"]) for n in corpo["neuronios"][1:]] == [
        ("piramidal", "#8B7BFF", True),
        ("piramidal", "#4A4F6E", False),  # podado é sempre cinza
        ("purkinje", "#FFC857", True),
    ]
    sinapses = {(s["origem_id"], s["destino_id"], s["peso"]) for s in corpo["sinapses"]}
    # O podado fica sem sinapses; o quarto se liga aos 2 vivos anteriores, e a
    # ligação com o primeiro (mesma matéria) é reforçada.
    assert sinapses == {
        (primeiro, segundo, 1),
        (primeiro, quarto, 2),
        (segundo, quarto, 1),
    }
    assert set(corpo["sinapses"][0]) == {"id", "origem_id", "destino_id", "peso"}


@pytest.mark.parametrize(
    ("duracao", "tipo"),
    [
        (10, "granular"),
        (20, "granular"),
        (25, "piramidal"),
        (55, "piramidal"),
        (60, "purkinje"),
        (120, "purkinje"),
    ],
)
def test_tipo_pelas_faixas_de_duracao_do_design(duracao, tipo):
    neuronio = Neuronio(uuid4(), uuid4(), duracao)
    assert _neuronio_json(neuronio)["tipo"] == tipo


def test_cada_estudante_ve_so_a_sua_rede(cliente, usuario):
    outro = UsuarioModel.objects.create_user(email="outro@synapse.com", nome="Outro")
    _montar_rede(outro, [{"criado_em": _no_dia(1)}, {"criado_em": _no_dia(2)}])
    [meu] = _montar_rede(usuario, [{"criado_em": _no_dia(3)}])

    corpo = cliente.get("/rede").json()

    assert [n["id"] for n in corpo["neuronios"]] == [meu]
    assert corpo["sinapses"] == []


def test_sessoes_feitas_pela_api_aparecem_na_rede(cliente, monkeypatch):
    agora = {"instante": INICIO}
    monkeypatch.setattr("app.api.sessoes.agora", lambda: agora["instante"])
    for _ in range(2):
        sessao = cliente.post("/sessoes", {"duracao_minutos": 10}, format="json").json()
        agora["instante"] += timedelta(minutes=10)
        assert cliente.post(f"/sessoes/{sessao['id']}/concluir").status_code == 200
    sessao = cliente.post("/sessoes", {"duracao_minutos": 10}, format="json").json()
    cliente.post(f"/sessoes/{sessao['id']}/desistir")

    corpo = cliente.get("/rede").json()

    assert [n["vivo"] for n in corpo["neuronios"]] == [True, True, False]
    assert len(corpo["sinapses"]) == 1


# ------------------------------------------------------------------ filtros


@pytest.fixture
def rede_de_outubro(usuario):
    """Um neurônio por dia, de 1 a 5 de outubro, alternando as matérias."""
    materias = [CALCULO, FISICA, CALCULO, FISICA, CALCULO]
    return _montar_rede(
        usuario,
        [
            {"criado_em": _no_dia(dia), "materia_id": materia}
            for dia, materia in enumerate(materias, start=1)
        ],
    )


def _ids(resposta) -> list[str]:
    assert resposta.status_code == 200, resposta.json()
    return [n["id"] for n in resposta.json()["neuronios"]]


def test_filtro_por_datas_inclui_os_dias_das_pontas(cliente, rede_de_outubro):
    resposta = cliente.get("/rede", {"de": "2026-10-02", "ate": "2026-10-04"})

    assert _ids(resposta) == rede_de_outubro[1:4]


def test_filtro_so_com_inicio_ou_so_com_fim(cliente, rede_de_outubro):
    assert _ids(cliente.get("/rede", {"de": "2026-10-04"})) == rede_de_outubro[3:]
    assert _ids(cliente.get("/rede", {"ate": "2026-10-01"})) == rede_de_outubro[:1]


def test_filtro_com_data_e_hora_respeita_o_fuso(cliente, usuario):
    # 01:00 de 3/10 em UTC ainda é 22:00 de 2/10 em Brasília (UTC-3).
    noite, dia_seguinte = _montar_rede(
        usuario, [{"criado_em": _no_dia(3, hora=1)}, {"criado_em": _no_dia(3, hora=15)}]
    )

    resposta = cliente.get(
        "/rede",
        {"de": "2026-10-02T00:00:00-03:00", "ate": "2026-10-02T23:59:59-03:00"},
    )

    assert _ids(resposta) == [noite]
    assert dia_seguinte not in _ids(
        cliente.get("/rede", {"ate": "2026-10-02T23:59:59-03:00"})
    )


def test_filtro_por_materia_traz_so_as_sinapses_entre_os_escolhidos(
    cliente, rede_de_outubro
):
    corpo = cliente.get("/rede", {"materia": str(CALCULO)}).json()

    calculo = [rede_de_outubro[i] for i in (0, 2, 4)]
    assert [n["id"] for n in corpo["neuronios"]] == calculo
    escolhidos = set(calculo)
    assert corpo["sinapses"]
    assert all(
        s["origem_id"] in escolhidos and s["destino_id"] in escolhidos
        for s in corpo["sinapses"]
    )


def test_filtros_combinados(cliente, rede_de_outubro):
    resposta = cliente.get(
        "/rede", {"de": "2026-10-02", "ate": "2026-10-05", "materia": str(FISICA)}
    )

    assert _ids(resposta) == [rede_de_outubro[1], rede_de_outubro[3]]


@pytest.mark.parametrize(
    ("filtros", "campo"),
    [
        ({"de": "ontem"}, "de"),
        ({"ate": "2026-02-30"}, "ate"),
        ({"de": "2026-10-05", "ate": "2026-10-01"}, "ate"),
        ({"materia": "calculo"}, "materia"),
    ],
)
def test_recusa_filtro_invalido(cliente, filtros, campo):
    resposta = cliente.get("/rede", filtros)

    assert resposta.status_code == 400
    assert resposta.json()["erro"] == "validacao"
    assert campo in resposta.json()["detalhes"]


# ------------------------------------------------------------------ desempenho


def test_criterio_responde_em_menos_de_300_ms_com_500_neuronios(
    cliente, usuario, django_assert_max_num_queries
):
    materias = [CALCULO, FISICA, None]
    _montar_rede(
        usuario,
        [
            {
                "criado_em": INICIO + timedelta(hours=i),
                "materia_id": materias[i % 3],
                "duracao": (10, 25, 60)[i % 3],
                "vivo": i % 6 != 5,
            }
            for i in range(500)
        ],
    )
    cliente.get("/rede")  # aquece (imports e conexão), como num servidor já no ar

    inicio = time.perf_counter()
    # Três consultas constantes: neurônios, sinapses e matérias (#28).
    with django_assert_max_num_queries(3):
        resposta = cliente.get("/rede")
    duracao = time.perf_counter() - inicio

    assert resposta.status_code == 200
    assert len(resposta.json()["neuronios"]) == 500
    assert len(resposta.json()["sinapses"]) > 700
    assert duracao < 0.3, f"GET /rede levou {duracao * 1000:.0f} ms"


def test_neuronio_com_materia_recebe_a_cor_da_materia_na_rede(cliente, usuario):
    from app.infra.modelos.materia import MateriaModel

    materia = MateriaModel.objects.create(
        usuario=usuario, nome="Bioquímica", cor="#FF6FB5"
    )
    _montar_rede(
        usuario,
        [
            {
                "criado_em": _no_dia(1),
                "duracao": 25,
                "materia_id": materia.id,
                "vivo": True,
            },
            {
                "criado_em": _no_dia(2),
                "duracao": 25,
                "materia_id": materia.id,
                "vivo": False,
            },
            {
                "criado_em": _no_dia(3),
                "duracao": 25,
                "materia_id": None,
                "vivo": True,
            },
        ],
    )

    resposta = cliente.get("/rede")
    assert resposta.status_code == 200
    neuronios = resposta.json()["neuronios"]
    assert len(neuronios) == 3
    # Vivo com matéria: recebe cor da matéria (#FF6FB5)
    assert neuronios[0]["cor"] == "#FF6FB5"
    assert neuronios[0]["materia_id"] == str(materia.id)
    # Podado com matéria: continua cinza (#4A4F6E)
    assert neuronios[1]["cor"] == "#4A4F6E"
    assert neuronios[1]["materia_id"] == str(materia.id)
    # Vivo sem matéria: cor padrão do tipo piramidal (#8B7BFF)
    assert neuronios[2]["cor"] == "#8B7BFF"
    assert neuronios[2]["materia_id"] is None


# ------------------------------------------------------------------ Swagger


def test_swagger_documenta_o_formato_os_filtros_e_um_exemplo(cliente):
    schema = cliente.get("/schema/", HTTP_ACCEPT="application/json").json()

    operacao = schema["paths"]["/rede"]["get"]
    assert {p["name"] for p in operacao["parameters"]} == {"de", "ate", "materia"}
    conteudo = operacao["responses"]["200"]["content"]["application/json"]
    assert conteudo["examples"]
    componentes = schema["components"]["schemas"]
    assert set(componentes["RedeResposta"]["properties"]) == {"neuronios", "sinapses"}
    assert set(componentes["NeuronioRede"]["properties"]) == {
        "id",
        "tipo",
        "variante",
        "materia_id",
        "cor",
        "criado_em",
        "duracao_minutos",
        "vivo",
    }


def test_campo_de_periodo_mostra_o_valor_em_iso_8601():
    campo = DataOuInstanteField()

    assert campo.to_representation(_no_dia(1)) == "2026-10-01T12:00:00+00:00"
