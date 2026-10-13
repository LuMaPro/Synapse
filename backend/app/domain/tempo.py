"""Horários do domínio. Todo horário é um datetime com fuso horário (UTC)."""

from datetime import UTC, datetime

from app.domain.excecoes import HorarioInvalido


def agora() -> datetime:
    return datetime.now(UTC)


def exigir_fuso(valor: datetime, campo: str) -> datetime:
    """Recusa datetimes sem fuso: comparar horários "ingênuos" gera erros sutis."""
    if not isinstance(valor, datetime) or valor.utcoffset() is None:
        raise HorarioInvalido(f"{campo} precisa ser um datetime com fuso horário.")
    return valor
