from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from app.application.rede import RedeNeuralService
from app.domain.entidades.neuronio import FabricaNeuronio, Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
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


class SessaoService:
    """Casos de uso da sessão de foco (issue #16).

    O servidor é a fonte da verdade do tempo: o cliente pode adiantar o próprio
    relógio, mas o horário usado aqui é sempre o do servidor (`relogio`). Toda
    sessão carregada passa antes pela expiração por abandono, então a regra de
    duração + 5 min vale mesmo sem a varredura periódica.

    Toda sessão que termina vira um neurônio na rede do estudante (#23): vivo, se
    foi concluída; morto e sem sinapses, se foi podada (poda sináptica). As ligações
    ficam a cargo da `RedeNeuralService`.
    """

    def __init__(
        self,
        sessoes: RepositorioSessao,
        rede: RedeNeuralService,
        relogio: Callable[[], datetime] = agora,
        materias: RepositorioMateria | None = None,
        fabrica: FabricaNeuronio | type[FabricaNeuronio] = FabricaNeuronio,
    ):
        self._sessoes = sessoes
        self._rede = rede
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
        self._sessoes.salvar(sessao)
        if sessao.codigo_estado == "podada":
            self._registrar_neuronio_podado(sessao)
        return sessao

    def concluir(
        self, usuario_id: UUID, sessao_id: UUID
    ) -> tuple[SessaoFoco, Neuronio]:
        sessao = self._carregar(usuario_id, sessao_id)
        instante = self._relogio()
        # Até 2 s antes do fim previsto conta como no tempo (diferença de relógio e
        # rede); a sessão termina no fim previsto, não antes dele.
        if sessao.fim_previsto - TOLERANCIA_RELOGIO <= instante < sessao.fim_previsto:
            instante = sessao.fim_previsto
        sessao.concluir(relogio=lambda: instante)

        neuronio = self._fabrica.criar(sessao)
        self._sessoes.salvar(sessao)
        self._rede.registrar(neuronio)
        return sessao, neuronio

    def desistir(self, usuario_id: UUID, sessao_id: UUID) -> SessaoFoco:
        sessao = self._carregar(usuario_id, sessao_id)
        sessao.desistir(relogio=self._relogio)
        self._sessoes.salvar(sessao)
        self._registrar_neuronio_podado(sessao)
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
            self._sessoes.salvar(sessao)
            self._registrar_neuronio_podado(sessao)
        return expirou

    def _registrar_neuronio_podado(self, sessao: SessaoFoco) -> None:
        """Poda sináptica (#23): a sessão podada deixa um neurônio morto na rede."""
        self._rede.registrar(self._fabrica.criar(sessao))
