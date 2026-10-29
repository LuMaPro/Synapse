"""Cálculo puro das estatísticas de foco do estudante (#30)."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum
from uuid import UUID

from app.domain.conquistas import FUSO_DOS_DIAS
from app.domain.entidades.materia import Materia
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.excecoes import PeriodoInvalido
from app.domain.loja import Efeito, cor_por_hex
from app.domain.tempo import exigir_fuso


class PeriodoEstatisticas(StrEnum):
    """Janela de tempo do painel de estatísticas."""

    DIA = "dia"
    SEMANA = "semana"
    MES = "mes"


DIAS_POR_PERIODO: dict[PeriodoEstatisticas, int] = {
    PeriodoEstatisticas.DIA: 1,
    PeriodoEstatisticas.SEMANA: 7,
    PeriodoEstatisticas.MES: 30,
}


def periodo_por_codigo(codigo: str | PeriodoEstatisticas) -> PeriodoEstatisticas:
    """Converte o código recebido para `PeriodoEstatisticas` ou lança erro."""
    if isinstance(codigo, PeriodoEstatisticas):
        return codigo
    try:
        return PeriodoEstatisticas(codigo)
    except ValueError:
        raise PeriodoInvalido(
            f"Período inválido: {codigo!r}. Use 'dia', 'semana' ou 'mes'."
        ) from None


def intervalo_do_periodo(
    periodo: PeriodoEstatisticas | str,
    instante: datetime,
    fuso: tzinfo = FUSO_DOS_DIAS,
) -> tuple[datetime, datetime, date, date]:
    """Início e fim do período no fuso informado (meia-noite do 1º dia até 23:59:59 de
    hoje), junto com as datas inicial e final."""
    periodo_enum = periodo_por_codigo(periodo)
    referencia = exigir_fuso(instante, "instante").astimezone(fuso)
    hoje = referencia.date()
    data_inicio = hoje - timedelta(days=DIAS_POR_PERIODO[periodo_enum] - 1)
    inicio = datetime.combine(data_inicio, time.min, tzinfo=fuso)
    fim = datetime.combine(hoje, time.max, tzinfo=fuso)
    return inicio, fim, data_inicio, hoje


@dataclass(frozen=True)
class TempoMateriaDia:
    """Minutos focados numa matéria dentro de um dia específico."""

    materia_id: UUID | None
    minutos: int


@dataclass(frozen=True)
class TempoDia:
    """Minutos focados em sessões concluídas num dia do período."""

    data: date
    minutos: int
    por_materia: tuple[TempoMateriaDia, ...] = ()


@dataclass(frozen=True)
class TempoMateria:
    """Minutos focados numa matéria ao longo do período, com os dados visuais dela."""

    materia_id: UUID | None
    nome: str | None
    cor: str | None
    efeito: Efeito | None
    minutos: int
    percentual: float


@dataclass(frozen=True)
class EstatisticasFoco:
    """Resumo calculado das sessões de foco do estudante no período escolhido."""

    periodo: PeriodoEstatisticas
    inicio: date
    fim: date
    tempo_total_minutos: int
    sessoes_concluidas: int
    sessoes_podadas: int
    total_sessoes: int
    taxa_sucesso: float
    melhor_horario: int | None
    por_dia: tuple[TempoDia, ...]
    por_materia: tuple[TempoMateria, ...]


def calcular_estatisticas(
    sessoes: Iterable[SessaoFoco],
    *,
    periodo: PeriodoEstatisticas | str,
    instante: datetime,
    materias: Iterable[Materia] = (),
    fuso: tzinfo = FUSO_DOS_DIAS,
) -> EstatisticasFoco:
    """Calcula as estatísticas do período a partir das sessões e matérias do estudante.

    Apenas sessões iniciadas dentro do período entram no cálculo. O tempo focado, o
    agrupamento por dia e por matéria e o melhor horário consideram somente sessões
    concluídas; a taxa de sucesso considera as sessões encerradas (`concluídas /
    (concluídas + podadas)`), ignorando uma eventual sessão ainda em andamento.
    """
    periodo_enum = periodo_por_codigo(periodo)
    inicio_periodo, fim_periodo, data_inicio, data_fim = intervalo_do_periodo(
        periodo_enum, instante, fuso
    )

    no_periodo = [
        sessao for sessao in sessoes if inicio_periodo <= sessao.inicio <= fim_periodo
    ]
    concluidas = [s for s in no_periodo if s.codigo_estado == "concluida"]
    podadas = [s for s in no_periodo if s.codigo_estado == "podada"]

    sessoes_concluidas = len(concluidas)
    sessoes_podadas = len(podadas)
    total_sessoes = sessoes_concluidas + sessoes_podadas
    taxa_sucesso = (
        round(sessoes_concluidas / total_sessoes, 4) if total_sessoes > 0 else 0.0
    )

    tempo_total_minutos = sum(s.duracao.minutos for s in concluidas)

    por_dia = _calcular_por_dia(
        concluidas,
        data_inicio=data_inicio,
        quantidade_dias=DIAS_POR_PERIODO[periodo_enum],
        fuso=fuso,
    )
    por_materia = _calcular_por_materia(
        concluidas,
        materias=materias,
        tempo_total_minutos=tempo_total_minutos,
    )
    melhor_horario = _calcular_melhor_horario(concluidas, fuso=fuso)

    return EstatisticasFoco(
        periodo=periodo_enum,
        inicio=data_inicio,
        fim=data_fim,
        tempo_total_minutos=tempo_total_minutos,
        sessoes_concluidas=sessoes_concluidas,
        sessoes_podadas=sessoes_podadas,
        total_sessoes=total_sessoes,
        taxa_sucesso=taxa_sucesso,
        melhor_horario=melhor_horario,
        por_dia=por_dia,
        por_materia=por_materia,
    )


def _calcular_por_dia(
    concluidas: list[SessaoFoco],
    *,
    data_inicio: date,
    quantidade_dias: int,
    fuso: tzinfo,
) -> tuple[TempoDia, ...]:
    minutos_dia: dict[date, int] = defaultdict(int)
    minutos_dia_materia: dict[date, dict[UUID | None, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for sessao in concluidas:
        dia = sessao.inicio.astimezone(fuso).date()
        minutos = sessao.duracao.minutos
        minutos_dia[dia] += minutos
        minutos_dia_materia[dia][sessao.materia_id] += minutos

    dias: list[TempoDia] = []
    for deslocamento in range(quantidade_dias):
        dia = data_inicio + timedelta(days=deslocamento)
        por_materia_dia = tuple(
            TempoMateriaDia(materia_id=materia_id, minutos=minutos)
            for materia_id, minutos in sorted(
                minutos_dia_materia[dia].items(),
                key=lambda item: (
                    -item[1],
                    item[0] is None,
                    str(item[0] or ""),
                ),
            )
        )
        dias.append(
            TempoDia(
                data=dia,
                minutos=minutos_dia[dia],
                por_materia=por_materia_dia,
            )
        )
    return tuple(dias)


def _calcular_por_materia(
    concluidas: list[SessaoFoco],
    *,
    materias: Iterable[Materia],
    tempo_total_minutos: int,
) -> tuple[TempoMateria, ...]:
    if tempo_total_minutos == 0:
        return ()

    materias_por_id = {m.id: m for m in materias}
    minutos_por_materia: dict[UUID | None, int] = defaultdict(int)
    for sessao in concluidas:
        minutos_por_materia[sessao.materia_id] += sessao.duracao.minutos

    itens: list[TempoMateria] = []
    for materia_id, minutos in minutos_por_materia.items():
        materia = materias_por_id.get(materia_id) if materia_id is not None else None
        nome = materia.nome if materia is not None else None
        cor = materia.cor if materia is not None else None
        cor_loja = cor_por_hex(cor) if cor is not None else None
        efeito = cor_loja.efeito if cor_loja is not None else None
        itens.append(
            TempoMateria(
                materia_id=materia_id,
                nome=nome,
                cor=cor,
                efeito=efeito,
                minutos=minutos,
                percentual=round(minutos / tempo_total_minutos, 4),
            )
        )

    itens.sort(
        key=lambda item: (
            -item.minutos,
            item.materia_id is None,
            (item.nome or "").lower(),
            str(item.materia_id or ""),
        )
    )
    return tuple(itens)


def _calcular_melhor_horario(
    concluidas: list[SessaoFoco],
    *,
    fuso: tzinfo,
) -> int | None:
    if not concluidas:
        return None

    minutos_por_hora: dict[int, int] = defaultdict(int)
    sessoes_por_hora: dict[int, int] = defaultdict(int)
    for sessao in concluidas:
        hora = sessao.inicio.astimezone(fuso).hour
        minutos_por_hora[hora] += sessao.duracao.minutos
        sessoes_por_hora[hora] += 1

    return max(
        minutos_por_hora,
        key=lambda hora: (minutos_por_hora[hora], sessoes_por_hora[hora], -hora),
    )
