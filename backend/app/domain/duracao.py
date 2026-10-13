from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from app.domain.excecoes import DuracaoInvalida


@dataclass(frozen=True)
class Duracao:
    """Objeto de valor: duração planejada de uma sessão de foco, em minutos.

    É imutável e sempre válido: se o objeto existe, a duração respeita as regras.
    Assim SessaoFoco e Neuronio não repetem a validação.
    """

    MINIMA: ClassVar[int] = 10
    MAXIMA: ClassVar[int] = 120
    PASSO: ClassVar[int] = 5

    minutos: int

    def __post_init__(self):
        # bool é subclasse de int em Python: sem esse teste, True passaria como 1.
        if isinstance(self.minutos, bool) or not isinstance(self.minutos, int):
            raise DuracaoInvalida("A duração precisa ser um número inteiro de minutos.")
        if not self.MINIMA <= self.minutos <= self.MAXIMA:
            raise DuracaoInvalida(
                f"A duração precisa estar entre {self.MINIMA} e {self.MAXIMA} minutos."
            )
        if self.minutos % self.PASSO != 0:
            raise DuracaoInvalida(
                f"A duração precisa ser múltipla de {self.PASSO} minutos."
            )

    def como_timedelta(self) -> timedelta:
        return timedelta(minutes=self.minutos)
