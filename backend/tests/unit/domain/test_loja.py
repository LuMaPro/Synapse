import pytest

from app.domain.entidades.neuronio import COR_PODADO, Granular, Piramidal, Purkinje
from app.domain.loja import (
    CATALOGO_CORES,
    CORES_DA_LOJA,
    CORES_GRATUITAS,
    CorLoja,
    Efeito,
    cor_por_codigo,
    cor_por_hex,
)


def test_as_cores_gratuitas_sao_a_paleta_das_materias_do_design():
    assert [c.hex for c in CORES_GRATUITAS] == [
        "#8B7BFF",
        "#3EE6E0",
        "#5BE49B",
        "#FFC857",
        "#FF8A5C",
        "#FF6FB5",
        "#6FA8FF",
        "#C3E86B",
    ]
    assert all(c.gratuita and c.efeito is None for c in CORES_GRATUITAS)


def test_a_loja_so_vende_cores_exclusivas():
    assert all(not c.gratuita for c in CORES_DA_LOJA)
    hexes = [c.hex for c in CATALOGO_CORES]
    codigos = [c.codigo for c in CATALOGO_CORES]
    assert len(set(hexes)) == len(hexes)
    assert len(set(codigos)) == len(codigos)
    # Não se confundem com a poda nem com a cor padrão dos tipos de neurônio.
    padrao = {t.cor for t in (Granular(), Piramidal(), Purkinje())}
    assert not ({COR_PODADO, "#FF5C7A"} | padrao) & {c.hex for c in CORES_DA_LOJA}


def test_as_cores_com_efeito_sao_as_mais_caras():
    lisas = [c.preco for c in CORES_DA_LOJA if c.efeito is None]
    com_efeito = [c.preco for c in CORES_DA_LOJA if c.efeito is not None]

    assert {c.efeito for c in CORES_DA_LOJA if c.efeito} == set(Efeito)
    assert max(lisas) < min(com_efeito)
    assert cor_por_codigo("arco_iris").preco == max(com_efeito)


def test_busca_pelo_codigo_e_pelo_hexadecimal():
    assert cor_por_codigo("tempestade").efeito is Efeito.TEMPESTADE
    assert cor_por_codigo("nao_existe") is None
    assert cor_por_hex("#ff3df0").codigo == "magenta_neon"
    assert cor_por_hex("#8B7BFF").gratuita
    assert cor_por_hex("#123456") is None


@pytest.mark.parametrize(
    ("hex_", "preco"), [("#8b7bff", 0), ("8B7BFF", 0), ("#8B7BFF", -1)]
)
def test_recusa_cor_mal_formada(hex_, preco):
    with pytest.raises(ValueError):
        CorLoja("x", "X", hex_, preco)
