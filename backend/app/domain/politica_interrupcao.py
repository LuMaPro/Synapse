from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.domain.excecoes import PoliticaInvalida
from app.domain.tempo import exigir_fuso

if TYPE_CHECKING:
    from app.domain.entidades.sessao_foco import SessaoFoco


@dataclass(frozen=True)
class Interrupcao:
    """Representa um momento em que o usuário saiu da tela de foco."""

    saida: datetime
    retorno: datetime | None = None

    def __post_init__(self):
        exigir_fuso(self.saida, "saida")
        if self.retorno is not None:
            exigir_fuso(self.retorno, "retorno")
            if self.retorno < self.saida:
                raise ValueError("O retorno não pode ser anterior à saída.")

    @property
    def segundos_fora(self) -> float:
        if self.retorno is None:
            return 0.0
        return (self.retorno - self.saida).total_seconds()


class PoliticaInterrupcao(ABC):
    """
    Base abstrata para a família de algoritmos de interrupção (Strategy, #11).
    """

    @property
    @abstractmethod
    def codigo(self) -> str:
        """Identificador estável do modo, para gravar no banco e trocar com a API."""

    @abstractmethod
    def deve_podar(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> bool: ...

    def instante_da_poda(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> datetime:
        """Quando a sessão morreu, se `deve_podar` disse que sim.

        Por padrão, no momento da saída. Não é a hora em que o aviso chega ao
        servidor, que pode vir bem depois (ex.: o estudante só voltou mais tarde).
        """
        return nova_interrupcao.saida


class ModoEstrito(PoliticaInterrupcao):
    """Qualquer saída poda a sessão imediatamente."""

    @property
    def codigo(self) -> str:
        return "estrito"

    def deve_podar(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> bool:
        return True


class ModoTolerante(PoliticaInterrupcao):
    """Permite saídas curtas até um limite de 10% da duração total da sessão."""

    def __init__(self, proporcao_tolerancia: float = 0.10):
        self.proporcao = proporcao_tolerancia

    @property
    def codigo(self) -> str:
        return "tolerante"

    def deve_podar(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> bool:
        if nova_interrupcao.retorno is None:
            return False  # Se ainda não voltou, não temos como saber o tempo total fora

        return nova_interrupcao.segundos_fora > self._saldo_restante(sessao, historico)

    def instante_da_poda(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> datetime:
        """A sessão morre quando o saldo acaba, no meio da saída que o estourou."""
        saldo = self._saldo_restante(sessao, historico)
        return nova_interrupcao.saida + timedelta(seconds=saldo)

    def _saldo_restante(
        self, sessao: "SessaoFoco", historico: list[Interrupcao]
    ) -> float:
        """Segundos que ainda podem ser passados fora da tela, somando o histórico."""
        tempo_total_permitido = (
            sessao.duracao.como_timedelta().total_seconds() * self.proporcao
        )
        tempo_ja_gasto = sum(i.segundos_fora for i in historico)
        return max(0.0, tempo_total_permitido - tempo_ja_gasto)


_POLITICAS: dict[str, type[PoliticaInterrupcao]] = {
    "estrito": ModoEstrito,
    "tolerante": ModoTolerante,
}


def politica_por_codigo(codigo: str) -> PoliticaInterrupcao:
    """Cria a política a partir do código vindo da API ou do banco."""
    try:
        return _POLITICAS[codigo]()
    except KeyError:
        validos = ", ".join(_POLITICAS)
        raise PoliticaInvalida(
            f"Modo desconhecido: {codigo!r}. Use um destes: {validos}."
        ) from None
