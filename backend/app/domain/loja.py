"""Loja de ATP: os tipos de neurônio que o estudante pode desbloquear (#34)."""

from dataclasses import dataclass

from app.domain.entidades.neuronio import (
    Granular,
    Piramidal,
    Purkinje,
    TipoNeuronio,
    VarianteCor,
)


@dataclass(frozen=True)
class ItemLoja:
    """Um tipo de neurônio à venda. Os originais custam 0 e já vêm desbloqueados."""

    tipo: TipoNeuronio
    preco: int

    def __post_init__(self):
        if self.preco < 0:
            raise ValueError("O preço não pode ser negativo.")

    @property
    def codigo(self) -> str:
        return self.tipo.codigo

    @property
    def forma(self) -> str:
        return self.tipo.forma

    @property
    def gratuito(self) -> bool:
        return self.preco == 0


# Os preços consideram 1 ATP por minuto de foco: a variação mais barata sai por
# quatro sessões de 25 min. As cores são da paleta das matérias (docs/design), sem
# o vermelho da poda nem o cinza do neurônio podado.
CATALOGO_LOJA: tuple[ItemLoja, ...] = (
    ItemLoja(Granular(), 0),
    ItemLoja(VarianteCor(Granular(), "granular_lima", "Granular Lima", "#C3E86B"), 100),
    ItemLoja(
        VarianteCor(Granular(), "granular_esmeralda", "Granular Esmeralda", "#5BE49B"),
        150,
    ),
    ItemLoja(Piramidal(), 0),
    ItemLoja(
        VarianteCor(Piramidal(), "piramidal_rosa", "Piramidal Rosa", "#FF6FB5"), 250
    ),
    ItemLoja(
        VarianteCor(Piramidal(), "piramidal_safira", "Piramidal Safira", "#6FA8FF"),
        300,
    ),
    ItemLoja(Purkinje(), 0),
    ItemLoja(
        VarianteCor(Purkinje(), "purkinje_coral", "Purkinje Coral", "#FF8A5C"), 400
    ),
    ItemLoja(
        VarianteCor(Purkinje(), "purkinje_lunar", "Purkinje Lunar", "#ECEDF7"), 500
    ),
)


def item_por_codigo(
    codigo: str, catalogo: tuple[ItemLoja, ...] = CATALOGO_LOJA
) -> ItemLoja | None:
    return next((item for item in catalogo if item.codigo == codigo), None)


def tipo_por_codigo(codigo: str) -> TipoNeuronio | None:
    """O tipo guardado num neurônio, ou `None` se ele saiu do catálogo."""
    item = item_por_codigo(codigo)
    return item.tipo if item else None
