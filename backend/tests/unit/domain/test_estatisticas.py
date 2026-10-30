from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.conquistas import FUSO_DOS_DIAS
from app.domain.entidades.materia import Materia
from app.domain.entidades.sessao_foco import Concluida, EmAndamento, Podada, SessaoFoco
from app.domain.estatisticas import (
    PeriodoEstatisticas,
    TempoDia,
    TempoMateria,
    TempoMateriaDia,
    calcular_estatisticas,
    intervalo_do_periodo,
    periodo_por_codigo,
)
from app.domain.excecoes import HorarioInvalido, PeriodoInvalido
from app.domain.loja import Efeito

USUARIO_ID = uuid4()

# Terça-feira, 20/10/2026 às 15h00 em Brasília (18h00 UTC).
AGORA = datetime(2026, 10, 20, 18, 0, tzinfo=UTC)


def _brasilia(
    ano: int, mes: int, dia: int, hora: int = 10, minuto: int = 0
) -> datetime:
    return datetime(ano, mes, dia, hora, minuto, tzinfo=FUSO_DOS_DIAS)


def _sessao(
    inicio: datetime,
    duracao: int = 25,
    *,
    estado: str = "concluida",
    materia_id=None,
) -> SessaoFoco:
    estados = {
        "concluida": Concluida,
        "podada": Podada,
        "em_andamento": EmAndamento,
    }
    encerrada_em = (
        None if estado == "em_andamento" else inicio + timedelta(minutes=duracao)
    )
    return SessaoFoco(
        usuario_id=USUARIO_ID,
        duracao_minutos=duracao,
        inicio=inicio,
        encerrada_em=encerrada_em,
        estado=estados[estado](),
        materia_id=materia_id,
    )


# ------------------------------------------------------------------ períodos


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("dia", PeriodoEstatisticas.DIA),
        ("semana", PeriodoEstatisticas.SEMANA),
        ("mes", PeriodoEstatisticas.MES),
        (PeriodoEstatisticas.SEMANA, PeriodoEstatisticas.SEMANA),
    ],
)
def test_periodo_por_codigo_aceita_valores_validos(entrada, esperado):
    assert periodo_por_codigo(entrada) == esperado


@pytest.mark.parametrize("invalido", ["", "ano", "SEMANA", "7", "hoje"])
def test_periodo_por_codigo_recusa_valor_invalido(invalido):
    with pytest.raises(PeriodoInvalido):
        periodo_por_codigo(invalido)


def test_intervalo_do_periodo_exige_instante_com_fuso():
    with pytest.raises(HorarioInvalido):
        intervalo_do_periodo("dia", datetime(2026, 10, 20, 12, 0))


@pytest.mark.parametrize(
    ("periodo", "inicio_esperado", "dias_esperados"),
    [
        ("dia", date(2026, 10, 20), 1),
        ("semana", date(2026, 10, 14), 7),
        ("mes", date(2026, 9, 21), 30),
    ],
)
def test_intervalo_do_periodo_cobre_os_dias_certos(
    periodo, inicio_esperado, dias_esperados
):
    inicio, fim, data_inicio, data_fim = intervalo_do_periodo(periodo, AGORA)

    assert data_inicio == inicio_esperado
    assert data_fim == date(2026, 10, 20)
    assert (data_fim - data_inicio).days + 1 == dias_esperados
    assert inicio == datetime(
        inicio_esperado.year,
        inicio_esperado.month,
        inicio_esperado.day,
        0,
        0,
        tzinfo=FUSO_DOS_DIAS,
    )
    assert fim == datetime(2026, 10, 20, 23, 59, 59, 999999, tzinfo=FUSO_DOS_DIAS)


def test_intervalo_usa_o_dia_de_brasilia_e_nao_o_de_utc():
    # 22h30 de 20/10 em Brasília já é 01h30 de 21/10 em UTC.
    noite_em_brasilia = datetime(2026, 10, 21, 1, 30, tzinfo=UTC)

    _, _, data_inicio, data_fim = intervalo_do_periodo("dia", noite_em_brasilia)

    assert data_inicio == data_fim == date(2026, 10, 20)


# ------------------------------------------------------------------ estado vazio


@pytest.mark.parametrize(
    ("periodo", "qtd_dias"), [("dia", 1), ("semana", 7), ("mes", 30)]
)
def test_sem_sessoes_devolve_zeros_e_todos_os_dias_do_periodo(periodo, qtd_dias):
    resumo = calcular_estatisticas([], periodo=periodo, instante=AGORA)

    assert resumo.periodo == PeriodoEstatisticas(periodo)
    assert resumo.tempo_total_minutos == 0
    assert resumo.sessoes_concluidas == 0
    assert resumo.sessoes_podadas == 0
    assert resumo.total_sessoes == 0
    assert resumo.taxa_sucesso == 0.0
    assert resumo.melhor_horario is None
    assert resumo.por_materia == ()
    assert len(resumo.por_dia) == qtd_dias
    assert [d.data for d in resumo.por_dia] == [
        resumo.inicio + timedelta(days=i) for i in range(qtd_dias)
    ]
    assert all(d.minutos == 0 and d.por_materia == () for d in resumo.por_dia)


# ------------------------------------------------------------------ recorte do período


def test_filtra_sessoes_pelas_pontas_de_cada_periodo():
    sessoes = [
        # Fora até do mês (31 dias atrás: 20/09/2026 23:59 em Brasília)
        _sessao(_brasilia(2026, 9, 20, 23, 59), duracao=60),
        # No primeiro segundo do mês (21/09/2026 00:00 em Brasília)
        _sessao(_brasilia(2026, 9, 21, 0, 0), duracao=40),
        # Um minuto antes da semana começar (13/10/2026 23:59 em Brasília)
        _sessao(_brasilia(2026, 10, 13, 23, 59), duracao=35),
        # No primeiro minuto da semana (14/10/2026 00:00 em Brasília)
        _sessao(_brasilia(2026, 10, 14, 0, 0), duracao=30),
        # Hoje (20/10/2026)
        _sessao(_brasilia(2026, 10, 20, 14, 0), duracao=25),
    ]

    dia = calcular_estatisticas(sessoes, periodo="dia", instante=AGORA)
    semana = calcular_estatisticas(sessoes, periodo="semana", instante=AGORA)
    mes = calcular_estatisticas(sessoes, periodo="mes", instante=AGORA)

    assert dia.tempo_total_minutos == 25
    assert semana.tempo_total_minutos == 30 + 25
    assert mes.tempo_total_minutos == 40 + 35 + 30 + 25


# --------------------------------------------------------- tempo por dia e matéria


def test_tempo_focado_por_dia_e_por_materia_ignora_podadas_e_em_andamento():
    calculo = Materia(USUARIO_ID, "Cálculo", "#8B7BFF")
    aurora = Materia(USUARIO_ID, "Física", "#5BFFB0")  # cor da loja com efeito aurora
    nao_estudada = Materia(USUARIO_ID, "História", "#FFC857")

    sessoes = [
        _sessao(_brasilia(2026, 10, 19, 9, 0), duracao=30, materia_id=calculo.id),
        _sessao(_brasilia(2026, 10, 20, 19, 0), duracao=50, materia_id=calculo.id),
        _sessao(_brasilia(2026, 10, 20, 20, 0), duracao=20, materia_id=aurora.id),
        _sessao(_brasilia(2026, 10, 20, 21, 0), duracao=25, materia_id=None),
        # Sessão podada e sessão em andamento não somam minutos focados:
        _sessao(
            _brasilia(2026, 10, 20, 10, 0),
            duracao=60,
            estado="podada",
            materia_id=aurora.id,
        ),
        _sessao(
            _brasilia(2026, 10, 20, 14, 50),
            duracao=45,
            estado="em_andamento",
            materia_id=calculo.id,
        ),
    ]

    resumo = calcular_estatisticas(
        sessoes,
        periodo="semana",
        instante=AGORA,
        materias=[calculo, aurora, nao_estudada],
    )

    assert resumo.tempo_total_minutos == 125

    # Penúltimo e último dias da janela de 7 dias (19/10 e 20/10):
    assert resumo.por_dia[-2] == TempoDia(
        data=date(2026, 10, 19),
        minutos=30,
        por_materia=(TempoMateriaDia(materia_id=calculo.id, minutos=30),),
    )
    assert resumo.por_dia[-1] == TempoDia(
        data=date(2026, 10, 20),
        minutos=95,
        por_materia=(
            TempoMateriaDia(materia_id=calculo.id, minutos=50),
            TempoMateriaDia(materia_id=None, minutos=25),
            TempoMateriaDia(materia_id=aurora.id, minutos=20),
        ),
    )
    assert all(d.minutos == 0 for d in resumo.por_dia[:-2])

    # Ordenado do maior tempo para o menor; matéria com 0 min não entra:
    assert resumo.por_materia == (
        TempoMateria(
            materia_id=calculo.id,
            nome="Cálculo",
            cor="#8B7BFF",
            efeito=None,
            minutos=80,
            percentual=0.64,
        ),
        TempoMateria(
            materia_id=None,
            nome=None,
            cor=None,
            efeito=None,
            minutos=25,
            percentual=0.2,
        ),
        TempoMateria(
            materia_id=aurora.id,
            nome="Física",
            cor="#5BFFB0",
            efeito=Efeito.AURORA,
            minutos=20,
            percentual=0.16,
        ),
    )


def test_sessao_as_22h_em_brasilia_fica_no_mesmo_dia_e_nao_no_seguinte():
    # 22h15 de 19/10 em Brasília = 01h15 de 20/10 em UTC.
    sessao = _sessao(datetime(2026, 10, 20, 1, 15, tzinfo=UTC), duracao=35)

    resumo = calcular_estatisticas([sessao], periodo="semana", instante=AGORA)

    por_data = {d.data: d.minutos for d in resumo.por_dia}
    assert por_data[date(2026, 10, 19)] == 35
    assert por_data[date(2026, 10, 20)] == 0


def test_empate_em_por_materia_coloca_materias_nomeadas_antes_de_sem_materia():
    poo = Materia(USUARIO_ID, "POO", "#3EE6E0")
    algoritmos = Materia(USUARIO_ID, "Algoritmos", "#5BE49B")
    sessoes = [
        _sessao(_brasilia(2026, 10, 20, 9, 0), duracao=30, materia_id=None),
        _sessao(_brasilia(2026, 10, 20, 10, 0), duracao=30, materia_id=poo.id),
        _sessao(_brasilia(2026, 10, 20, 11, 0), duracao=30, materia_id=algoritmos.id),
    ]

    resumo = calcular_estatisticas(
        sessoes, periodo="dia", instante=AGORA, materias=[poo, algoritmos]
    )

    assert [m.nome for m in resumo.por_materia] == ["Algoritmos", "POO", None]


# ------------------------------------------------------------------ taxa de sucesso


@pytest.mark.parametrize(
    ("estados", "concluidas_esp", "podadas_esp", "total_esp", "taxa_esp"),
    [
        (["concluida", "concluida"], 2, 0, 2, 1.0),
        (["podada", "podada"], 0, 2, 2, 0.0),
        (["concluida", "concluida", "podada"], 2, 1, 3, 0.6667),
        (["concluida", "podada", "podada", "concluida"], 2, 2, 4, 0.5),
        # Sessão em andamento não entra no denominador até terminar:
        (["concluida", "em_andamento"], 1, 0, 1, 1.0),
        (["em_andamento"], 0, 0, 0, 0.0),
    ],
)
def test_taxa_de_sucesso_concluidas_sobre_total(
    estados, concluidas_esp, podadas_esp, total_esp, taxa_esp
):
    sessoes = [
        _sessao(_brasilia(2026, 10, 20, 8 + indice, 0), estado=estado)
        for indice, estado in enumerate(estados)
    ]

    resumo = calcular_estatisticas(sessoes, periodo="dia", instante=AGORA)

    assert resumo.sessoes_concluidas == concluidas_esp
    assert resumo.sessoes_podadas == podadas_esp
    assert resumo.total_sessoes == total_esp
    assert resumo.taxa_sucesso == taxa_esp


# ------------------------------------------------------------------ melhor horário


def test_melhor_horario_escolhe_a_hora_com_mais_minutos_focados():
    sessoes = [
        _sessao(_brasilia(2026, 10, 18, 9, 0), duracao=45),
        _sessao(_brasilia(2026, 10, 19, 19, 5), duracao=25),
        _sessao(_brasilia(2026, 10, 20, 19, 35), duracao=30),
        # Podada de 120 min às 9h não soma para a hora 9:
        _sessao(_brasilia(2026, 10, 20, 9, 0), duracao=120, estado="podada"),
    ]

    resumo = calcular_estatisticas(sessoes, periodo="semana", instante=AGORA)

    assert resumo.melhor_horario == 19


def test_melhor_horario_desempata_por_sessoes_e_depois_pela_hora_mais_cedo():
    # Duas sessões de 25 min às 14h (50 min, 2 sessões) vencem uma de 50 min às 9h:
    sessoes_mais_frequente = [
        _sessao(_brasilia(2026, 10, 19, 9, 0), duracao=50),
        _sessao(_brasilia(2026, 10, 19, 14, 0), duracao=25),
        _sessao(_brasilia(2026, 10, 20, 14, 0), duracao=25),
    ]
    assert (
        calcular_estatisticas(
            sessoes_mais_frequente, periodo="semana", instante=AGORA
        ).melhor_horario
        == 14
    )

    # Mesmo total de minutos e mesma quantidade de sessões: vence a hora mais cedo:
    sessoes_empate_total = [
        _sessao(_brasilia(2026, 10, 20, 16, 0), duracao=30),
        _sessao(_brasilia(2026, 10, 20, 8, 0), duracao=30),
    ]
    assert (
        calcular_estatisticas(
            sessoes_empate_total, periodo="dia", instante=AGORA
        ).melhor_horario
        == 8
    )


def test_melhor_horario_usa_o_fuso_de_brasilia():
    # 01h00 UTC de 20/10 = 22h00 de 19/10 em Brasília.
    sessao = _sessao(datetime(2026, 10, 20, 1, 0, tzinfo=UTC), duracao=40)

    resumo = calcular_estatisticas([sessao], periodo="semana", instante=AGORA)

    assert resumo.melhor_horario == 22


def test_melhor_horario_e_nulo_quando_so_ha_sessoes_podadas():
    sessoes = [_sessao(_brasilia(2026, 10, 20, 19, 0), duracao=50, estado="podada")]

    resumo = calcular_estatisticas(sessoes, periodo="dia", instante=AGORA)

    assert resumo.melhor_horario is None
