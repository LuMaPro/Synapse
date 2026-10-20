from datetime import datetime
from uuid import UUID

from app.domain.duracao import Duracao
from app.domain.entidades.base import Entidade
from app.domain.tempo import agora, exigir_fuso


class Neuronio(Entidade):
    """Neurônio que nasce quando uma sessão de foco termina (#16 e #23).

    A duração é a da sessão. Sessão concluída gera um neurônio vivo; sessão podada
    gera um neurônio morto (`vivo=False`), que aparece cinza na rede e não forma
    sinapses (poda sináptica, #23). A matéria vem da sessão (#27). O tipo (granular,
    piramidal, Purkinje) vem com o Factory Method (#22).
    """

    def __init__(
        self,
        usuario_id: UUID,
        sessao_id: UUID,
        duracao_minutos: int,
        *,
        vivo: bool = True,
        materia_id: UUID | None = None,
        criado_em: datetime | None = None,
        id: UUID | None = None,
    ):
        super().__init__(id)
        self._usuario_id = usuario_id
        self._sessao_id = sessao_id
        self._duracao = Duracao(duracao_minutos)
        self._vivo = vivo
        self._materia_id = materia_id
        self._criado_em = (
            exigir_fuso(criado_em, "criado_em") if criado_em is not None else agora()
        )

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def sessao_id(self) -> UUID:
        return self._sessao_id

    @property
    def duracao(self) -> Duracao:
        return self._duracao

    @property
    def vivo(self) -> bool:
        return self._vivo

    @property
    def materia_id(self) -> UUID | None:
        return self._materia_id

    @property
    def criado_em(self) -> datetime:
        return self._criado_em

    def __repr__(self) -> str:
        return f"Neuronio(id={self.id}, sessao_id={self._sessao_id})"
