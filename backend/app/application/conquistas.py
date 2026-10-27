from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, tzinfo
from uuid import UUID

from app.domain.conquistas import (
    CATALOGO_CONQUISTAS,
    FUSO_DOS_DIAS,
    RegraConquista,
    ResumoFoco,
    Sequencia,
)
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.repositorios import RepositorioConquista, RepositorioRedeNeural
from app.domain.tempo import agora


@dataclass(frozen=True)
class SituacaoConquista:
    """Uma conquista do catálogo, do ponto de vista de um estudante."""

    regra: RegraConquista
    progresso: int
    desbloqueada_em: datetime | None

    @property
    def desbloqueada(self) -> bool:
        return self.desbloqueada_em is not None


@dataclass(frozen=True)
class PainelConquistas:
    """A sequência de dias e todas as conquistas, bloqueadas e desbloqueadas."""

    sequencia: Sequencia
    conquistas: list[SituacaoConquista]


class ConquistaService:
    """Casos de uso das conquistas e da sequência de dias (#32).

    As regras vêm de um catálogo (`CATALOGO_CONQUISTAS`, por padrão), e o serviço
    trata todas do mesmo jeito: monta o resumo do foco do estudante a partir da rede
    neural e pergunta a cada regra se ela foi cumprida. Quem chama `avaliar` ao fim
    de cada sessão concluída é o observador `AvaliadorConquistas` (#24).
    """

    def __init__(
        self,
        conquistas: RepositorioConquista,
        redes: RepositorioRedeNeural,
        regras: Iterable[RegraConquista] = CATALOGO_CONQUISTAS,
        relogio: Callable[[], datetime] = agora,
        fuso: tzinfo = FUSO_DOS_DIAS,
    ):
        self._conquistas = conquistas
        self._redes = redes
        self._regras = tuple(regras)
        codigos = [r.codigo for r in self._regras]
        if len(set(codigos)) != len(codigos):
            raise ValueError("Cada conquista do catálogo precisa de um código próprio.")
        self._relogio = relogio
        self._fuso = fuso

    def avaliar(
        self, usuario_id: UUID, instante: datetime | None = None
    ) -> list[ConquistaDesbloqueada]:
        """Desbloqueia, com a data `instante`, as conquistas cumpridas que ainda
        estavam bloqueadas. Devolve só as que acabaram de ser desbloqueadas."""
        _, _, novas = self._avaliar(usuario_id, instante or self._relogio())
        return novas

    def consultar(self, usuario_id: UUID) -> PainelConquistas:
        """A sequência de dias e todas as conquistas, com o progresso de cada uma.

        Antes, desbloqueia o que já estiver cumprido: assim quem focava antes de as
        conquistas existirem já as encontra desbloqueadas na primeira consulta.
        """
        resumo, desbloqueadas, _ = self._avaliar(usuario_id, self._relogio())
        return PainelConquistas(
            resumo.sequencia,
            [
                SituacaoConquista(
                    regra, regra.progresso(resumo), desbloqueadas.get(regra.codigo)
                )
                for regra in self._regras
            ],
        )

    def _avaliar(
        self, usuario_id: UUID, instante: datetime
    ) -> tuple[ResumoFoco, dict[str, datetime], list[ConquistaDesbloqueada]]:
        resumo = ResumoFoco.da_rede(
            self._redes.carregar(usuario_id), instante, self._fuso
        )
        desbloqueadas = {
            c.codigo: c.desbloqueada_em
            for c in self._conquistas.listar_por_usuario(usuario_id)
        }
        novas = []
        for regra in self._regras:
            if regra.codigo not in desbloqueadas and regra.cumprida(resumo):
                conquista = ConquistaDesbloqueada(usuario_id, regra.codigo, instante)
                self._conquistas.salvar(conquista)
                desbloqueadas[regra.codigo] = instante
                novas.append(conquista)
        return resumo, desbloqueadas, novas
