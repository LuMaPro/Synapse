from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.entidades.materia import Materia
from app.domain.entidades.neuronio import (
    FabricaNeuronio,
    Granular,
    Piramidal,
    Purkinje,
    TipoNeuronio,
)
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.excecoes import (
    DuracaoInvalida,
    HorarioInvalido,
    MateriaNaoEncontrada,
    PoliticaInvalida,
    SessaoAtivaExistente,
    SessaoNaoEncontrada,
    TransicaoInvalida,
)
from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.observadores import AtualizadorRede
from tests.repositorios import (
    RepositorioMateriaMemoria,
    RepositorioRedeNeuralMemoria,
    RepositorioSessaoMemoria,
)

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
def redes():
    return RepositorioRedeNeuralMemoria()


def _publicador_com_rede(rede: RedeNeuralService) -> PublicadorEventos:
    """Monta o publicador como a API: o AtualizadorRede inscrito nos dois eventos."""
    publicador = PublicadorEventos()
    atualizador = AtualizadorRede(rede)
    publicador.inscrever(SessaoConcluida, atualizador)
    publicador.inscrever(SessaoPodada, atualizador)
    return publicador


@pytest.fixture
def publicador(redes):
    # Publicador de verdade (os neurônios chegam à rede); o Mock só registra as
    # chamadas, para os testes conferirem os eventos publicados.
    return Mock(
        spec=PublicadorEventos, wraps=_publicador_com_rede(RedeNeuralService(redes))
    )


@pytest.fixture
def materias():
    return RepositorioMateriaMemoria()


@pytest.fixture
def servico(sessoes, publicador, relogio, materias):
    return SessaoService(sessoes, publicador, relogio=relogio, materias=materias)


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
    servico, publicador, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=-2)

    concluida, _ = servico.concluir(usuario_id, sessao.id)

    assert concluida.codigo_estado == "concluida"
    assert concluida.encerrada_em == sessao.fim_previsto
    publicador.publicar.assert_called_once()


def test_concluir_3_segundos_antes_ainda_e_cedo(servico, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=-3)

    with pytest.raises(TransicaoInvalida):
        servico.concluir(usuario_id, sessao.id)


def test_concluir_forcar_conclusao_permite_encerrar_na_hora(
    servico, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=1)

    concluida, _ = servico.concluir(usuario_id, sessao.id, forcar_conclusao=True)
    assert concluida.codigo_estado == "concluida"
    assert concluida.encerrada_em == sessao.fim_previsto


def test_concluir_publica_evento_sessao_concluida(
    servico, publicador, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=1)

    concluida, _ = servico.concluir(usuario_id, sessao.id)

    assert concluida.codigo_estado == "concluida"
    publicador.publicar.assert_called_once()
    evento = publicador.publicar.call_args[0][0]
    assert isinstance(evento, SessaoConcluida)
    assert evento.sessao_id == sessao.id
    assert evento.usuario_id == usuario_id


def _neuronio_da_sessao(redes, usuario_id, sessao_id):
    rede = redes.carregar(usuario_id)
    return next(n for n in rede.neuronios if n.sessao_id == sessao_id), rede


def test_concluir_cria_o_neuronio(servico, redes, usuario_id, relogio):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25, seconds=1)

    concluida, neuronio = servico.concluir(usuario_id, sessao.id)

    assert concluida.codigo_estado == "concluida"
    assert neuronio.sessao_id == sessao.id
    assert neuronio.usuario_id == usuario_id
    assert neuronio.duracao.minutos == 25
    assert neuronio.vivo
    assert _neuronio_da_sessao(redes, usuario_id, sessao.id)[0] == neuronio


def test_neuronios_de_sessoes_concluidas_formam_sinapses(
    servico, redes, usuario_id, relogio
):
    neuronios = []
    for _ in range(3):
        sessao = servico.iniciar(usuario_id, 10, "estrito")
        relogio.avancar(minutes=10)
        neuronios.append(servico.concluir(usuario_id, sessao.id)[1])

    rede = redes.carregar(usuario_id)
    pares = {(s.origem_id, s.destino_id) for s in rede.sinapses}
    primeiro, segundo, terceiro = neuronios
    assert pares == {
        (primeiro.id, segundo.id),
        (primeiro.id, terceiro.id),
        (segundo.id, terceiro.id),
    }


def test_interrupcao_no_estrito_poda_no_momento_da_saida(
    servico, publicador, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=6)

    podada = servico.registrar_interrupcao(
        usuario_id, sessao.id, INICIO + timedelta(minutes=5), None
    )

    assert podada.codigo_estado == "podada"
    assert podada.encerrada_em == INICIO + timedelta(minutes=5)

    evento = publicador.publicar.call_args[0][0]
    assert isinstance(evento, SessaoPodada)


def test_interrupcoes_no_tolerante_somam_ate_o_saldo(
    servico, publicador, usuario_id, relogio
):
    # 10 min: saldo de 60 s.
    sessao = servico.iniciar(usuario_id, 10, "tolerante")
    relogio.avancar(minutes=5)
    saida = INICIO + timedelta(minutes=1)

    servico.registrar_interrupcao(
        usuario_id, sessao.id, saida, saida + timedelta(seconds=40)
    )
    assert sessao.codigo_estado == "em_andamento"
    publicador.publicar.assert_not_called()

    saida = INICIO + timedelta(minutes=3)
    servico.registrar_interrupcao(
        usuario_id, sessao.id, saida, saida + timedelta(seconds=30)
    )
    assert sessao.codigo_estado == "podada"
    assert sessao.encerrada_em == saida + timedelta(seconds=20)

    evento = publicador.publicar.call_args[0][0]
    assert isinstance(evento, SessaoPodada)


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


def test_desistir_conta_como_poda_e_publica_evento(
    servico, publicador, usuario_id, relogio
):
    sessao = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=3)

    podada = servico.desistir(usuario_id, sessao.id)

    assert podada.codigo_estado == "podada"
    assert podada.encerrada_em == INICIO + timedelta(minutes=3)

    evento = publicador.publicar.call_args[0][0]
    assert isinstance(evento, SessaoPodada)
    assert evento.sessao_id == sessao.id


def _podar_por_saida_no_estrito(servico, usuario_id, sessao, relogio):
    relogio.avancar(minutes=6)
    saida = sessao.inicio + timedelta(minutes=5)
    servico.registrar_interrupcao(usuario_id, sessao.id, saida, None)


def _podar_por_saldo_no_tolerante(servico, usuario_id, sessao, relogio):
    relogio.avancar(minutes=6)
    saida = sessao.inicio + timedelta(minutes=1)
    servico.registrar_interrupcao(
        usuario_id, sessao.id, saida, saida + timedelta(minutes=4)
    )


def _podar_por_desistencia(servico, usuario_id, sessao, relogio):
    relogio.avancar(minutes=3)
    servico.desistir(usuario_id, sessao.id)


def _podar_por_abandono_ao_acessar(servico, usuario_id, sessao, relogio):
    relogio.avancar(minutes=31)
    servico.buscar_ativa(usuario_id)


def _podar_por_abandono_na_varredura(servico, usuario_id, sessao, relogio):
    relogio.avancar(minutes=31)
    servico.podar_orfas()


@pytest.mark.parametrize(
    ("modo", "podar"),
    [
        ("estrito", _podar_por_saida_no_estrito),
        ("tolerante", _podar_por_saldo_no_tolerante),
        ("estrito", _podar_por_desistencia),
        ("estrito", _podar_por_abandono_ao_acessar),
        ("tolerante", _podar_por_abandono_na_varredura),
    ],
)
def test_criterios_de_poda_publicam_evento_sessao_podada(
    servico, sessoes, publicador, usuario_id, relogio, modo, podar
):
    sessao = servico.iniciar(usuario_id, 25, modo)

    podar(servico, usuario_id, sessao, relogio)

    assert sessoes.buscar_por_id(sessao.id).codigo_estado == "podada"

    evento = publicador.publicar.call_args[0][0]
    assert isinstance(evento, SessaoPodada)
    assert evento.sessao_id == sessao.id


@pytest.mark.parametrize(
    ("modo", "podar"),
    [
        ("estrito", _podar_por_saida_no_estrito),
        ("tolerante", _podar_por_saldo_no_tolerante),
        ("estrito", _podar_por_desistencia),
        ("estrito", _podar_por_abandono_ao_acessar),
        ("tolerante", _podar_por_abandono_na_varredura),
    ],
)
def test_criterio_poda_sinaptica_sessao_podada_gera_neuronio_morto_sem_sinapses(
    servico, sessoes, redes, usuario_id, relogio, modo, podar
):
    # Um neurônio vivo antes, para a poda ter a quem se ligar se a regra deixasse.
    anterior = servico.iniciar(usuario_id, 25, "estrito")
    relogio.avancar(minutes=25)
    servico.concluir(usuario_id, anterior.id)
    sessao = servico.iniciar(usuario_id, 25, modo)

    podar(servico, usuario_id, sessao, relogio)

    assert sessoes.buscar_por_id(sessao.id).codigo_estado == "podada"
    morto, rede = _neuronio_da_sessao(redes, usuario_id, sessao.id)
    assert not morto.vivo
    assert morto.duracao.minutos == 25
    assert rede.sinapses_de(morto.id) == []


def test_poda_logo_apos_conclusao_na_tolerancia_entra_na_rede(
    servico, redes, usuario_id, relogio
):
    # Concluída 1 s antes do fim, a sessão termina no fim previsto: o neurônio fica
    # datado 1 s no futuro. Uma sessão nova podada nesse segundo deixa um neurônio
    # morto com data anterior à dele, e a rede precisa aceitar.
    primeira = servico.iniciar(usuario_id, 10, "estrito")
    relogio.avancar(minutes=9, seconds=59)
    _, vivo = servico.concluir(usuario_id, primeira.id)
    segunda = servico.iniciar(usuario_id, 10, "estrito")

    servico.registrar_interrupcao(usuario_id, segunda.id, relogio.instante, None)

    morto, rede = _neuronio_da_sessao(redes, usuario_id, segunda.id)
    assert morto.criado_em < vivo.criado_em
    assert rede.neuronios == [morto, vivo]


def test_criterio_regra_trocada_sem_mexer_no_servico_de_sessao(
    sessoes, redes, usuario_id, relogio
):
    class SemLigacoes(RegraFormacaoSinapses):
        def conexoes(self, novo, rede):
            return []

    publicador = _publicador_com_rede(RedeNeuralService(redes, regra=SemLigacoes()))
    servico = SessaoService(sessoes, publicador, relogio=relogio)
    for _ in range(3):
        sessao = servico.iniciar(usuario_id, 10, "estrito")
        relogio.avancar(minutes=10)
        servico.concluir(usuario_id, sessao.id)

    rede = redes.carregar(usuario_id)
    assert len(rede) == 3
    assert rede.sinapses == []


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


def test_podar_orfas_varre_todos_os_usuarios(servico, relogio, publicador):
    abandonadas = [servico.iniciar(uuid4(), 10, "estrito") for _ in range(2)]
    relogio.avancar(minutes=14)
    recente = servico.iniciar(uuid4(), 25, "estrito")
    relogio.avancar(minutes=2)  # as de 10 min passaram de 15 min; a recente não

    assert servico.podar_orfas() == 2
    assert all(s.codigo_estado == "podada" for s in abandonadas)
    assert recente.codigo_estado == "em_andamento"
    assert publicador.publicar.call_count == 2


def test_iniciar_sessao_com_materia_valida_associa_materia(
    servico, materias, usuario_id
):
    materia = Materia(usuario_id, "Cálculo", "#8B7BFF")
    materias.salvar(materia)

    sessao = servico.iniciar(usuario_id, 25, "estrito", materia_id=materia.id)

    assert sessao.materia_id == materia.id


def test_iniciar_sessao_com_materia_inexistente_lanca_excecao(servico, usuario_id):
    with pytest.raises(MateriaNaoEncontrada):
        servico.iniciar(usuario_id, 25, "estrito", materia_id=uuid4())


def test_iniciar_sessao_com_materia_de_outro_usuario_lanca_excecao(
    servico, materias, usuario_id
):
    outro_usuario = uuid4()
    materia_outro = Materia(outro_usuario, "Física", "#3EE6E0")
    materias.salvar(materia_outro)

    with pytest.raises(MateriaNaoEncontrada):
        servico.iniciar(usuario_id, 25, "estrito", materia_id=materia_outro.id)


def test_concluir_sessao_com_materia_passa_materia_para_neuronio(
    servico, materias, usuario_id, relogio, redes
):
    materia = Materia(usuario_id, "Cálculo", "#8B7BFF")
    materias.salvar(materia)

    sessao = servico.iniciar(usuario_id, 25, "estrito", materia_id=materia.id)
    relogio.avancar(minutes=25)
    sessao_concluida, neuronio = servico.concluir(usuario_id, sessao.id)

    assert sessao_concluida.materia_id == materia.id
    assert neuronio.materia_id == materia.id
    rede = redes.carregar(usuario_id)
    assert rede.neuronios[0].materia_id == materia.id


def test_poda_sessao_com_materia_passa_materia_para_neuronio(
    servico, materias, usuario_id, relogio, redes
):
    materia = Materia(usuario_id, "Cálculo", "#8B7BFF")
    materias.salvar(materia)

    servico.iniciar(usuario_id, 25, "estrito", materia_id=materia.id)
    relogio.avancar(minutes=31)  # abandono gera poda
    servico.buscar_ativa(usuario_id)

    rede = redes.carregar(usuario_id)
    assert len(rede) == 1
    assert rede.neuronios[0].vivo is False
    assert rede.neuronios[0].materia_id == materia.id


@pytest.mark.parametrize(
    ("duracao", "esperado"),
    [(10, Granular()), (25, Piramidal()), (60, Purkinje())],
)
def test_concluir_cria_neuronio_com_tipo_da_fabrica(
    servico, usuario_id, relogio, duracao, esperado
):
    sessao = servico.iniciar(usuario_id, duracao, "estrito")
    relogio.avancar(minutes=duracao)

    _, neuronio = servico.concluir(usuario_id, sessao.id)

    assert neuronio.tipo == esperado


def test_criterio_tipo_novo_na_fabrica_sem_mexer_no_servico_de_sessao(
    sessoes, publicador, usuario_id, relogio
):
    class Fusiforme(TipoNeuronio):
        duracao_minima = 40
        duracao_maxima = 59

        @property
        def nome(self) -> str:
            return "Fusiforme"

        @property
        def cor(self) -> str:
            return "#6FA8FF"

        @property
        def numero_dendritos(self) -> int:
            return 6

        @property
        def raio(self) -> float:
            return 7.5

    fabrica = FabricaNeuronio((*FabricaNeuronio.TIPOS_PADRAO, Fusiforme()))
    servico = SessaoService(sessoes, publicador, relogio=relogio, fabrica=fabrica)
    sessao = servico.iniciar(usuario_id, 45, "estrito")
    relogio.avancar(minutes=45)

    _, neuronio = servico.concluir(usuario_id, sessao.id)

    assert neuronio.tipo == Fusiforme()
    assert neuronio.cor == "#6FA8FF"


# ------------------------------------------------------------------ histórico (#29)


def _sessao_terminada(servico, usuario_id, relogio, *, duracao=10, concluir=True):
    sessao = servico.iniciar(usuario_id, duracao, "estrito")
    if concluir:
        relogio.avancar(minutes=duracao)
        servico.concluir(usuario_id, sessao.id)
    else:
        relogio.avancar(minutes=1)
        servico.desistir(usuario_id, sessao.id)
    relogio.avancar(hours=1)
    return sessao


def test_historico_da_mais_recente_para_a_mais_antiga(servico, usuario_id, relogio):
    primeira = _sessao_terminada(servico, usuario_id, relogio)
    segunda = _sessao_terminada(servico, usuario_id, relogio, concluir=False)
    ativa = servico.iniciar(usuario_id, 25, "estrito")

    pagina = servico.historico(usuario_id)

    assert [s.id for s in pagina.sessoes] == [ativa.id, segunda.id, primeira.id]
    assert [s.codigo_estado for s in pagina.sessoes] == [
        "em_andamento",
        "podada",
        "concluida",
    ]
    assert (pagina.total, pagina.pagina, pagina.paginas) == (3, 1, 1)


def test_historico_filtra_por_estado_e_periodo(servico, usuario_id, relogio):
    antiga = _sessao_terminada(servico, usuario_id, relogio)
    podada = _sessao_terminada(servico, usuario_id, relogio, concluir=False)
    recente = _sessao_terminada(servico, usuario_id, relogio)

    concluidas = servico.historico(usuario_id, estado="concluida")
    assert [s.id for s in concluidas.sessoes] == [recente.id, antiga.id]

    periodo = servico.historico(usuario_id, de=podada.inicio, ate=podada.inicio)
    assert [s.id for s in periodo.sessoes] == [podada.id]


def test_historico_em_paginas(servico, usuario_id, relogio):
    sessoes = [_sessao_terminada(servico, usuario_id, relogio) for _ in range(5)]

    segunda = servico.historico(usuario_id, pagina=2, tamanho=2)

    assert [s.id for s in segunda.sessoes] == [sessoes[2].id, sessoes[1].id]
    assert (segunda.total, segunda.paginas) == (5, 3)
    assert servico.historico(usuario_id, pagina=4, tamanho=2).sessoes == []


def test_historico_so_traz_as_sessoes_do_estudante(servico, usuario_id, relogio):
    _sessao_terminada(servico, uuid4(), relogio)

    assert servico.historico(usuario_id).total == 0


def test_historico_poda_antes_a_sessao_abandonada(
    servico, sessoes, usuario_id, relogio
):
    abandonada = servico.iniciar(usuario_id, 10, "estrito")
    relogio.avancar(minutes=16)

    pagina = servico.historico(usuario_id)

    assert pagina.sessoes[0].id == abandonada.id
    assert pagina.sessoes[0].codigo_estado == "podada"
    assert sessoes.buscar_por_id(abandonada.id).codigo_estado == "podada"


def test_historico_vazio_tem_uma_pagina(servico, usuario_id):
    pagina = servico.historico(usuario_id)

    assert (pagina.sessoes, pagina.total, pagina.paginas) == ([], 0, 1)


@pytest.mark.parametrize(("pagina", "tamanho"), [(0, 20), (1, 0)])
def test_historico_recusa_pagina_ou_tamanho_menor_que_1(
    servico, usuario_id, pagina, tamanho
):
    with pytest.raises(ValueError):
        servico.historico(usuario_id, pagina=pagina, tamanho=tamanho)
