from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entidades.neuronio import (
    COR_PODADO,
    FabricaNeuronio,
    Granular,
    Neuronio,
    Piramidal,
    Purkinje,
    VarianteCor,
)
from app.domain.entidades.sessao_foco import Concluida, Podada, SessaoFoco
from app.domain.loja import CATALOGO_LOJA, ItemLoja, item_por_codigo, tipo_por_codigo

ROSA = VarianteCor(Piramidal(), "piramidal_rosa", "Piramidal Rosa", "#FF6FB5")


# ------------------------------------------------------------------ variação


def test_a_variacao_troca_so_o_nome_e_a_cor():
    assert ROSA.nome == "Piramidal Rosa"
    assert ROSA.cor == "#FF6FB5"
    assert ROSA.codigo == "piramidal_rosa"
    # A forma, a faixa de duração e o desenho continuam os do tipo original.
    assert ROSA.forma == "piramidal"
    assert ROSA.base == Piramidal()
    assert (ROSA.duracao_minima, ROSA.duracao_maxima) == (25, 59)
    assert ROSA.numero_dendritos == Piramidal().numero_dendritos
    assert ROSA.raio == Piramidal().raio
    assert ROSA.aceita(25) and ROSA.aceita(59)
    assert not ROSA.aceita(24) and not ROSA.aceita(60)


def test_os_tipos_originais_tem_a_propria_forma():
    assert [t.forma for t in (Granular(), Piramidal(), Purkinje())] == [
        "granular",
        "piramidal",
        "purkinje",
    ]


def test_variacoes_sao_iguais_pelo_codigo():
    outra_rosa = VarianteCor(Piramidal(), "piramidal_rosa", "Outro nome", "#000000")
    safira = VarianteCor(Piramidal(), "piramidal_safira", "Safira", "#6FA8FF")

    assert ROSA == outra_rosa
    assert hash(ROSA) == hash(outra_rosa)
    assert ROSA != safira
    assert ROSA != Piramidal()
    assert Piramidal() != ROSA
    assert repr(ROSA) == "VarianteCor('piramidal_rosa')"


def test_nao_ha_variacao_de_variacao():
    with pytest.raises(TypeError):
        VarianteCor(ROSA, "rosa_rosa", "Rosa Rosa", "#FF00FF")


def _sessao(duracao, estado):
    inicio = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
    return SessaoFoco(
        uuid4(),
        duracao,
        inicio=inicio,
        encerrada_em=inicio + timedelta(minutes=duracao),
        estado=estado,
    )


def test_a_fabrica_com_a_variacao_cria_neuronios_dela_na_faixa_dela():
    fabrica = FabricaNeuronio((Granular(), ROSA, Purkinje()))

    rosa = fabrica.criar(_sessao(45, Concluida()))
    granular = fabrica.criar(_sessao(10, Concluida()))

    assert rosa.tipo == ROSA
    assert rosa.tipo.forma == "piramidal"
    assert rosa.cor == "#FF6FB5"
    assert granular.tipo == Granular()


def test_neuronio_podado_da_variacao_continua_cinza():
    fabrica = FabricaNeuronio((Granular(), ROSA, Purkinje()))

    podado = fabrica.criar(_sessao(45, Podada()))

    assert podado.tipo == ROSA
    assert podado.cor == COR_PODADO


def test_neuronio_aceita_a_variacao_como_tipo():
    neuronio = Neuronio(uuid4(), uuid4(), 30, tipo=ROSA)

    assert neuronio.cor == "#FF6FB5"
    assert neuronio.numero_dendritos == Piramidal().numero_dendritos


# ------------------------------------------------------------------ catálogo


def test_catalogo_tem_um_original_gratuito_por_forma_e_variacoes_pagas():
    codigos = [item.codigo for item in CATALOGO_LOJA]
    originais = [item for item in CATALOGO_LOJA if item.gratuito]
    variacoes = [item for item in CATALOGO_LOJA if not item.gratuito]

    assert len(set(codigos)) == len(codigos)
    assert [item.codigo for item in originais] == ["granular", "piramidal", "purkinje"]
    assert len(variacoes) == 6
    assert all(isinstance(item.tipo, VarianteCor) for item in variacoes)
    assert all(item.preco > 0 for item in variacoes)
    # As cores não se confundem com a do neurônio podado nem com as originais.
    cores = [item.tipo.cor.upper() for item in CATALOGO_LOJA]
    assert len(set(cores)) == len(cores)
    assert COR_PODADO not in cores


def test_variacoes_mais_longas_custam_mais():
    preco = {item.codigo: item.preco for item in CATALOGO_LOJA}

    assert preco["granular_lima"] < preco["piramidal_rosa"] < preco["purkinje_coral"]


def test_busca_item_e_tipo_pelo_codigo():
    assert item_por_codigo("piramidal_rosa").preco == 250
    assert item_por_codigo("nao_existe") is None
    assert tipo_por_codigo("piramidal_rosa") == ROSA
    assert tipo_por_codigo("purkinje") == Purkinje()
    assert tipo_por_codigo("aposentado") is None


def test_item_sabe_a_forma_e_se_e_gratuito():
    item = ItemLoja(ROSA, 250)

    assert item.codigo == "piramidal_rosa"
    assert item.forma == "piramidal"
    assert not item.gratuito
    assert ItemLoja(Piramidal(), 0).gratuito


def test_preco_nao_pode_ser_negativo():
    with pytest.raises(ValueError):
        ItemLoja(ROSA, -1)
