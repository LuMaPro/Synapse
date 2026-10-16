from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.sessoes import SessaoService
from app.domain.excecoes import (
    DuracaoInvalida,
    HorarioInvalido,
    PoliticaInvalida,
    SessaoAtivaExistente,
    SessaoNaoEncontrada,
    TransicaoInvalida,
)
from tests.repositorios import RepositorioNeuronioMemoria, RepositorioSessaoMemoria

INICIO = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)


class Relogio:
    """Relógio do servidor controlado pelo teste."""

    def __init__(self, instante: datetime):
        self.instante = instante

    def __call__(self) -> datetime:
        return self.instante

    def avancar(self, **delta) -> None:
        self.instante += timedelta(**delta)


@pytest.fixture
def relogio():
    return Relogio(INICIO)


@pytest.fixture
def sessoes():
    return RepositorioSessaoMemoria()


@pytest.fixture
def neuronios():
    return RepositorioNeuronioMemoria()


@pytest.fixture
def servico(sessoes, neuronios, relogio):
    return SessaoService(sessoes, neuronios, relogio=relogio)


@pytest.fixture
def usuario_id():
    return uuid4()


def test_inicia_sessao_com_o_horario_do_servidor(servico, sessoes, usuario_id):
    sessao = servico.iniciar(usuario_id, 25, "tolerante")

    assert sessao.inicio == INICIO
    assert sessao.politica.codigo == "tolerante"
    assert sessoes.buscar_por_id(sessao.id) is sessao


def test_so_uma_sessao_ativa_por_usuario(servico, usuario_id):
    servico.iniciar(usuario_id, 25, "estrito")

    with pytest.raises(SessaoAtivaExistente):
        servico.iniciar(usuario_id, 25, "estrito")

    # Outro estudante pode iniciar a dele.
    servico.iniciar(uuid4(), 25, "estrito")


@pytest.mark.parametrize(
    ("duracao", "modo", "excecao"),
    [(7, "estrito", DuracaoInvalida), (25, "relaxado", PoliticaInvalida)],
)
def test_recusa_duracao_ou_modo_invalidos(servico, usuario_id, duracao, modo, excecao):
    with pytest.raises(excecao):
        servico.iniciar(usuario_id, duracao, modo)


def test_busca_a_sessao_ativa(servico, usuario_id):
    assert servico.buscar_ativa(usuario_id) is None

    sessao = servico.iniciar(usuario_id, 25, "estrito")

    assert servico.buscar_ativa(usuario_id) is sessao


def test_concluir_antes_da_hora_e_recusado(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=24)

    with pytest.raises(TransicaoInvalida):
        servico.concluir(usuario_id, sessao.id)


def test_concluir_ate_2_segundos_antes_conta_como_no_tempo(
    servico, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=-2)

    concluida, _ = servico.concluir(usuario_id, sessao.id)

    assert concluida.codigo_estado == "concluida"
    assert concluida.encerrada_em == sessao.fim_previsto


def test_concluir_3_segundos_antes_ainda_e_cedo(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=-3)

    with pytest.raises(TransicaoInvalida):
        servico.concluir(usuario_id, sessao.id)


def test_concluir_cria_o_neuronio(servico, neuronios, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=1)

    concluida, neuronio = servico.concluir(usuario_id, sessao.id)

    assert concluida.codigo_estado == "concluida"
    assert neuronio.sessao_id == sessao.id
    assert neuronio.usuario_id == usuario_id
    assert neuronio.duracao.minutos == 25
    assert neuronios.buscar_por_sessao(sessao.id) is neuronio


def test_interrupcao_no_estrito_poda_no_momento_da_saida(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=6)

    podada = servico.registrar_interrupcao(
        usuario_id, sessao.id, INICIO + timedelta(minutes=5), None
    )

    assert podada.codigo_estado == "podada"
    assert podada.encerrada_em == INICIO + timedelta(minutes=5)


def test_interrupcoes_no_tolerante_somam_ate_o_saldo(servico, usuario_id, relogio):
    # 10 min: saldo de 60 s.
    sessao = servico.iniciar(usuario_id, 10, "tolerante")
    relogio.avancar(minutes=5)
    saida = INICIO + timedelta(minutes=1)

    servico.registrar_interrupcao(
        usuario_id, sessao.id, saida, saida + timedelta(seconds=40)
    )
    assert sessao.codigo_estado == "em_andamento"

    saida = INICIO + timedelta(minutes=3)
    servico.registrar_interrupcao(
        usuario_id, sessao.id, saida, saida + timedelta(seconds=30)
    )
    assert sessao.codigo_estado == "podada"
    assert sessao.encerrada_em == saida + timedelta(seconds=20)


def test_recusa_saida_no_futuro(servico, usuario_id):
    sessao = servico.iniciar(usuario_id, 25, "tolerante")

    with pytest.raises(HorarioInvalido, match="futuro"):
        servico.registrar_interrupcao(
            usuario_id, sessao.id, INICIO + timedelta(minutes=1), None
        )


def test_recusa_saida_anterior_ao_inicio_da_sessao(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "tolerante")
    relogio.avancar(minutes=5)
    antes = INICIO - timedelta(seconds=30)

    with pytest.raises(HorarioInvalido, match="anterior ao início"):
        servico.registrar_interrupcao(
            usuario_id, sessao.id, antes, antes + timedelta(seconds=10)
        )
    assert sessao.historico_interrupcoes == []


def test_desistir_conta_como_poda(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=3)

    podada = servico.desistir(usuario_id, sessao.id)

    assert podada.codigo_estado == "podada"
    assert podada.encerrada_em == INICIO + timedelta(minutes=3)


@pytest.mark.parametrize("acao", ["concluir", "desistir"])
def test_sessao_de_outro_usuario_responde_como_inexistente(servico, usuario_id, acao):
    sessao = servico.iniciar(usuario_id, 25, "estrito")

    with pytest.raises(SessaoNaoEncontrada):
        getattr(servico, acao)(uuid4(), sessao.id)
    with pytest.raises(SessaoNaoEncontrada):
        getattr(servico, acao)(usuario_id, uuid4())


def test_sessao_abandonada_e_podada_ao_ser_acessada(
    servico, sessoes, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=31)

    assert servico.buscar_ativa(usuario_id) is None
    assert sessoes.buscar_por_id(sessao.id).codigo_estado == "podada"
    with pytest.raises(TransicaoInvalida):
        servico.concluir(usuario_id, sessao.id)
    # Com a órfã podada, o estudante pode começar outra.
    servico.iniciar(usuario_id, 25, "estrito")


def test_podar_orfas_varre_todos_os_usuarios(servico, relogio):
    abandonadas = [servico.iniciar(uuid4(), 10, "estrito") for _ in range(2)]
    relogio.avancar(minutes=14)
    recente = servico.iniciar(uuid4(), 25, "estrito")
    relogio.avancar(minutes=2)  # as de 10 min passaram de 15 min; a recente não

    assert servico.podar_orfas() == 2
    assert all(s.codigo_estado == "podada" for s in abandonadas)
    assert recente.codigo_estado == "em_andamento"
