from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.carteira import Carteira, atp_da_sessao
from app.domain.entidades.neuronio import Granular, Piramidal, Purkinje
from app.domain.excecoes import (
    HorarioInvalido,
    SaldoInsuficiente,
    TipoBloqueado,
    TipoJaDesbloqueado,
)
from app.domain.loja import CATALOGO_LOJA, item_por_codigo

AGORA = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
ROSA = item_por_codigo("piramidal_rosa")  # 250 ATP
SAFIRA = item_por_codigo("piramidal_safira")  # 300 ATP
LIMA = item_por_codigo("granular_lima")  # 100 ATP
PIRAMIDAL = item_por_codigo("piramidal")


@pytest.mark.parametrize("duracao", [10, 25, 45, 120])
def test_criterio_sessao_rende_atp_proporcional_a_duracao(duracao):
    # 1 ATP por minuto: 45 min rendem 45 ATP, como no protótipo.
    assert atp_da_sessao(duracao) == duracao


def test_carteira_nova_comeca_vazia_com_os_tipos_originais():
    carteira = Carteira(uuid4())

    assert carteira.saldo == 0
    assert carteira.desbloqueados == {}
    assert carteira.tipos_em_uso(CATALOGO_LOJA) == (Granular(), Piramidal(), Purkinje())
    assert carteira.possui(PIRAMIDAL)
    assert not carteira.possui(ROSA)


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


def test_criterio_comprar_desconta_o_preco_desbloqueia_e_passa_a_usar():
    carteira = Carteira(uuid4(), saldo=300)

    carteira.comprar(ROSA, AGORA)

    assert carteira.saldo == 50
    assert carteira.desbloqueados == {"piramidal_rosa": AGORA}
    assert carteira.em_uso == {"piramidal": "piramidal_rosa"}
    assert carteira.tipos_em_uso(CATALOGO_LOJA) == (Granular(), ROSA.tipo, Purkinje())


def test_da_para_comprar_com_o_saldo_exato():
    carteira = Carteira(uuid4(), saldo=250)

    carteira.comprar(ROSA, AGORA)

    assert carteira.saldo == 0


def test_criterio_sem_saldo_a_compra_e_recusada_e_nada_muda():
    carteira = Carteira(uuid4(), saldo=200)

    with pytest.raises(SaldoInsuficiente, match="Faltam 50 ATP"):
        carteira.comprar(ROSA, AGORA)

    assert carteira.saldo == 200
    assert not carteira.possui(ROSA)
    assert carteira.em_uso == {}


def test_nao_compra_o_mesmo_tipo_duas_vezes():
    carteira = Carteira(uuid4(), saldo=1000)
    carteira.comprar(ROSA, AGORA)

    with pytest.raises(TipoJaDesbloqueado):
        carteira.comprar(ROSA, AGORA)
    assert carteira.saldo == 750


def test_tipo_original_nao_se_compra():
    with pytest.raises(TipoJaDesbloqueado):
        Carteira(uuid4(), saldo=1000).comprar(PIRAMIDAL, AGORA)


def test_so_usa_o_que_ja_comprou():
    carteira = Carteira(uuid4(), saldo=1000)

    with pytest.raises(TipoBloqueado):
        carteira.usar(ROSA)
    assert carteira.em_uso == {}


def test_troca_entre_variacoes_compradas_e_volta_ao_original():
    carteira = Carteira(uuid4(), saldo=1000)
    carteira.comprar(ROSA, AGORA)
    carteira.comprar(SAFIRA, AGORA)
    assert carteira.tipos_em_uso(CATALOGO_LOJA)[1] == SAFIRA.tipo

    carteira.usar(ROSA)
    assert carteira.tipos_em_uso(CATALOGO_LOJA)[1] == ROSA.tipo

    carteira.usar(PIRAMIDAL)
    assert carteira.em_uso == {}
    assert carteira.tipos_em_uso(CATALOGO_LOJA)[1] == Piramidal()
    # Continua desbloqueada: dá para voltar a usar sem pagar de novo.
    assert carteira.possui(ROSA)


def test_cada_forma_tem_a_sua_escolha():
    carteira = Carteira(uuid4(), saldo=1000)

    carteira.comprar(ROSA, AGORA)
    carteira.comprar(LIMA, AGORA)

    assert carteira.tipos_em_uso(CATALOGO_LOJA) == (LIMA.tipo, ROSA.tipo, Purkinje())


def test_escolha_fora_do_catalogo_volta_ao_original():
    carteira = Carteira(
        uuid4(),
        desbloqueados={"piramidal_aposentado": AGORA},
        em_uso={"piramidal": "piramidal_aposentado"},
    )

    assert carteira.tipos_em_uso(CATALOGO_LOJA)[1] == Piramidal()


def test_escolha_de_tipo_nao_comprado_volta_ao_original():
    # Ex.: dado inconsistente no banco; a carteira não usa o que não é do estudante.
    carteira = Carteira(uuid4(), em_uso={"piramidal": "piramidal_rosa"})

    assert carteira.tipos_em_uso(CATALOGO_LOJA)[1] == Piramidal()


def test_as_listas_devolvidas_sao_copias():
    carteira = Carteira(uuid4(), saldo=300)
    carteira.comprar(ROSA, AGORA)

    carteira.desbloqueados.clear()
    carteira.em_uso.clear()

    assert carteira.possui(ROSA)
    assert carteira.em_uso == {"piramidal": "piramidal_rosa"}
    assert repr(carteira) == "Carteira(saldo=50)"


def test_exige_horario_com_fuso():
    with pytest.raises(HorarioInvalido):
        Carteira(uuid4(), saldo=300).comprar(ROSA, datetime(2026, 10, 27, 14, 0))
