from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.entidades import Sinapse
from app.domain.excecoes import HorarioInvalido, SinapseInvalida

CRIADA_EM = datetime(2026, 10, 20, 14, 0, tzinfo=UTC)


def test_cria_sinapse_entre_dois_neuronios():
    origem, destino = uuid4(), uuid4()

    sinapse = Sinapse(origem, destino, 2, criada_em=CRIADA_EM)

    assert isinstance(sinapse.id, UUID)
    assert sinapse.origem_id == origem
    assert sinapse.destino_id == destino
    assert sinapse.peso == 2
    assert sinapse.criada_em == CRIADA_EM


def test_criterio_recusa_neuronio_ligado_a_ele_mesmo():
    neuronio = uuid4()

    with pytest.raises(SinapseInvalida, match="ele mesmo"):
        Sinapse(neuronio, neuronio, 1)


@pytest.mark.parametrize("peso", [0, -1, 1.5, "2", None, True])
def test_recusa_peso_invalido(peso):
    with pytest.raises(SinapseInvalida, match="peso"):
        Sinapse(uuid4(), uuid4(), peso)


def test_recusa_data_sem_fuso():
    with pytest.raises(HorarioInvalido):
        Sinapse(uuid4(), uuid4(), 1, criada_em=datetime(2026, 10, 20, 14, 0))


def test_o_par_nao_depende_da_direcao():
    a, b = uuid4(), uuid4()

    assert Sinapse(a, b, 1).par == Sinapse(b, a, 3).par == frozenset({a, b})


@pytest.mark.parametrize("atributo", ["id", "origem_id", "destino_id", "peso"])
def test_atributos_sao_somente_leitura(atributo):
    sinapse = Sinapse(uuid4(), uuid4(), 1)

    with pytest.raises(AttributeError):
        setattr(sinapse, atributo, "outro valor")


def test_repr_mostra_as_pontas_e_o_peso():
    origem, destino = uuid4(), uuid4()

    assert repr(Sinapse(origem, destino, 3)) == (
        f"Sinapse(origem_id={origem}, destino_id={destino}, peso=3)"
    )
