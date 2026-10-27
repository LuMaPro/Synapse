from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.loja import LojaService
from app.application.materias import MateriaService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.excecoes import (
    CorBloqueada,
    CorInvalida,
    CorNaoEncontrada,
    SaldoInsuficiente,
)
from app.domain.loja import CorLoja
from app.domain.observadores import AtualizadorRede, CreditadorATP
from tests.repositorios import (
    RepositorioCarteiraMemoria,
    RepositorioMateriaMemoria,
    RepositorioRedeNeuralMemoria,
    RepositorioSessaoMemoria,
)

INICIO = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
MAGENTA = "#FF3DF0"  # Magenta neon, 250 ATP


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
def carteiras():
    return RepositorioCarteiraMemoria()


@pytest.fixture
def loja(carteiras, relogio):
    return LojaService(carteiras, relogio=relogio)


def _situacao(vitrine, codigo):
    return next(s for s in vitrine.cores if s.cor.codigo == codigo)


# ------------------------------------------------------------------ loja


def test_vitrine_de_estudante_novo(loja):
    vitrine = loja.consultar(uuid4())

    assert vitrine.saldo == 0
    assert len(vitrine.cores) == 8 + 12
    assert all(s.desbloqueada for s in vitrine.cores if s.cor.gratuita)
    assert not any(s.desbloqueada for s in vitrine.cores if not s.cor.gratuita)


def test_creditar_sessao_guarda_o_atp(loja, carteiras):
    usuario = uuid4()

    assert loja.creditar_sessao(usuario, 45) == 45
    loja.creditar_sessao(usuario, 25)

    assert carteiras.carregar(usuario).saldo == 70


def test_comprar_grava_e_devolve_a_vitrine_atualizada(loja, carteiras, relogio):
    usuario = uuid4()
    loja.creditar_sessao(usuario, 120)
    loja.creditar_sessao(usuario, 120)
    loja.creditar_sessao(usuario, 120)

    vitrine = loja.comprar(usuario, "magenta_neon")

    assert vitrine.saldo == 110
    assert _situacao(vitrine, "magenta_neon").desbloqueada
    guardada = carteiras.carregar(usuario)
    assert guardada.saldo == 110
    assert guardada.desbloqueadas == {"magenta_neon": relogio.instante}


def test_compra_sem_saldo_nao_grava_nada(loja, carteiras):
    usuario = uuid4()
    loja.creditar_sessao(usuario, 60)

    with pytest.raises(SaldoInsuficiente):
        loja.comprar(usuario, "lavanda")

    assert carteiras.carregar(usuario).saldo == 60


def test_cor_fora_da_loja(loja):
    with pytest.raises(CorNaoEncontrada):
        loja.comprar(uuid4(), "unicornio")


def test_carteiras_de_estudantes_diferentes_nao_se_misturam(loja):
    usuario, outro = uuid4(), uuid4()
    loja.creditar_sessao(usuario, 100)

    assert loja.consultar(outro).saldo == 0


def test_cor_disponivel_para_uma_materia(loja):
    usuario = uuid4()

    assert loja.exigir_cor_disponivel(usuario, "#8b7bff").codigo == "violeta"
    with pytest.raises(CorBloqueada, match="Compre a cor Magenta neon"):
        loja.exigir_cor_disponivel(usuario, MAGENTA)
    with pytest.raises(CorInvalida):
        loja.exigir_cor_disponivel(usuario, "#123456")

    for _ in range(3):
        loja.creditar_sessao(usuario, 120)
    loja.comprar(usuario, "magenta_neon")
    assert loja.exigir_cor_disponivel(usuario, MAGENTA).codigo == "magenta_neon"


@pytest.mark.parametrize(
    "catalogo",
    [
        [CorLoja("a", "A", "#111111"), CorLoja("a", "B", "#222222")],
        [CorLoja("a", "A", "#111111"), CorLoja("b", "B", "#111111")],
    ],
)
def test_recusa_catalogo_com_codigo_ou_cor_repetidos(carteiras, catalogo):
    with pytest.raises(ValueError):
        LojaService(carteiras, catalogo=catalogo)


# ------------------------------------------------------------------ matérias


@pytest.fixture
def materias(loja):
    return MateriaService(RepositorioMateriaMemoria(), loja)


def test_criterio_materia_so_usa_cor_gratuita_ou_comprada(materias, loja):
    usuario = uuid4()

    assert materias.criar(usuario, "Cálculo", "#8B7BFF").cor == "#8B7BFF"
    with pytest.raises(CorBloqueada):
        materias.criar(usuario, "Física", MAGENTA)
    with pytest.raises(CorInvalida):
        materias.criar(usuario, "Física", "#123456")

    for _ in range(3):
        loja.creditar_sessao(usuario, 120)
    loja.comprar(usuario, "magenta_neon")
    assert materias.criar(usuario, "Física", MAGENTA).cor == MAGENTA


def test_editar_para_uma_cor_bloqueada_e_recusado_e_nada_muda(materias):
    usuario = uuid4()
    materia = materias.criar(usuario, "Cálculo", "#8B7BFF")

    with pytest.raises(CorBloqueada):
        materias.atualizar(usuario, materia.id, cor=MAGENTA)

    assert materias.buscar(usuario, materia.id).cor == "#8B7BFF"


def test_cor_antiga_fora_da_paleta_continua_ao_editar_so_o_nome(loja):
    # Matéria criada antes da paleta valer (ex.: pela API, com qualquer cor).
    repo = RepositorioMateriaMemoria()
    usuario = uuid4()
    materia = MateriaService(repo).criar(usuario, "Química", "#123456")

    renomeada = MateriaService(repo, loja).atualizar(
        usuario, materia.id, nome="Química orgânica", cor="#123456"
    )

    assert renomeada.cor == "#123456"


# ------------------------------------------------------------------ observador


@pytest.fixture
def sessao_service(loja, relogio):
    """Montado como a API: o CreditadorATP inscrito em SessaoConcluida."""
    publicador = PublicadorEventos()
    atualizador = AtualizadorRede(RedeNeuralService(RepositorioRedeNeuralMemoria()))
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    publicador.inscrever(SessaoConcluida, CreditadorATP(loja))
    return SessaoService(RepositorioSessaoMemoria(), publicador, relogio=relogio)


def _concluir(servico, relogio, usuario, duracao):
    sessao = servico.iniciar(usuario, duracao, "estrito")
    relogio.avancar(minutes=duracao)
    return servico.concluir(usuario, sessao.id)


def test_criterio_concluir_a_sessao_credita_o_atp(sessao_service, loja, relogio):
    usuario = uuid4()

    _concluir(sessao_service, relogio, usuario, 45)
    _concluir(sessao_service, relogio, usuario, 25)

    assert loja.consultar(usuario).saldo == 70


def test_sessao_podada_nao_rende_atp(sessao_service, loja, relogio):
    usuario = uuid4()
    sessao = sessao_service.iniciar(usuario, 120, "estrito")
    relogio.avancar(minutes=110)

    sessao_service.desistir(usuario, sessao.id)

    assert loja.consultar(usuario).saldo == 0


def test_o_creditador_ignora_sessoes_podadas():
    loja = Mock(spec=LojaService)
    creditador = CreditadorATP(loja)

    creditador.processar(SessaoPodada(uuid4(), uuid4(), 25, INICIO))
    assert not loja.creditar_sessao.called

    usuario = uuid4()
    creditador.processar(SessaoConcluida(uuid4(), usuario, 25, INICIO))
    loja.creditar_sessao.assert_called_once_with(usuario, 25)
