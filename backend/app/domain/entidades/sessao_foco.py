from datetime import datetime
from uuid import UUID

from app.domain.duracao import Duracao
from app.domain.entidades.base import Entidade
from app.domain.excecoes import HorarioInvalido
from app.domain.tempo import agora, exigir_fuso


class SessaoFoco(Entidade):
    """Sessão de foco de um estudante.

    Por enquanto guarda os dados e os horários da sessão. O ciclo de vida (concluir,
    podar, desistir) vem com o padrão State (#10), e a política de interrupção com o
    Strategy (#11).
    """

    def __init__(
        self,
        usuario_id: UUID,
        duracao_minutos: int,
        *,
        inicio: datetime | None = None,
        encerrada_em: datetime | None = None,
        id: UUID | None = None,
    ):
        super().__init__(id)
        self._usuario_id = usuario_id
        self._duracao = Duracao(duracao_minutos)
        self._inicio = exigir_fuso(inicio, "inicio") if inicio is not None else agora()
        if encerrada_em is not None:
            exigir_fuso(encerrada_em, "encerrada_em")
            if encerrada_em < self._inicio:
                raise HorarioInvalido("A sessão não pode terminar antes de começar.")
        self._encerrada_em = encerrada_em

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def duracao(self) -> Duracao:
        return self._duracao

    @property
    def inicio(self) -> datetime:
        return self._inicio

    @property
    def fim_previsto(self) -> datetime:
        """Horário em que a sessão termina se o estudante não sair da tela."""
        return self._inicio + self._duracao.como_timedelta()

    @property
    def encerrada_em(self) -> datetime | None:
        """Horário real de término; None enquanto a sessão não terminou."""
        return self._encerrada_em

    def __repr__(self) -> str:
        return (
            f"SessaoFoco(id={self.id}, usuario_id={self._usuario_id}, "
            f"duracao={self._duracao.minutos} min)"
        )
