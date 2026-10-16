from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.duracao import Duracao
from app.domain.entidades import SessaoFoco
from app.domain.excecoes import (
    DuracaoInvalida,
    ErroDominio,
    HorarioInvalido,
    TransicaoInvalida,
)
from app.domain.politica_interrupcao import Interrupcao, ModoEstrito, ModoTolerante

INICIO = datetime(2026, 10, 12, 14, 0, tzinfo=UTC)


def test_cria_sessao_com_duracao_e_horarios():
    usuario_id = uuid4()

    sessao = SessaoFoco(usuario_id, 25, inicio=INICIO)

    assert isinstance(sessao.id, UUID)
    assert sessao.usuario_id == usuario_id
    assert sessao.duracao == Duracao(25)
    assert sessao.inicio == INICIO
    assert sessao.fim_previsto == INICIO + timedelta(minutes=25)
    assert sessao.encerrada_em is None


def test_inicio_padrao_e_agora():
    antes = datetime.now(UTC)
    sessao = SessaoFoco(uuid4(), 25)

    assert antes <= sessao.inicio <= datetime.now(UTC)


@pytest.mark.parametrize("duracao", [0, 5, 9, 121, 23, 25.5, "25", None])
def test_duracao_invalida_lanca_excecao_de_dominio(duracao):
    with pytest.raises(DuracaoInvalida) as erro:
        SessaoFoco(uuid4(), duracao, inicio=INICIO)

    assert isinstance(erro.value, ErroDominio)


def test_recusa_inicio_sem_fuso():
    with pytest.raises(HorarioInvalido):
        SessaoFoco(uuid4(), 25, inicio=datetime(2026, 10, 12, 14, 0))


def test_reconstroi_sessao_encerrada():
    encerrada_em = INICIO + timedelta(minutes=25)

    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, encerrada_em=encerrada_em)

    assert sessao.encerrada_em == encerrada_em


def test_recusa_sessao_que_termina_antes_de_comecar():
    with pytest.raises(HorarioInvalido, match="antes de começar"):
        SessaoFoco(
            uuid4(), 25, inicio=INICIO, encerrada_em=INICIO - timedelta(seconds=1)
        )


def test_recusa_encerramento_sem_fuso():
    with pytest.raises(HorarioInvalido):
        SessaoFoco(
            uuid4(), 25, inicio=INICIO, encerrada_em=datetime(2026, 10, 12, 15, 0)
        )


@pytest.mark.parametrize(
    "atributo",
    ["id", "usuario_id", "duracao", "inicio", "fim_previsto", "encerrada_em", "estado"],
)
def test_atributos_sao_somente_leitura(atributo):
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO)

    with pytest.raises(AttributeError):
        setattr(sessao, atributo, "outro valor")


def test_sessoes_sao_iguais_quando_tem_o_mesmo_id():
    id_comum = uuid4()

    assert SessaoFoco(uuid4(), 25, id=id_comum) == SessaoFoco(uuid4(), 60, id=id_comum)
    assert SessaoFoco(uuid4(), 25) != SessaoFoco(uuid4(), 25)


def test_repr_mostra_id_usuario_duracao_e_estado():
    sessao = SessaoFoco(uuid4(), 25)

    assert repr(sessao) == (
        f"SessaoFoco(id={sessao.id}, usuario_id={sessao.usuario_id}, "
        f"duracao=25 min, estado=em andamento)"
    )


# ==============================================================================
# Testes do Ciclo de Vida da Sessão (Padrão State - Issue #10)
# ==============================================================================


@pytest.fixture
def relogio_fixo():
    """Injeta a hora de INICIO para testes de transição."""

    def _relogio():
        return INICIO

    return _relogio


@pytest.fixture
def relogio_futuro():
    """Injeta uma hora bem posterior ao fim da sessão padrão de 25 min."""

    def _relogio():
        return INICIO + timedelta(minutes=45)

    return _relogio


@pytest.fixture
def sessao_padrao(relogio_fixo):
    return SessaoFoco(usuario_id=uuid4(), duracao_minutos=25, inicio=relogio_fixo())


def test_sessao_inicia_em_andamento(sessao_padrao):
    assert sessao_padrao.estado == "em andamento"
    assert sessao_padrao.encerrada_em is None


def test_concluir_sessao_antes_do_tempo_lanca_excecao(sessao_padrao, relogio_fixo):
    with pytest.raises(
        TransicaoInvalida,
        match="A sessão ainda não atingiu a duração planejada",
    ):
        sessao_padrao.concluir(relogio=relogio_fixo)


def test_concluir_sessao_apos_tempo_planejado(sessao_padrao, relogio_futuro):
    sessao_padrao.concluir(relogio=relogio_futuro)

    assert sessao_padrao.estado == "concluída"
    assert sessao_padrao.encerrada_em == relogio_futuro()


def test_podar_sessao_em_andamento(sessao_padrao, relogio_fixo):
    sessao_padrao.podar(relogio=relogio_fixo)

    assert sessao_padrao.estado == "podada"
    assert sessao_padrao.encerrada_em == relogio_fixo()


def test_desistir_sessao_em_andamento(sessao_padrao, relogio_fixo):
    sessao_padrao.desistir(relogio=relogio_fixo)

    assert sessao_padrao.estado == "podada"
    assert sessao_padrao.encerrada_em == relogio_fixo()


def test_transicoes_invalidas_sessao_concluida(sessao_padrao, relogio_futuro):
    sessao_padrao.concluir(relogio=relogio_futuro)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível concluir uma sessão concluída",
    ):
        sessao_padrao.concluir(relogio=relogio_futuro)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível podar uma sessão concluída",
    ):
        sessao_padrao.podar(relogio=relogio_futuro)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível desistir de uma sessão concluída",
    ):
        sessao_padrao.desistir(relogio=relogio_futuro)


def test_transicoes_invalidas_sessao_podada(sessao_padrao, relogio_fixo):
    sessao_padrao.podar(relogio=relogio_fixo)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível concluir uma sessão podada",
    ):
        sessao_padrao.concluir(relogio=relogio_fixo)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível podar uma sessão podada",
    ):
        sessao_padrao.podar(relogio=relogio_fixo)

    with pytest.raises(
        TransicaoInvalida,
        match="Não é possível desistir de uma sessão podada",
    ):
        sessao_padrao.desistir(relogio=relogio_fixo)


@pytest.mark.parametrize("transicao", ["concluir", "podar", "desistir"])
def test_recusa_instante_sem_fuso_vindo_do_relogio(sessao_padrao, transicao):
    sem_fuso = datetime(2026, 10, 12, 15, 0)

    with pytest.raises(HorarioInvalido):
        getattr(sessao_padrao, transicao)(relogio=lambda: sem_fuso)

    assert sessao_padrao.codigo_estado == "em_andamento"
    assert sessao_padrao.encerrada_em is None


@pytest.mark.parametrize("transicao", ["podar", "desistir"])
def test_recusa_instante_anterior_ao_inicio(sessao_padrao, transicao):
    antes_do_inicio = INICIO - timedelta(seconds=1)

    with pytest.raises(HorarioInvalido, match="antes de começar"):
        getattr(sessao_padrao, transicao)(relogio=lambda: antes_do_inicio)

    assert sessao_padrao.codigo_estado == "em_andamento"


def test_codigo_do_estado_e_estavel_e_sem_acento(
    sessao_padrao, relogio_fixo, relogio_futuro
):
    assert sessao_padrao.codigo_estado == "em_andamento"

    concluida = SessaoFoco(uuid4(), 25, inicio=INICIO)
    concluida.concluir(relogio=relogio_futuro)
    assert concluida.codigo_estado == "concluida"

    sessao_padrao.podar(relogio=relogio_fixo)
    assert sessao_padrao.codigo_estado == "podada"


# ==============================================================================
# Interrupções e política (Strategy - Issue #11)
# ==============================================================================


def _saida(minuto: float, segundos_fora: float) -> Interrupcao:
    saida = INICIO + timedelta(minutes=minuto)
    return Interrupcao(saida=saida, retorno=saida + timedelta(seconds=segundos_fora))


def test_politica_padrao_e_o_modo_estrito():
    assert isinstance(SessaoFoco(uuid4(), 25, inicio=INICIO).politica, ModoEstrito)


def test_modo_estrito_poda_no_instante_da_saida():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoEstrito())

    sessao.registrar_interrupcao(_saida(minuto=5, segundos_fora=60))

    assert sessao.codigo_estado == "podada"
    assert sessao.encerrada_em == INICIO + timedelta(minutes=5)
    assert sessao.historico_interrupcoes == []


def test_modo_tolerante_guarda_saidas_dentro_do_saldo():
    # 25 min: saldo de 10% = 150 s
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoTolerante())

    sessao.registrar_interrupcao(_saida(minuto=5, segundos_fora=60))
    sessao.registrar_interrupcao(_saida(minuto=10, segundos_fora=90))

    assert sessao.codigo_estado == "em_andamento"
    assert len(sessao.historico_interrupcoes) == 2


def test_modo_tolerante_poda_no_instante_em_que_o_saldo_acaba():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoTolerante())
    sessao.registrar_interrupcao(_saida(minuto=5, segundos_fora=60))

    # Restam 90 s de saldo; saiu aos 10 min por 10 min: morre aos 10 min e 90 s.
    sessao.registrar_interrupcao(_saida(minuto=10, segundos_fora=600))

    assert sessao.codigo_estado == "podada"
    assert sessao.encerrada_em == INICIO + timedelta(minutes=10, seconds=90)


def test_poda_nao_usa_a_hora_em_que_o_aviso_chega():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoEstrito())

    # Mesmo registrando bem depois, a poda vale para o momento da saída.
    sessao.registrar_interrupcao(_saida(minuto=2, segundos_fora=1))

    assert sessao.encerrada_em == INICIO + timedelta(minutes=2)


def test_recusa_poda_por_saida_anterior_ao_inicio():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoEstrito())

    with pytest.raises(HorarioInvalido):
        sessao.registrar_interrupcao(_saida(minuto=-10, segundos_fora=5))

    assert sessao.codigo_estado == "em_andamento"


@pytest.mark.parametrize("encerrar", ["podar", "concluir"])
def test_sessao_encerrada_nao_aceita_interrupcao(encerrar, relogio_futuro):
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, politica=ModoTolerante())
    getattr(sessao, encerrar)(relogio=relogio_futuro)

    with pytest.raises(TransicaoInvalida, match="Não é possível interromper"):
        sessao.registrar_interrupcao(_saida(minuto=5, segundos_fora=10))


# ==============================================================================
# Sessão abandonada, histórico e tempo (Issue #16)
# ==============================================================================


def test_sessao_em_andamento_expira_depois_de_duracao_mais_5_min():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO)

    assert sessao.expirar_se_abandonada(INICIO + timedelta(minutes=30)) is False
    assert sessao.codigo_estado == "em_andamento"

    assert sessao.expirar_se_abandonada(INICIO + timedelta(hours=3)) is True
    assert sessao.codigo_estado == "podada"
    # A poda vale a partir do limite, não da hora em que alguém percebeu.
    assert sessao.encerrada_em == INICIO + timedelta(minutes=30)


@pytest.mark.parametrize("encerrar", ["podar", "concluir"])
def test_sessao_encerrada_nao_expira(encerrar, relogio_futuro):
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO)
    getattr(sessao, encerrar)(relogio=relogio_futuro)
    encerrada_em = sessao.encerrada_em

    assert sessao.expirar_se_abandonada(INICIO + timedelta(hours=3)) is False
    assert sessao.encerrada_em == encerrada_em


def test_reconstroi_sessao_com_historico_e_soma_o_tempo_fora():
    historico = [_saida(minuto=2, segundos_fora=30), _saida(minuto=8, segundos_fora=45)]

    sessao = SessaoFoco(
        uuid4(), 25, inicio=INICIO, politica=ModoTolerante(), interrupcoes=historico
    )

    assert sessao.historico_interrupcoes == historico
    assert sessao.tempo_fora == timedelta(seconds=75)
    # O saldo de 150 s considera o histórico: mais 80 s estouram.
    sessao.registrar_interrupcao(_saida(minuto=12, segundos_fora=80))
    assert sessao.codigo_estado == "podada"


def test_restante_em_calcula_ate_o_fim_previsto_e_nao_fica_negativo():
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO)

    assert sessao.restante_em(INICIO + timedelta(minutes=10)) == timedelta(minutes=15)
    assert sessao.restante_em(INICIO + timedelta(hours=1)) == timedelta(0)
