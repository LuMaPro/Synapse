from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.conquistas import ConquistaService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.conquistas import CATALOGO_CONQUISTAS, PrimeiroNeuronio, Sequencia
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.entidades.neuronio import Neuronio
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.observadores import AtualizadorRede, AvaliadorConquistas
from tests.repositorios import (
    RepositorioConquistaMemoria,
    RepositorioRedeNeuralMemoria,
    RepositorioSessaoMemoria,
)

# 14h em Brasília.
INICIO = datetime(2026, 10, 20, 17, 0, tzinfo=UTC)


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
def redes():
    return RepositorioRedeNeuralMemoria()


@pytest.fixture
def repo_conquistas():
    return RepositorioConquistaMemoria()


@pytest.fixture
def servico(repo_conquistas, redes, relogio):
    return ConquistaService(repo_conquistas, redes, relogio=relogio)


def _formar_neuronio(redes, usuario, duracao=25, quando=INICIO, *, vivo=True):
    """Coloca na rede o neurônio de uma sessão terminada em `quando`."""
    rede = redes.carregar(usuario)
    rede.adicionar(Neuronio(usuario, uuid4(), duracao, vivo=vivo, criado_em=quando))
    redes.salvar(rede)


def _codigos(conquistas) -> list[str]:
    return [c.codigo for c in conquistas]


# ------------------------------------------------------------------ avaliar


def test_desbloqueia_a_conquista_cumprida_com_a_data_informada(servico, redes):
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    quando = INICIO + timedelta(minutes=25)

    novas = servico.avaliar(usuario, quando)

    assert _codigos(novas) == ["primeiro_neuronio"]
    assert novas[0].usuario_id == usuario
    assert novas[0].desbloqueada_em == quando


def test_cada_conquista_e_desbloqueada_uma_vez_so(servico, redes, repo_conquistas):
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    servico.avaliar(usuario)
    _formar_neuronio(redes, usuario, quando=INICIO + timedelta(hours=1))

    assert servico.avaliar(usuario) == []
    assert len(repo_conquistas) == 1


def test_sem_data_usa_o_relogio(servico, redes, relogio):
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    relogio.avancar(hours=2)

    [conquista] = servico.avaliar(usuario)

    assert conquista.desbloqueada_em == relogio.instante


def test_sessoes_podadas_nao_desbloqueiam_nada(servico, redes):
    usuario = uuid4()
    _formar_neuronio(redes, usuario, duracao=120, vivo=False)

    assert servico.avaliar(usuario) == []


def test_desbloqueia_varias_de_uma_vez(servico, redes):
    usuario = uuid4()
    # Uma sessão de 2 h por dia, 7 dias seguidos.
    for dia in range(7):
        _formar_neuronio(redes, usuario, 120, INICIO + timedelta(days=dia))

    novas = servico.avaliar(usuario, INICIO + timedelta(days=6, hours=2))

    # 14 h focadas, 7 dias e sessões de 2 h; as 11 sinapses não chegam a 100.
    assert _codigos(novas) == [
        "primeiro_neuronio",
        "horas_focadas_10",
        "dias_seguidos_7",
        "sessao_sem_poda_120",
    ]


def test_conquistas_de_um_estudante_nao_valem_para_outro(servico, redes):
    usuario, outro = uuid4(), uuid4()
    _formar_neuronio(redes, usuario)
    servico.avaliar(usuario)

    assert servico.avaliar(outro) == []
    assert not servico.consultar(outro).conquistas[0].desbloqueada


# ------------------------------------------------------------------ consultar


def test_consulta_traz_todas_as_conquistas_bloqueadas_e_desbloqueadas(
    servico, redes, relogio
):
    usuario = uuid4()
    for dia in range(3):
        _formar_neuronio(redes, usuario, 50, INICIO + timedelta(days=dia))
    servico.avaliar(usuario, INICIO + timedelta(days=2))
    relogio.avancar(days=3)

    painel = servico.consultar(usuario)

    # Sem sessão hoje (dia 23), a sequência de ontem ainda vale.
    assert painel.sequencia == Sequencia(atual=3, recorde=3)
    assert [c.regra for c in painel.conquistas] == list(CATALOGO_CONQUISTAS)
    situacao = {c.regra.codigo: c for c in painel.conquistas}
    assert situacao["primeiro_neuronio"].desbloqueada
    assert situacao["primeiro_neuronio"].desbloqueada_em == INICIO + timedelta(days=2)
    assert situacao["primeiro_neuronio"].progresso == 1
    assert not situacao["horas_focadas_10"].desbloqueada
    assert situacao["horas_focadas_10"].desbloqueada_em is None
    assert situacao["horas_focadas_10"].progresso == 150
    assert situacao["dias_seguidos_7"].progresso == 3
    assert situacao["sinapses_100"].progresso == 3
    assert situacao["sessao_sem_poda_120"].progresso == 50


def test_a_sequencia_zera_quando_passa_um_dia_inteiro_sem_sessao(
    servico, redes, relogio
):
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    relogio.avancar(days=2)

    assert servico.consultar(usuario).sequencia == Sequencia(atual=0, recorde=1)


def test_estudante_novo_ve_tudo_bloqueado(servico):
    painel = servico.consultar(uuid4())

    assert painel.sequencia == Sequencia(0, 0)
    assert not any(c.desbloqueada for c in painel.conquistas)
    assert all(c.progresso == 0 for c in painel.conquistas)


def test_consulta_desbloqueia_o_que_ja_estava_cumprido(servico, redes, relogio):
    # Quem já focava antes de as conquistas existirem: nenhum `avaliar` rodou.
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    relogio.avancar(days=1)

    painel = servico.consultar(usuario)

    assert painel.conquistas[0].desbloqueada_em == relogio.instante
    assert servico.avaliar(usuario) == []


def test_ignora_conquista_guardada_que_saiu_do_catalogo(
    servico, redes, repo_conquistas
):
    usuario = uuid4()
    repo_conquistas.salvar(ConquistaDesbloqueada(usuario, "aposentada", INICIO))

    painel = servico.consultar(usuario)

    assert "aposentada" not in [c.regra.codigo for c in painel.conquistas]


def test_o_catalogo_pode_ser_trocado(repo_conquistas, redes):
    usuario = uuid4()
    _formar_neuronio(redes, usuario)
    servico = ConquistaService(repo_conquistas, redes, regras=[PrimeiroNeuronio()])

    assert [c.regra.codigo for c in servico.consultar(usuario).conquistas] == [
        "primeiro_neuronio"
    ]


def test_recusa_catalogo_com_codigo_repetido(repo_conquistas, redes):
    with pytest.raises(ValueError):
        ConquistaService(
            repo_conquistas, redes, regras=[PrimeiroNeuronio(), PrimeiroNeuronio()]
        )


# ------------------------------------------------------------------ observador


@pytest.fixture
def sessoes():
    return RepositorioSessaoMemoria()


def _sessao_service(sessoes, redes, repo_conquistas, relogio, *, avaliador_antes=False):
    """Monta o publicador como a API: o avaliador depois do atualizador da rede."""
    atualizador = AtualizadorRede(RedeNeuralService(redes))
    avaliador = AvaliadorConquistas(ConquistaService(repo_conquistas, redes))
    publicador = PublicadorEventos()
    if avaliador_antes:
        publicador.inscrever(SessaoConcluida, avaliador)
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    if not avaliador_antes:
        publicador.inscrever(SessaoConcluida, avaliador)
    return SessaoService(sessoes, publicador, relogio=relogio)


def _concluir(servico, relogio, usuario, duracao=25):
    sessao = servico.iniciar(usuario, duracao, "estrito")
    relogio.avancar(minutes=duracao)
    sessao, _ = servico.concluir(usuario, sessao.id)
    return sessao


def test_criterio_concluir_a_primeira_sessao_desbloqueia_o_primeiro_neuronio(
    sessoes, redes, repo_conquistas, relogio
):
    servico = _sessao_service(sessoes, redes, repo_conquistas, relogio)
    usuario = uuid4()

    sessao = _concluir(servico, relogio, usuario)

    [conquista] = repo_conquistas.listar_por_usuario(usuario)
    assert conquista.codigo == "primeiro_neuronio"
    # A data é a da conclusão: a tela pode avisar o que a sessão desbloqueou.
    assert conquista.desbloqueada_em == sessao.encerrada_em


def test_desistir_nao_desbloqueia_nada(sessoes, redes, repo_conquistas, relogio):
    servico = _sessao_service(sessoes, redes, repo_conquistas, relogio)
    usuario = uuid4()
    sessao = servico.iniciar(usuario, 120, "estrito")
    relogio.avancar(minutes=100)

    servico.desistir(usuario, sessao.id)

    assert repo_conquistas.listar_por_usuario(usuario) == []


def test_criterio_cem_sinapses(sessoes, redes, repo_conquistas, relogio):
    servico = _sessao_service(sessoes, redes, repo_conquistas, relogio)
    usuario = uuid4()

    # Cada neurônio novo se liga aos 2 mais recentes: 99 sinapses com 51 sessões.
    for _ in range(51):
        _concluir(servico, relogio, usuario, duracao=10)
    assert "sinapses_100" not in _codigos(repo_conquistas.listar_por_usuario(usuario))

    ultima = _concluir(servico, relogio, usuario, duracao=10)

    desbloqueadas = {
        c.codigo: c.desbloqueada_em for c in repo_conquistas.listar_por_usuario(usuario)
    }
    assert desbloqueadas["sinapses_100"] == ultima.encerrada_em


def test_criterio_sete_dias_seguidos(sessoes, redes, repo_conquistas, relogio):
    servico = _sessao_service(sessoes, redes, repo_conquistas, relogio)
    usuario = uuid4()

    for _ in range(6):
        _concluir(servico, relogio, usuario)
        relogio.avancar(days=1)
    assert "dias_seguidos_7" not in _codigos(
        repo_conquistas.listar_por_usuario(usuario)
    )

    _concluir(servico, relogio, usuario)

    assert "dias_seguidos_7" in _codigos(repo_conquistas.listar_por_usuario(usuario))


def test_o_avaliador_precisa_vir_depois_do_atualizador_da_rede(
    sessoes, redes, repo_conquistas, relogio
):
    # Inscrito antes, ele olha a rede sem o neurônio da sessão que acabou.
    servico = _sessao_service(
        sessoes, redes, repo_conquistas, relogio, avaliador_antes=True
    )
    usuario = uuid4()

    _concluir(servico, relogio, usuario)

    assert repo_conquistas.listar_por_usuario(usuario) == []


def test_o_avaliador_ignora_sessoes_podadas():
    conquistas = Mock(spec=ConquistaService)
    avaliador = AvaliadorConquistas(conquistas)

    avaliador.processar(SessaoPodada(uuid4(), uuid4(), 25, INICIO))
    assert not conquistas.avaliar.called

    usuario = uuid4()
    avaliador.processar(SessaoConcluida(uuid4(), usuario, 25, INICIO))
    conquistas.avaliar.assert_called_once_with(usuario, INICIO)
