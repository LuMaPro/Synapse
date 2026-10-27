from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.conquistas import (
    CATALOGO_CONQUISTAS,
    DiasSeguidos,
    HorasFocadas,
    PrimeiroNeuronio,
    RegraConquista,
    ResumoFoco,
    Sequencia,
    SessaoLongaSemPoda,
    SinapsesFormadas,
    calcular_sequencia,
)
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.entidades.neuronio import Neuronio
from app.domain.excecoes import HorarioInvalido
from app.domain.rede_neural import RedeNeural

HOJE = date(2026, 10, 27)


def _dias(*atras: int) -> list[date]:
    """Dias contados para trás a partir de HOJE (0 é hoje, 1 é ontem...)."""
    return [HOJE - timedelta(days=n) for n in atras]


# ------------------------------------------------------------------ sequência


class TestCalcularSequencia:
    def test_sem_sessoes_nao_ha_sequencia(self):
        assert calcular_sequencia([], HOJE) == Sequencia(atual=0, recorde=0)

    def test_sessao_hoje_comeca_a_sequencia(self):
        assert calcular_sequencia(_dias(0), HOJE) == Sequencia(atual=1, recorde=1)

    def test_conta_os_dias_seguidos_ate_hoje(self):
        assert calcular_sequencia(_dias(0, 1, 2, 3), HOJE) == Sequencia(4, 4)

    def test_sem_sessao_hoje_a_sequencia_de_ontem_ainda_vale(self):
        # O dia ainda não acabou: dá tempo de concluir uma sessão hoje.
        assert calcular_sequencia(_dias(1, 2, 3), HOJE) == Sequencia(3, 3)

    def test_um_dia_inteiro_sem_sessao_zera_a_atual_e_mantem_o_recorde(self):
        assert calcular_sequencia(_dias(2, 3, 4), HOJE) == Sequencia(0, 3)

    def test_o_recorde_pode_ser_de_uma_sequencia_antiga(self):
        dias = _dias(0, 1) + _dias(10, 11, 12, 13, 14)
        assert calcular_sequencia(dias, HOJE) == Sequencia(atual=2, recorde=5)

    def test_varias_sessoes_no_mesmo_dia_contam_uma_vez_e_a_ordem_nao_importa(self):
        dias = _dias(1, 0, 0, 2, 1, 0)
        assert calcular_sequencia(dias, HOJE) == Sequencia(3, 3)


# ------------------------------------------------------------------ resumo


def _neuronio(usuario_id, duracao, criado_em, *, vivo=True):
    return Neuronio(usuario_id, uuid4(), duracao, vivo=vivo, criado_em=criado_em)


class TestResumoDaRede:
    def test_rede_vazia(self):
        resumo = ResumoFoco.da_rede(RedeNeural(uuid4()), datetime.now(UTC))

        assert resumo == ResumoFoco()

    def test_conta_so_os_neuronios_vivos_e_as_sinapses(self):
        usuario = uuid4()
        rede = RedeNeural(usuario)
        inicio = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
        for i, duracao in enumerate([25, 120, 60]):
            rede.adicionar(_neuronio(usuario, duracao, inicio + timedelta(days=i)))
        # Sessão podada: neurônio morto, que não conta para nada.
        rede.adicionar(_neuronio(usuario, 90, inicio + timedelta(days=3), vivo=False))

        resumo = ResumoFoco.da_rede(rede, inicio + timedelta(days=3))

        assert resumo.neuronios_vivos == 3
        assert resumo.minutos_focados == 25 + 120 + 60
        assert resumo.maior_sessao_minutos == 120
        assert resumo.sinapses == len(rede.sinapses) == 3
        assert resumo.sequencia == Sequencia(atual=3, recorde=3)

    def test_os_dias_sao_contados_no_horario_de_brasilia(self):
        usuario = uuid4()
        # 20/10 às 10h e às 22h30 em Brasília; em UTC, a segunda já seria dia 21.
        rede = RedeNeural(
            usuario,
            [
                _neuronio(usuario, 25, datetime(2026, 10, 20, 13, 0, tzinfo=UTC)),
                _neuronio(usuario, 25, datetime(2026, 10, 21, 1, 30, tzinfo=UTC)),
            ],
        )
        # 21/10 às 23h em Brasília (22/10 em UTC): a sessão de ontem ainda vale.
        instante = datetime(2026, 10, 22, 2, 0, tzinfo=UTC)

        assert ResumoFoco.da_rede(rede, instante).sequencia == Sequencia(1, 1)


# ------------------------------------------------------------------ regras


@pytest.mark.parametrize(
    ("regra", "abaixo", "na_meta"),
    [
        (PrimeiroNeuronio(), ResumoFoco(), ResumoFoco(neuronios_vivos=1)),
        (
            HorasFocadas(10),
            ResumoFoco(minutos_focados=599),
            ResumoFoco(minutos_focados=600),
        ),
        (
            DiasSeguidos(7),
            ResumoFoco(sequencia=Sequencia(atual=6, recorde=6)),
            ResumoFoco(sequencia=Sequencia(atual=7, recorde=7)),
        ),
        (SinapsesFormadas(100), ResumoFoco(sinapses=99), ResumoFoco(sinapses=100)),
        (
            SessaoLongaSemPoda(120),
            ResumoFoco(maior_sessao_minutos=115),
            ResumoFoco(maior_sessao_minutos=120),
        ),
    ],
    ids=lambda valor: valor.codigo if isinstance(valor, RegraConquista) else None,
)
def test_cada_regra_so_e_cumprida_ao_chegar_na_meta(regra, abaixo, na_meta):
    assert not regra.cumprida(abaixo)
    assert regra.progresso(abaixo) < regra.meta
    assert regra.cumprida(na_meta)
    assert regra.progresso(na_meta) == regra.meta


def test_o_progresso_para_na_meta():
    regra = HorasFocadas(10)

    assert regra.progresso(ResumoFoco(minutos_focados=250)) == 250
    assert regra.progresso(ResumoFoco(minutos_focados=5000)) == 600


def test_dias_seguidos_vale_mesmo_depois_de_quebrar_a_sequencia():
    resumo = ResumoFoco(sequencia=Sequencia(atual=0, recorde=8))

    assert DiasSeguidos(7).cumprida(resumo)


def test_regras_com_meta_configuravel_tem_codigo_nome_e_dica_proprios():
    assert HorasFocadas(50).codigo == "horas_focadas_50"
    assert HorasFocadas(50).nome == "50 horas focadas"
    assert HorasFocadas(50).meta == 3000
    assert DiasSeguidos(30).descricao == (
        "Conclua pelo menos uma sessão por dia, 30 dias seguidos."
    )
    assert SessaoLongaSemPoda(120).nome == "2 h sem poda"
    assert SessaoLongaSemPoda(90).nome == "90 min sem poda"


def test_meta_precisa_ser_positiva():
    with pytest.raises(ValueError):
        HorasFocadas(0)


def test_uma_conquista_nova_e_so_uma_subclasse():
    class CemNeuronios(RegraConquista):
        def __init__(self):
            super().__init__(
                "cem_neuronios", "Cem neurônios", "Forme 100.", meta=100, unidade="x"
            )

        def medir(self, resumo):
            return resumo.neuronios_vivos

    assert CemNeuronios().cumprida(ResumoFoco(neuronios_vivos=100))
    assert repr(CemNeuronios()) == "CemNeuronios(codigo='cem_neuronios')"


def test_regra_sem_medir_nao_pode_ser_criada():
    class Incompleta(RegraConquista):
        pass

    with pytest.raises(TypeError):
        Incompleta("x", "X", "X", meta=1, unidade="x")


def test_catalogo_tem_as_conquistas_da_issue_com_codigos_unicos():
    codigos = [r.codigo for r in CATALOGO_CONQUISTAS]

    assert codigos == [
        "primeiro_neuronio",
        "horas_focadas_10",
        "dias_seguidos_7",
        "sinapses_100",
        "sessao_sem_poda_120",
    ]
    assert all(r.nome and r.descricao and r.unidade for r in CATALOGO_CONQUISTAS)


# ------------------------------------------------------------------ entidade


class TestConquistaDesbloqueada:
    def test_guarda_o_codigo_e_quando_foi_desbloqueada(self):
        usuario = uuid4()
        quando = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)

        conquista = ConquistaDesbloqueada(usuario, "primeiro_neuronio", quando)

        assert conquista.usuario_id == usuario
        assert conquista.codigo == "primeiro_neuronio"
        assert conquista.desbloqueada_em == quando
        assert repr(conquista) == "ConquistaDesbloqueada(codigo='primeiro_neuronio')"

    def test_exige_o_codigo_e_horario_com_fuso(self):
        with pytest.raises(ValueError):
            ConquistaDesbloqueada(uuid4(), "", datetime.now(UTC))
        with pytest.raises(HorarioInvalido):
            ConquistaDesbloqueada(uuid4(), "primeiro_neuronio", datetime(2026, 10, 27))
