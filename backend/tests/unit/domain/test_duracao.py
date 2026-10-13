from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from app.domain.duracao import Duracao
from app.domain.excecoes import DuracaoInvalida


@pytest.mark.parametrize("minutos", [10, 25, 60, 120])
def test_aceita_duracoes_validas(minutos):
    assert Duracao(minutos).minutos == minutos


@pytest.mark.parametrize("minutos", [-10, 0, 5, 125, 180])
def test_recusa_duracao_fora_do_intervalo(minutos):
    with pytest.raises(DuracaoInvalida, match="entre 10 e 120"):
        Duracao(minutos)


@pytest.mark.parametrize("minutos", [11, 23, 117])
def test_recusa_duracao_que_nao_e_multipla_de_5(minutos):
    with pytest.raises(DuracaoInvalida, match="múltipla de 5"):
        Duracao(minutos)


@pytest.mark.parametrize("minutos", [25.0, "25", None, True])
def test_recusa_duracao_que_nao_e_inteiro(minutos):
    with pytest.raises(DuracaoInvalida, match="número inteiro"):
        Duracao(minutos)


def test_e_imutavel():
    duracao = Duracao(25)

    with pytest.raises(FrozenInstanceError):
        duracao.minutos = 30


def test_duracoes_com_os_mesmos_minutos_sao_iguais():
    assert Duracao(25) == Duracao(25)
    assert Duracao(25) != Duracao(30)


def test_converte_para_timedelta():
    assert Duracao(25).como_timedelta() == timedelta(minutes=25)
