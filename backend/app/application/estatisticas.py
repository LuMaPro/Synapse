from collections.abc import Callable
from datetime import datetime, tzinfo
from uuid import UUID

from app.application.sessoes import SessaoService
from app.domain.conquistas import FUSO_DOS_DIAS
from app.domain.estatisticas import (
    EstatisticasFoco,
    PeriodoEstatisticas,
    calcular_estatisticas,
    intervalo_do_periodo,
    periodo_por_codigo,
)
from app.domain.repositorios import RepositorioMateria, RepositorioSessao
from app.domain.tempo import agora


class EstatisticasService:
    """Caso de uso do painel de estatísticas de foco (#30).

    Antes de calcular, verifica se há uma sessão abandonada em andamento e a poda
    (pelo `SessaoService`, quando fornecido, para que o evento `SessaoPodada` também
    chegue à rede neural). Em seguida busca só as sessões do período e as matérias do
    estudante e delega a conta pura a `calcular_estatisticas`.
    """

    def __init__(
        self,
        sessoes: RepositorioSessao,
        materias: RepositorioMateria,
        *,
        sessao_service: SessaoService | None = None,
        relogio: Callable[[], datetime] = agora,
        fuso: tzinfo = FUSO_DOS_DIAS,
    ):
        self._sessoes = sessoes
        self._materias = materias
        self._sessao_service = sessao_service
        self._relogio = relogio
        self._fuso = fuso

    def consultar(
        self,
        usuario_id: UUID,
        periodo: PeriodoEstatisticas | str = PeriodoEstatisticas.SEMANA,
    ) -> EstatisticasFoco:
        periodo_enum = periodo_por_codigo(periodo)
        instante = self._relogio()
        self._expirar_abandonada(usuario_id, instante)

        inicio_periodo, fim_periodo, _, _ = intervalo_do_periodo(
            periodo_enum, instante, self._fuso
        )
        sessoes = self._sessoes.listar_por_periodo(
            usuario_id, de=inicio_periodo, ate=fim_periodo
        )
        materias = self._materias.listar_por_usuario(usuario_id)
        return calcular_estatisticas(
            sessoes,
            periodo=periodo_enum,
            instante=instante,
            materias=materias,
            fuso=self._fuso,
        )

    def _expirar_abandonada(self, usuario_id: UUID, instante: datetime) -> None:
        if self._sessao_service is not None:
            self._sessao_service.buscar_ativa(usuario_id)
            return
        ativa = self._sessoes.buscar_ativa_por_usuario(usuario_id)
        if ativa is not None and ativa.expirar_se_abandonada(instante):
            self._sessoes.salvar(ativa)

