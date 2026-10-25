from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from abc import ABC, abstractmethod
from typing import Any



@dataclass(frozen=True)
class SessaoConcluida:
    """Evento disparado quando o estudante finaliza a sessão com sucesso."""
    sessao_id: UUID
    usuario_id: UUID
    duracao_minutos: int
    conclusao: datetime
    materia_id: UUID | None = None

@dataclass(frozen=True)
class SessaoPodada:
    """Evento disparado quando o estudante desiste ou esgota a tolerância."""
    sessao_id: UUID
    usuario_id: UUID
    duracao_minutos: int
    podada_em: datetime
    materia_id: UUID | None = None



class ObservadorSessao(ABC):
    """ Interface que todo observador de sessão deve implementar """

    @abstractmethod
    def processar(self, evento: Any) -> None:
        pass


class PublicadorEventos:
    """ Gerencia as inscrições e distribui os eventos pelo sistema """
    
    def __init__(self) -> None:
        # Mapeia o tipo do evento para uma lista de observadores
        self._observadores: dict[type, list[ObservadorSessao]] = {}

    def inscrever(self, tipo_evento: type, observador: ObservadorSessao) -> None:
        if tipo_evento not in self._observadores:
            self._observadores[tipo_evento] = []
        self._observadores[tipo_evento].append(observador)

    def publicar(self, evento: Any) -> None:
        tipo_evento = type(evento)
        # Observadores recebem alerta quando o evento acontece
        for observador in self._observadores.get(tipo_evento, []):
            observador.processar(evento)