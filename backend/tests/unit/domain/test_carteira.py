from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.carteira import Carteira, atp_da_sessao
from app.domain.excecoes import CorJaDesbloqueada, HorarioInvalido, SaldoInsuficiente
from app.domain.loja import cor_por_codigo

AGORA = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
MAGENTA = cor_por_codigo("magenta_neon")  # 250 ATP
ARCO_IRIS = cor_por_codigo("arco_iris")  # 1200 ATP
VIOLETA = cor_por_codigo("violeta")  # gratuita


@pytest.mark.parametrize("duracao", [10, 25, 45, 120])
def test_criterio_sessao_rende_atp_proporcional_a_duracao(duracao):
    # 1 ATP por minuto: 45 min rendem 45 ATP, como no protótipo.
    assert atp_da_sessao(duracao) == duracao


def test_carteira_nova_comeca_vazia_e_com_as_cores_gratuitas():
    carteira = Carteira(uuid4())

    assert carteira.saldo == 0
    assert carteira.desbloqueadas == {}
    assert carteira.possui(VIOLETA)
    assert not carteira.possui(MAGENTA)


def test_creditar_soma_ao_saldo():
    carteira = Carteira(uuid4())

    carteira.creditar(25)
    carteira.creditar(45)

    assert carteira.saldo == 70


@pytest.mark.parametrize("quantia", [0, -5])
def test_credito_precisa_ser_positivo(quantia):
    with pytest.raises(ValueError):
        Carteira(uuid4()).creditar(quantia)


def test_saldo_nao_comeca_negativo():
    with pytest.raises(ValueError):
        Carteira(uuid4(), saldo=-1)


def test_criterio_comprar_desconta_o_preco_e_desbloqueia_a_cor():
    carteira = Carteira(uuid4(), saldo=300)

    carteira.comprar(MAGENTA, AGORA)

    assert carteira.saldo == 50
    assert carteira.desbloqueadas == {"magenta_neon": AGORA}
    assert carteira.possui(MAGENTA)


def test_da_para_comprar_com_o_saldo_exato():
    carteira = Carteira(uuid4(), saldo=250)

    carteira.comprar(MAGENTA, AGORA)

    assert carteira.saldo == 0


def test_criterio_sem_saldo_a_compra_e_recusada_e_nada_muda():
    carteira = Carteira(uuid4(), saldo=1000)

    with pytest.raises(SaldoInsuficiente, match="Faltam 200 ATP"):
        carteira.comprar(ARCO_IRIS, AGORA)

    assert carteira.saldo == 1000
    assert not carteira.possui(ARCO_IRIS)


def test_nao_compra_a_mesma_cor_duas_vezes():
    carteira = Carteira(uuid4(), saldo=1000)
    carteira.comprar(MAGENTA, AGORA)

    with pytest.raises(CorJaDesbloqueada):
        carteira.comprar(MAGENTA, AGORA)
    assert carteira.saldo == 750


def test_cor_gratuita_nao_se_compra():
    with pytest.raises(CorJaDesbloqueada):
        Carteira(uuid4(), saldo=1000).comprar(VIOLETA, AGORA)


def test_a_lista_devolvida_e_uma_copia():
    carteira = Carteira(uuid4(), saldo=300)
    carteira.comprar(MAGENTA, AGORA)

    carteira.desbloqueadas.clear()

    assert carteira.possui(MAGENTA)
    assert repr(carteira) == "Carteira(saldo=50)"


def test_exige_horario_com_fuso():
    with pytest.raises(HorarioInvalido):
        Carteira(uuid4(), saldo=300).comprar(MAGENTA, datetime(2026, 10, 27, 14, 0))
