"""Filtro de período usado pelos endpoints que listam por data (#25 e #29)."""

import re
from datetime import UTC, date, datetime, time

from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import is_aware, make_aware
from rest_framework import serializers

SO_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")

DESCRICAO_PERIODO = (
    "Data (`2026-10-20`, o dia inteiro em UTC) ou data e hora ISO 8601 com fuso "
    "(`2026-10-20T00:00:00-03:00`). O `+` de um fuso precisa ir codificado (`%2B`)."
)


class DataOuInstanteField(serializers.Field):
    """Aceita uma data (`2026-10-20`) ou data e hora ISO 8601 com fuso
    (`2026-10-20T08:00:00-03:00`). Sem fuso, vale o UTC."""

    default_error_messages = {
        "invalido": "Use uma data (AAAA-MM-DD) ou data e hora ISO 8601."
    }

    def to_internal_value(self, valor) -> date | datetime:
        texto = str(valor)
        try:
            # Só a data vem antes: o parse_datetime também aceitaria "2026-10-20",
            # como meia-noite, e o `ate` deixaria o próprio dia de fora.
            if SO_DATA.fullmatch(texto):
                return parse_date(texto)
            instante = parse_datetime(texto)
        except ValueError:  # bem formatada, mas impossível (ex.: 2026-02-30)
            instante = None
        if instante is None:
            self.fail("invalido")
        return instante if is_aware(instante) else make_aware(instante, UTC)

    def to_representation(self, valor) -> str:
        return valor.isoformat()


class FiltroPeriodoSerializer(serializers.Serializer):
    """`de` e `ate`, os dois inclusive. Uma data vale o dia inteiro (em UTC): do
    começo, em `de`, ao fim, em `ate`."""

    de = DataOuInstanteField(required=False)
    ate = DataOuInstanteField(required=False)

    def validate(self, dados: dict) -> dict:
        de, ate = dados.get("de"), dados.get("ate")
        if isinstance(de, date) and not isinstance(de, datetime):
            dados["de"] = datetime.combine(de, time.min, tzinfo=UTC)
        if isinstance(ate, date) and not isinstance(ate, datetime):
            dados["ate"] = datetime.combine(ate, time.max, tzinfo=UTC)
        if "de" in dados and "ate" in dados and dados["de"] > dados["ate"]:
            raise serializers.ValidationError(
                {"ate": "O fim do período não pode ser antes do início."}
            )
        return dados
