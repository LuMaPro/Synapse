from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.excecoes import HorarioInvalido
from app.domain.politica_interrupcao import (
    Interrupcao,
    ModoEstrito,
    ModoTolerante,
)

INICIO = datetime(2026, 10, 12, 14, 0, tzinfo=UTC)


@pytest.fixture
def sessao_60_min():
    """Sessão de 60 minutos (10% de tolerância = 6 minutos = 360 segundos)."""
    return SessaoFoco(usuario_id=uuid4(), duracao_minutos=60, inicio=INICIO)


# ==============================================================================
# Testes da Interrupcao
# ==============================================================================


def test_interrupcao_calcula_segundos_fora_corretamente():
    saida = INICIO
    retorno = INICIO + timedelta(minutes=2, seconds=30)
    interrupcao = Interrupcao(saida=saida, retorno=retorno)

    assert interrupcao.segundos_fora == 150.0


def test_interrupcao_sem_retorno_tem_zero_segundos_fora():
    interrupcao = Interrupcao(saida=INICIO)

    assert interrupcao.segundos_fora == 0.0


def test_interrupcao_rejeita_horarios_sem_fuso():
    naive_dt = datetime(2026, 10, 12, 14, 0)

    with pytest.raises(HorarioInvalido, match="saida"):
        Interrupcao(saida=naive_dt)

    with pytest.raises(HorarioInvalido, match="retorno"):
        Interrupcao(saida=INICIO, retorno=naive_dt)


def test_interrupcao_rejeita_retorno_antes_da_saida():
    with pytest.raises(ValueError, match="O retorno não pode ser anterior à saída"):
        Interrupcao(saida=INICIO, retorno=INICIO - timedelta(seconds=1))


# ==============================================================================
# Testes do Modo Estrito
# ==============================================================================


def test_modo_estrito_sempre_poda(sessao_60_min):
    politica = ModoEstrito()
    interrupcao = Interrupcao(saida=INICIO, retorno=INICIO + timedelta(seconds=5))

    assert politica.deve_podar(sessao_60_min, interrupcao, []) is True


# ==============================================================================
# Testes do Modo Tolerante
# ==============================================================================


def test_modo_tolerante_nao_poda_se_ainda_nao_retornou(sessao_60_min):
    politica = ModoTolerante(proporcao_tolerancia=0.10)
    interrupcao = Interrupcao(saida=INICIO)

    assert politica.deve_podar(sessao_60_min, interrupcao, []) is False


def test_modo_tolerante_nao_poda_se_dentro_do_limite(sessao_60_min):
    politica = ModoTolerante(proporcao_tolerancia=0.10)
    # Limite é 6 minutos. Saiu por 5 minutos.
    interrupcao = Interrupcao(saida=INICIO, retorno=INICIO + timedelta(minutes=5))

    assert politica.deve_podar(sessao_60_min, interrupcao, []) is False


def test_modo_tolerante_poda_se_estourar_limite_em_uma_saida(sessao_60_min):
    politica = ModoTolerante(proporcao_tolerancia=0.10)
    # Limite é 6 minutos. Saiu por 7 minutos.
    interrupcao = Interrupcao(saida=INICIO, retorno=INICIO + timedelta(minutes=7))

    assert politica.deve_podar(sessao_60_min, interrupcao, []) is True


def test_modo_tolerante_poda_somando_historico(sessao_60_min):
    politica = ModoTolerante(proporcao_tolerancia=0.10)

    # Já tinha saído por 4 minutos
    historico = [Interrupcao(saida=INICIO, retorno=INICIO + timedelta(minutes=4))]

    # Saiu por mais 3 minutos. Total = 7 minutos (estoura os 6 min de limite).
    nova = Interrupcao(
        saida=INICIO + timedelta(minutes=10), retorno=INICIO + timedelta(minutes=13)
    )

    assert politica.deve_podar(sessao_60_min, nova, historico) is True


# ==============================================================================
# Instante da poda
# ==============================================================================


def test_modo_estrito_poda_no_instante_da_saida(sessao_60_min):
    saida = INICIO + timedelta(minutes=10)
    interrupcao = Interrupcao(saida=saida, retorno=saida + timedelta(minutes=1))

    assert ModoEstrito().instante_da_poda(sessao_60_min, interrupcao, []) == saida


def test_modo_tolerante_poda_quando_o_saldo_acaba(sessao_60_min):
    politica = ModoTolerante(proporcao_tolerancia=0.10)
    # Limite de 6 minutos; já gastou 4. Saiu aos 10 min por mais 3: o saldo de 2 min
    # acaba aos 12 min, no meio da saída.
    historico = [Interrupcao(saida=INICIO, retorno=INICIO + timedelta(minutes=4))]
    saida = INICIO + timedelta(minutes=10)
    nova = Interrupcao(saida=saida, retorno=saida + timedelta(minutes=3))

    instante = politica.instante_da_poda(sessao_60_min, nova, historico)

    assert instante == saida + timedelta(minutes=2)
