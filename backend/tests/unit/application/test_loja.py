from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.loja import FabricaDoEstudante, LojaService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.entidades.neuronio import Granular, Piramidal, VarianteCor
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.excecoes import SaldoInsuficiente, TipoBloqueado, TipoNaoEncontrado
from app.domain.loja import ItemLoja
from app.domain.observadores import AtualizadorRede, CreditadorATP
from tests.repositorios import (
    RepositorioCarteiraMemoria,
    RepositorioRedeNeuralMemoria,
    RepositorioSessaoMemoria,
)

INICIO = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)


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
    return next(s for s in vitrine.itens if s.item.codigo == codigo)


# ------------------------------------------------------------------ casos de uso


def test_vitrine_de_estudante_novo(loja):
    vitrine = loja.consultar(uuid4())

    assert vitrine.saldo == 0
    assert len(vitrine.itens) == 9
    originais = [s for s in vitrine.itens if s.item.gratuito]
    assert all(s.desbloqueado and s.em_uso for s in originais)
    variacoes = [s for s in vitrine.itens if not s.item.gratuito]
    assert not any(s.desbloqueado or s.em_uso for s in variacoes)


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

    vitrine = loja.comprar(usuario, "piramidal_rosa")

    assert vitrine.saldo == 110
    rosa = _situacao(vitrine, "piramidal_rosa")
    assert rosa.desbloqueado and rosa.em_uso
    assert not _situacao(vitrine, "piramidal").em_uso
    guardada = carteiras.carregar(usuario)
    assert guardada.saldo == 110
    assert guardada.desbloqueados == {"piramidal_rosa": relogio.instante}


def test_compra_sem_saldo_nao_grava_nada(loja, carteiras):
    usuario = uuid4()
    loja.creditar_sessao(usuario, 60)

    with pytest.raises(SaldoInsuficiente):
        loja.comprar(usuario, "granular_lima")

    assert carteiras.carregar(usuario).saldo == 60


def test_usar_troca_o_tipo_em_uso(loja):
    usuario = uuid4()
    for _ in range(3):
        loja.creditar_sessao(usuario, 120)
    loja.comprar(usuario, "piramidal_rosa")

    vitrine = loja.usar(usuario, "piramidal")

    assert _situacao(vitrine, "piramidal").em_uso
    assert not _situacao(vitrine, "piramidal_rosa").em_uso
    assert _situacao(vitrine, "piramidal_rosa").desbloqueado
    assert loja.tipos_em_uso(usuario)[1] == Piramidal()


def test_usar_tipo_nao_comprado_e_recusado(loja):
    with pytest.raises(TipoBloqueado):
        loja.usar(uuid4(), "piramidal_rosa")


@pytest.mark.parametrize("acao", ["comprar", "usar"])
def test_tipo_fora_da_loja(loja, acao):
    with pytest.raises(TipoNaoEncontrado):
        getattr(loja, acao)(uuid4(), "unicornio")


def test_carteiras_de_estudantes_diferentes_nao_se_misturam(loja):
    usuario, outro = uuid4(), uuid4()
    loja.creditar_sessao(usuario, 100)

    assert loja.consultar(outro).saldo == 0


def test_catalogo_proprio(carteiras):
    violeta = VarianteCor(Granular(), "granular_violeta", "Violeta", "#8B00FF")
    loja = LojaService(
        carteiras, catalogo=[ItemLoja(Granular(), 0), ItemLoja(violeta, 10)]
    )

    assert [s.item.codigo for s in loja.consultar(uuid4()).itens] == [
        "granular",
        "granular_violeta",
    ]


@pytest.mark.parametrize(
    "catalogo",
    [
        # Código repetido.
        [ItemLoja(Granular(), 0), ItemLoja(Granular(), 0)],
        # Variação sem o original gratuito da forma.
        [ItemLoja(VarianteCor(Piramidal(), "p", "P", "#000000"), 10)],
        # Dois gratuitos para a mesma forma.
        [
            ItemLoja(Piramidal(), 0),
            ItemLoja(VarianteCor(Piramidal(), "p", "P", "#000000"), 0),
        ],
    ],
)
def test_recusa_catalogo_mal_formado(carteiras, catalogo):
    with pytest.raises(ValueError):
        LojaService(carteiras, catalogo=catalogo)


# ------------------------------------------------------------- observador e fábrica


@pytest.fixture
def redes():
    return RepositorioRedeNeuralMemoria()


@pytest.fixture
def sessao_service(loja, redes, relogio):
    """Montado como a API: a fábrica do estudante e o CreditadorATP inscrito."""
    publicador = PublicadorEventos()
    atualizador = AtualizadorRede(RedeNeuralService(redes))
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    publicador.inscrever(SessaoConcluida, CreditadorATP(loja))
    return SessaoService(
        RepositorioSessaoMemoria(),
        publicador,
        relogio=relogio,
        fabrica=FabricaDoEstudante(loja),
    )


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


def test_criterio_a_fabrica_usa_o_tipo_escolhido_na_loja(
    sessao_service, loja, relogio, redes
):
    usuario = uuid4()
    for _ in range(3):
        _concluir(sessao_service, relogio, usuario, 120)
    _, antes = _concluir(sessao_service, relogio, usuario, 25)
    loja.comprar(usuario, "piramidal_rosa")

    _, rosa = _concluir(sessao_service, relogio, usuario, 25)
    _, granular = _concluir(sessao_service, relogio, usuario, 10)

    assert antes.tipo == Piramidal()
    assert rosa.tipo.codigo == "piramidal_rosa"
    assert rosa.tipo.forma == "piramidal"
    assert rosa.cor == "#FF6FB5"
    # Outra faixa de duração continua com o tipo original.
    assert granular.tipo == Granular()
    # Os neurônios antigos não mudam; a rede guarda cada um com o seu tipo.
    tipos = [n.tipo.codigo for n in redes.carregar(usuario).neuronios]
    assert tipos[-3:] == ["piramidal", "piramidal_rosa", "granular"]


def test_voltar_ao_original_vale_para_as_proximas_sessoes(
    sessao_service, loja, relogio
):
    usuario = uuid4()
    for _ in range(3):
        _concluir(sessao_service, relogio, usuario, 120)
    loja.comprar(usuario, "piramidal_rosa")
    loja.usar(usuario, "piramidal")

    _, neuronio = _concluir(sessao_service, relogio, usuario, 30)

    assert neuronio.tipo == Piramidal()


def test_o_creditador_ignora_sessoes_podadas():
    loja = Mock(spec=LojaService)
    creditador = CreditadorATP(loja)

    creditador.processar(SessaoPodada(uuid4(), uuid4(), 25, INICIO))
    assert not loja.creditar_sessao.called

    usuario = uuid4()
    creditador.processar(SessaoConcluida(uuid4(), usuario, 25, INICIO))
    loja.creditar_sessao.assert_called_once_with(usuario, 25)
