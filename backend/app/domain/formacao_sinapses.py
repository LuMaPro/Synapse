from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.entidades.neuronio import Neuronio

if TYPE_CHECKING:
    from app.domain.rede_neural import RedeNeural

PESO_INICIAL = 1


@dataclass(frozen=True)
class Conexao:
    """Ligação proposta pela regra: um neurônio que já está na rede e o peso."""

    alvo_id: UUID
    peso: int


class RegraFormacaoSinapses(ABC):
    """Decide a quem um neurônio recém-nascido se liga (padrão Strategy, #23).

    A regra só propõe as ligações. Quem garante as invariantes (sem sinapse
    repetida, sem ligação de um neurônio com ele mesmo, só neurônios vivos) é a
    `RedeNeural`, valha a regra que valer. Trocar a regra não mexe na rede nem em
    quem registra os neurônios (`SessaoService`).
    """

    @abstractmethod
    def conexoes(self, novo: Neuronio, rede: "RedeNeural") -> list[Conexao]:
        """Ligações do neurônio `novo`, que ainda não está na `rede`."""
        ...


class RegraRecentesEMesmaMateria(RegraFormacaoSinapses):
    """Regra padrão: o neurônio novo se liga aos `recentes` neurônios vivos mais
    recentes e ao último vivo da mesma matéria.

    A ligação com a matéria é reforçada: o peso é o da ligação que trouxe o último
    neurônio para a trilha da matéria, mais 1 (até `peso_maximo`). Então, cada vez
    que o estudante volta a uma matéria, a ligação fica mais forte. Se o último da
    matéria também está entre os recentes, sai uma sinapse só, com o peso reforçado.
    Neurônio sem matéria só se liga aos recentes.
    """

    def __init__(self, recentes: int = 2, peso_maximo: int = 5):
        if recentes < 0:
            raise ValueError("O número de neurônios recentes não pode ser negativo.")
        if peso_maximo < PESO_INICIAL:
            raise ValueError(f"O peso máximo deve ser pelo menos {PESO_INICIAL}.")
        self._recentes = recentes
        self._peso_maximo = peso_maximo

    def conexoes(self, novo: Neuronio, rede: "RedeNeural") -> list[Conexao]:
        anteriores = [n for n in rede.vivos if n.criado_em <= novo.criado_em]
        pesos = {
            n.id: PESO_INICIAL
            for n in anteriores[max(0, len(anteriores) - self._recentes) :]
        }

        ultimo_da_materia = self._ultimo_da_materia(novo, anteriores)
        if ultimo_da_materia is not None:
            peso = self._peso_da_trilha(ultimo_da_materia, rede) + 1
            pesos[ultimo_da_materia.id] = min(peso, self._peso_maximo)

        return [Conexao(alvo_id, peso) for alvo_id, peso in pesos.items()]

    @staticmethod
    def _ultimo_da_materia(
        novo: Neuronio, anteriores: list[Neuronio]
    ) -> Neuronio | None:
        if novo.materia_id is None:
            return None
        return next(
            (n for n in reversed(anteriores) if n.materia_id == novo.materia_id), None
        )

    @staticmethod
    def _peso_da_trilha(neuronio: Neuronio, rede: "RedeNeural") -> int:
        """Peso da ligação que trouxe `neuronio` para a trilha da matéria dele, ou o
        peso inicial se ele foi o primeiro da matéria."""
        pesos = [
            sinapse.peso
            for sinapse in rede.sinapses_de(neuronio.id)
            if sinapse.destino_id == neuronio.id
            and (origem := rede.neuronio(sinapse.origem_id)) is not None
            and origem.materia_id == neuronio.materia_id
        ]
        return max(pesos, default=PESO_INICIAL)
