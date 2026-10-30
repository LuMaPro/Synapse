import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.entidades.neuronio import FabricaNeuronio, Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.eventos import PublicadorEventos, SessaoConcluida, SessaoPodada
from app.domain.excecoes import (
    HorarioInvalido,
    MateriaNaoEncontrada,
    SessaoAtivaExistente,
    SessaoNaoEncontrada,
)
from app.domain.politica_interrupcao import Interrupcao, politica_por_codigo
from app.domain.repositorios import RepositorioMateria, RepositorioSessao
from app.domain.tempo import agora

# Diferença de relógio e rede aceita entre o cliente e o servidor (#16).
TOLERANCIA_RELOGIO = timedelta(seconds=2)


@dataclass(frozen=True)
class PaginaHistorico:
    """Uma página do histórico de sessões (#29)."""

    sessoes: list[SessaoFoco]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        """Quantidade de páginas; a lista vazia ainda tem uma (vazia)."""
        return max(1, math.ceil(self.total / self.tamanho))


class SessaoService:
    """Casos de uso da sessão de foco (issue #16).

    O servidor é a fonte da verdade do tempo: o cliente pode adiantar o próprio
    relógio, mas o horário usado aqui é sempre o do servidor (`relogio`). Toda
    sessão carregada passa antes pela expiração por abandono, então a regra de
    duração + 5 min vale mesmo sem a varredura periódica.

    Toda sessão que termina vira um neurônio (#23), criado pela `FabricaNeuronio`
    (#22): vivo, se foi concluída; morto, se foi podada. A exceção é a sessão podada
    antes de 5 min de foco: ela é apagada, sem neurônio e sem evento, para não encher
    o histórico e o banco de começos desistidos. O serviço só publica o evento
    (`SessaoConcluida` ou `SessaoPodada`, #24); quem coloca o neurônio na rede,
    desbloqueia as conquistas (#32) e credita o ATP (#34), e no futuro atualiza as
    estatísticas, são os observadores inscritos.
    """

    def __init__(
        self,
        sessoes: RepositorioSessao,
        publicador: PublicadorEventos,
        relogio: Callable[[], datetime] = agora,
        materias: RepositorioMateria | None = None,
        fabrica: FabricaNeuronio | type[FabricaNeuronio] = FabricaNeuronio,
    ):
        self._sessoes = sessoes
        self._publicador = publicador
        self._relogio = relogio
        self._materias = materias
        self._fabrica = fabrica

    def iniciar(
        self,
        usuario_id: UUID,
        duracao_minutos: int,
        modo: str,
        materia_id: UUID | None = None,
    ) -> SessaoFoco:
        if self.buscar_ativa(usuario_id) is not None:
            raise SessaoAtivaExistente("Já existe uma sessão de foco em andamento.")
        if materia_id is not None:
            if (
                self._materias is None
                or self._materias.buscar_por_usuario_e_id(usuario_id, materia_id)
                is None
            ):
                raise MateriaNaoEncontrada("Matéria não encontrada.")
        sessao = SessaoFoco(
            usuario_id,
            duracao_minutos,
            inicio=self._relogio(),
            politica=politica_por_codigo(modo),
            materia_id=materia_id,
        )
        self._sessoes.salvar(sessao)
        return sessao

    def buscar_ativa(self, usuario_id: UUID) -> SessaoFoco | None:
        sessao = self._sessoes.buscar_ativa_por_usuario(usuario_id)
        if sessao is None:
            return None
        if self._expirar(sessao):
            return None
        return sessao

    def historico(
        self,
        usuario_id: UUID,
        *,
        de: datetime | None = None,
        ate: datetime | None = None,
        estado: str | None = None,
        pagina: int = 1,
        tamanho: int = 20,
    ) -> PaginaHistorico:
        """As sessões do estudante, da mais recente para a mais antiga (#29).

        Antes, poda a sessão abandonada, se houver: senão ela apareceria como em
        andamento até alguém acessá-la.
        """
        if pagina < 1 or tamanho < 1:
            raise ValueError("A página e o tamanho começam em 1.")
        self.buscar_ativa(usuario_id)
        sessoes, total = self._sessoes.listar_historico(
            usuario_id,
            de=de,
            ate=ate,
            estado=estado,
            deslocamento=(pagina - 1) * tamanho,
            limite=tamanho,
        )
        return PaginaHistorico(sessoes, total, pagina, tamanho)

    def registrar_interrupcao(
        self,
        usuario_id: UUID,
        sessao_id: UUID,
        saida: datetime,
        retorno: datetime | None,
    ) -> SessaoFoco:
        sessao = self._carregar(usuario_id, sessao_id)
        limite = self._relogio() + TOLERANCIA_RELOGIO
        if saida > limite or (retorno is not None and retorno > limite):
            raise HorarioInvalido("A saída não pode estar no futuro.")
        if saida < sessao.inicio:
            raise HorarioInvalido("A saída não pode ser anterior ao início da sessão.")
        sessao.registrar_interrupcao(Interrupcao(saida=saida, retorno=retorno))
        if sessao.codigo_estado == "podada":
            self._registrar_poda(sessao)
        else:
            self._sessoes.salvar(sessao)
        return sessao

    def concluir(
        self, usuario_id: UUID, sessao_id: UUID, *, forcar_conclusao: bool = False
    ) -> tuple[SessaoFoco, Neuronio]:
        sessao = self._carregar(usuario_id, sessao_id)
        instante = self._relogio()
        # No modo de desenvolvimento ou debug, permite forçar a conclusão imediatamente.
        if forcar_conclusao and instante < sessao.fim_previsto:
            instante = sessao.fim_previsto
        # Até 2 s antes do fim previsto conta como no tempo (diferença de relógio e
        # rede); a sessão termina no fim previsto, não antes dele.
        elif sessao.fim_previsto - TOLERANCIA_RELOGIO <= instante < sessao.fim_previsto:
            instante = sessao.fim_previsto
        sessao.concluir(relogio=lambda: instante)

        neuronio = self._fabrica.criar(sessao)
        self._sessoes.salvar(sessao)
        self._publicador.publicar(
            SessaoConcluida(
                sessao.id,
                sessao.usuario_id,
                sessao.duracao.minutos,
                instante,
                sessao.materia_id,
                neuronio=neuronio,
            )
        )
        return sessao, neuronio

    def desistir(self, usuario_id: UUID, sessao_id: UUID) -> SessaoFoco:
        sessao = self._carregar(usuario_id, sessao_id)
        sessao.desistir(relogio=self._relogio)
        self._registrar_poda(sessao)
        return sessao

    def podar_orfas(self) -> int:
        """Varredura das sessões abandonadas. Devolve quantas foram podadas."""
        return sum(self._expirar(s) for s in self._sessoes.listar_em_andamento())

    def _carregar(self, usuario_id: UUID, sessao_id: UUID) -> SessaoFoco:
        sessao = self._sessoes.buscar_por_id(sessao_id)
        # Sessão de outro estudante responde igual a inexistente: não revela que existe.
        if sessao is None or sessao.usuario_id != usuario_id:
            raise SessaoNaoEncontrada("Sessão de foco não encontrada.")
        self._expirar(sessao)
        return sessao

    def _expirar(self, sessao: SessaoFoco) -> bool:
        expirou = sessao.expirar_se_abandonada(self._relogio())
        if expirou:
            self._registrar_poda(sessao)
        return expirou

    def _registrar_poda(self, sessao: SessaoFoco) -> None:
        """Grava a poda e publica o neurônio morto, ou apaga a sessão curta demais."""
        if sessao.curta_demais:
            self._sessoes.remover(sessao.id)
            return
        self._sessoes.salvar(sessao)
        self._publicar_poda(sessao)

    def _publicar_poda(self, sessao: SessaoFoco) -> None:
        """Poda sináptica (#23): a sessão podada deixa um neurônio morto na rede."""
        self._publicador.publicar(
            SessaoPodada(
                sessao.id,
                sessao.usuario_id,
                sessao.duracao.minutos,
                sessao.encerrada_em,
                sessao.materia_id,
                neuronio=self._fabrica.criar(sessao),
            )
        )
