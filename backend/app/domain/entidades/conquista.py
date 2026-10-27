from datetime import datetime
from uuid import UUID

from app.domain.entidades.base import Entidade
from app.domain.tempo import exigir_fuso


class ConquistaDesbloqueada(Entidade):
    """Conquista que o estudante já desbloqueou (#32).

    Guarda só o código da regra (ver `app/domain/conquistas.py`) e quando ela foi
    cumprida: nome, descrição e meta ficam na regra, então podem mudar sem migrar
    dados. Uma conquista desbloqueada não volta a ficar bloqueada.
    """

    def __init__(
        self,
        usuario_id: UUID,
        codigo: str,
        desbloqueada_em: datetime,
        *,
        id: UUID | None = None,
    ):
        super().__init__(id)
        if not codigo:
            raise ValueError("A conquista precisa do código da regra.")
        self._usuario_id = usuario_id
        self._codigo = codigo
        self._desbloqueada_em = exigir_fuso(desbloqueada_em, "desbloqueada_em")

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def desbloqueada_em(self) -> datetime:
        return self._desbloqueada_em

    def __repr__(self) -> str:
        return f"ConquistaDesbloqueada(codigo={self._codigo!r})"
