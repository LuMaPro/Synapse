import pytest

from app.domain.excecoes import (
    DuracaoInvalida,
    EmailInvalido,
    ErroDominio,
    HorarioInvalido,
    NomeInvalido,
)


@pytest.mark.parametrize(
    "excecao", [DuracaoInvalida, EmailInvalido, HorarioInvalido, NomeInvalido]
)
def test_excecoes_herdam_de_erro_dominio(excecao):
    assert issubclass(excecao, ErroDominio)

    with pytest.raises(ErroDominio, match="mensagem"):
        raise excecao("mensagem")
