from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.estatisticas import EstatisticasService
from app.application.rede import RedeNeuralService
from app.application.sessoes import SessaoService
from app.domain.conquistas import FUSO_DOS_DIAS
from app.domain.entidades.materia import Materia
from app.domain.entidades.sessao_foco import Concluida, SessaoFoco
from app.domain.eventos import PublicadorEventos, SessaoPodada
from app.domain.excecoes import PeriodoInvalido
from app.domain.observadores import AtualizadorRede
from tests.repositorios import (
    RepositorioMateriaMemoria,
    RepositorioRedeNeuralMemoria,
    RepositorioSessaoMemoria,
)


class Relogio:
    def __init__(self, instante: datetime):
        self.instante = instante

    def __call__(self) -> datetime:
        return self.instante

    def avancar(self, **delta) -> None:
        self.instante += timedelta(**delta)


# 20/10/2026 às 15h00 em Brasília (18h00 UTC).
INICIO = datetime(2026, 10, 20, 18, 0, tzinfo=UTC)


@pytest.fixture
def relogio() -> Relogio:
    return Relogio(INICIO)


def test_consulta_separa_sessoes_e_materias_por_estudante(relogio):
    sessoes = RepositorioSessaoMemoria()
    materias = RepositorioMateriaMemoria()
    ana = uuid4()
    bruno = uuid4()

    calculo_ana = Materia(ana, "Cálculo", "#8B7BFF")
    fisica_bruno = Materia(bruno, "Física", "#3EE6E0")
    materias.salvar(calculo_ana)
    materias.salvar(fisica_bruno)

    sessoes.salvar(
        SessaoFoco(
            ana,
            30,
            inicio=datetime(2026, 10, 20, 14, 0, tzinfo=FUSO_DOS_DIAS),
            encerrada_em=datetime(2026, 10, 20, 14, 30, tzinfo=FUSO_DOS_DIAS),
            estado=Concluida(),
            materia_id=calculo_ana.id,
        )
    )
    sessoes.salvar(
        SessaoFoco(
            bruno,
            60,
            inicio=datetime(2026, 10, 20, 10, 0, tzinfo=FUSO_DOS_DIAS),
            encerrada_em=datetime(2026, 10, 20, 11, 0, tzinfo=FUSO_DOS_DIAS),
            estado=Concluida(),
            materia_id=fisica_bruno.id,
        )
    )

    servico = EstatisticasService(sessoes, materias, relogio=relogio)
    resumo_ana = servico.consultar(ana, periodo="dia")

    assert resumo_ana.tempo_total_minutos == 30
    assert resumo_ana.sessoes_concluidas == 1
    assert resumo_ana.melhor_horario == 14
    assert [m.nome for m in resumo_ana.por_materia] == ["Cálculo"]


def test_poda_sessao_abandonada_antes_de_calcular_e_publica_evento(relogio):
    sessoes = RepositorioSessaoMemoria()
    materias = RepositorioMateriaMemoria()
    redes = RepositorioRedeNeuralMemoria()
    publicador = PublicadorEventos()
    publicador.inscrever(SessaoPodada, AtualizadorRede(RedeNeuralService(redes)))

    sessao_service = SessaoService(
        sessoes, publicador, relogio=relogio, materias=materias
    )
    estatisticas = EstatisticasService(
        sessoes,
        materias,
        sessao_service=sessao_service,
        relogio=relogio,
    )

    estudante = uuid4()
    sessao = sessao_service.iniciar(estudante, 25, "estrito")
    # Passou de 25 + 5 min sem concluir: sessão abandonada.
    relogio.avancar(minutes=31)

    resumo = estatisticas.consultar(estudante, periodo="dia")

    assert resumo.sessoes_concluidas == 0
    assert resumo.sessoes_podadas == 1
    assert resumo.total_sessoes == 1
    assert resumo.taxa_sucesso == 0.0
    assert sessoes.buscar_por_id(sessao.id).codigo_estado == "podada"
    neuronios = redes.carregar(estudante).neuronios
    assert len(neuronios) == 1
    assert neuronios[0].vivo is False


def test_poda_sessao_abandonada_mesmo_sem_sessao_service(relogio):
    sessoes = RepositorioSessaoMemoria()
    materias = RepositorioMateriaMemoria()
    estudante = uuid4()

    abandonada = SessaoFoco(estudante, 10, inicio=relogio())
    sessoes.salvar(abandonada)
    relogio.avancar(minutes=16)

    servico = EstatisticasService(sessoes, materias, relogio=relogio)
    resumo = servico.consultar(estudante, periodo="dia")

    assert resumo.sessoes_podadas == 1
    assert sessoes.buscar_por_id(abandonada.id).codigo_estado == "podada"


def test_sessao_em_andamento_dentro_do_prazo_continua_ativa(relogio):
    sessoes = RepositorioSessaoMemoria()
    materias = RepositorioMateriaMemoria()
    estudante = uuid4()

    ativa = SessaoFoco(estudante, 25, inicio=relogio())
    sessoes.salvar(ativa)
    relogio.avancar(minutes=10)

    servico = EstatisticasService(sessoes, materias, relogio=relogio)
    resumo = servico.consultar(estudante, periodo="dia")

    assert resumo.total_sessoes == 0
    assert resumo.taxa_sucesso == 0.0
    assert sessoes.buscar_por_id(ativa.id).codigo_estado == "em_andamento"


def test_recusa_periodo_desconhecido(relogio):
    servico = EstatisticasService(
        RepositorioSessaoMemoria(), RepositorioMateriaMemoria(), relogio=relogio
    )

    with pytest.raises(PeriodoInvalido):
        servico.consultar(uuid4(), periodo="anual")

