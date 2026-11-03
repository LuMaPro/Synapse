"""Texto de cada registro no Django Admin (o __str__ dos models)."""

import uuid
from datetime import UTC, datetime

from app.infra.modelos.carteira import CarteiraModel, CorDesbloqueadaModel
from app.infra.modelos.conquista import ConquistaModel
from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sessao_foco import InterrupcaoModel
from app.infra.modelos.sinapse import SinapseModel

QUANDO = datetime(2026, 10, 30, 14, 5, 9, tzinfo=UTC)


def test_carteira_mostra_o_saldo():
    assert str(CarteiraModel(saldo=30)) == "30 ATP"


def test_cor_desbloqueada_mostra_o_codigo():
    assert str(CorDesbloqueadaModel(codigo="aurora", desbloqueada_em=QUANDO)) == (
        "aurora"
    )


def test_conquista_mostra_o_codigo_e_a_data():
    conquista = ConquistaModel(codigo="primeira_sessao", desbloqueada_em=QUANDO)

    assert str(conquista) == "primeira_sessao (30/10/2026)"


def test_neuronio_mostra_a_duracao():
    id_neuronio = uuid.uuid4()
    neuronio = NeuronioModel(id=id_neuronio, duracao_minutos=25, criado_em=QUANDO)

    assert str(neuronio) == f"Neurônio {id_neuronio} (25 min)"


def test_interrupcao_mostra_a_sessao_e_a_hora_da_saida():
    id_sessao = uuid.uuid4()
    interrupcao = InterrupcaoModel(sessao_id=id_sessao, saida=QUANDO)

    assert str(interrupcao) == f"Interrupção da sessão {id_sessao} às 14:05:09"


def test_sinapse_mostra_a_ligacao_e_o_peso():
    origem, destino = uuid.uuid4(), uuid.uuid4()
    sinapse = SinapseModel(
        origem_id=origem, destino_id=destino, peso=2, criada_em=QUANDO
    )

    assert str(sinapse) == f"Sinapse {origem} → {destino} (peso 2)"
