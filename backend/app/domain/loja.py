"""Cores das matérias e a loja de ATP (#34).

A cor de um neurônio vem da matéria da sessão; sem matéria, é a cor padrão do tipo.
As 8 cores da paleta do design são de todos. A loja vende cores exclusivas, que não
se confundem com elas, e as mais caras têm efeitos animados.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

_HEX = re.compile(r"^#[0-9A-F]{6}$")


class Efeito(StrEnum):
    """Animação de uma cor da loja. O desenho fica com o frontend; sem animação
    (ex.: `prefers-reduced-motion`), vale o hexadecimal da cor."""

    PULSAR = "pulsar"  # o brilho respira
    AURORA = "aurora"  # a cor passeia entre verde, ciano e violeta
    GALAXIA = "galaxia"  # estrelas orbitando o neurônio
    TEMPESTADE = "tempestade"  # faíscas de raio em volta
    ARCO_IRIS = "arco_iris"  # a cor percorre o arco-íris


@dataclass(frozen=True)
class CorLoja:
    """Uma cor que o estudante pode dar a uma matéria. Preço 0: de todos."""

    codigo: str
    nome: str
    hex: str
    preco: int = 0
    efeito: Efeito | None = None

    def __post_init__(self):
        if not _HEX.match(self.hex):
            raise ValueError("A cor precisa ser um hexadecimal #RRGGBB em maiúsculas.")
        if self.preco < 0:
            raise ValueError("O preço não pode ser negativo.")

    @property
    def gratuita(self) -> bool:
        return self.preco == 0


# A paleta das matérias do design (docs/design/README.md), de todos.
CORES_GRATUITAS: tuple[CorLoja, ...] = (
    CorLoja("violeta", "Violeta", "#8B7BFF"),
    CorLoja("ciano", "Ciano", "#3EE6E0"),
    CorLoja("verde", "Verde", "#5BE49B"),
    CorLoja("ambar", "Âmbar", "#FFC857"),
    CorLoja("laranja", "Laranja", "#FF8A5C"),
    CorLoja("rosa", "Rosa", "#FF6FB5"),
    CorLoja("azul", "Azul", "#6FA8FF"),
    CorLoja("lima", "Lima", "#C3E86B"),
)

# Os preços consideram 1 ATP por minuto de foco: a cor mais barata sai por quatro
# sessões de 25 min; o arco-íris, por umas 20 horas. Nenhuma lembra o vermelho da
# poda nem o cinza do neurônio podado.
CORES_DA_LOJA: tuple[CorLoja, ...] = (
    CorLoja("lavanda", "Lavanda", "#C9B3FF", 100),
    CorLoja("menta", "Menta", "#8AFFD0", 100),
    CorLoja("celeste", "Celeste", "#A6E3FF", 150),
    CorLoja("pessego", "Pêssego", "#FFC2A1", 150),
    CorLoja("magenta_neon", "Magenta neon", "#FF3DF0", 250),
    CorLoja("dourado", "Dourado", "#FFE14D", 250),
    CorLoja("prata_lunar", "Prata lunar", "#E4E8FF", 300),
    CorLoja("pulsar", "Pulsar", "#7DF9FF", 500, Efeito.PULSAR),
    CorLoja("aurora", "Aurora", "#5BFFB0", 700, Efeito.AURORA),
    CorLoja("galaxia", "Galáxia", "#B69CFF", 900, Efeito.GALAXIA),
    CorLoja("tempestade", "Tempestade", "#A8C8FF", 1000, Efeito.TEMPESTADE),
    CorLoja("arco_iris", "Arco-íris", "#FF7AD9", 1200, Efeito.ARCO_IRIS),
)

CATALOGO_CORES: tuple[CorLoja, ...] = CORES_GRATUITAS + CORES_DA_LOJA


def cor_por_codigo(
    codigo: str, catalogo: tuple[CorLoja, ...] = CATALOGO_CORES
) -> CorLoja | None:
    return next((cor for cor in catalogo if cor.codigo == codigo), None)


def cor_por_hex(
    hex_: str, catalogo: tuple[CorLoja, ...] = CATALOGO_CORES
) -> CorLoja | None:
    """A cor do catálogo com este hexadecimal (cada cor tem o seu), ou `None`."""
    alvo = hex_.upper()
    return next((cor for cor in catalogo if cor.hex == alvo), None)
