from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.domain.duracao import Duracao
from app.domain.entidades.base import Entidade
from app.domain.excecoes import HorarioInvalido, TransicaoInvalida
from app.domain.politica_interrupcao import (
    Interrupcao,
    ModoEstrito,
    PoliticaInterrupcao,
)
from app.domain.tempo import agora, exigir_fuso


class EstadoSessao(ABC):
    """
    Base abstrata para o ciclo de vida da sessão (padrão State, #10).

    Define as transições possíveis (concluir, podar, desistir). Por padrão, todas
    as ações lançam `TransicaoInvalida`. Os estados concretos devem sobrescrever
    apenas as transições que são permitidas para eles.
    """

    @property
    @abstractmethod
    def nome(self) -> str: ...

    @property
    @abstractmethod
    def codigo(self) -> str:
        """Identificador estável, sem acento, para gravar no banco e devolver na API."""

    def concluir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        raise TransicaoInvalida(f"Não é possível concluir uma sessão {self.nome}.")

    def podar(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        raise TransicaoInvalida(f"Não é possível podar uma sessão {self.nome}.")

    def desistir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        raise TransicaoInvalida(f"Não é possível desistir de uma sessão {self.nome}.")


class EmAndamento(EstadoSessao):
    """
    Estado inicial de uma sessão.

    Neste estado, o neurônio está crescendo. A sessão pode transicionar para
    Concluída (se o tempo previsto tiver passado) ou para Podada (em caso de
    distração ou desistência manual).
    """

    @property
    def nome(self) -> str:
        return "em andamento"

    @property
    def codigo(self) -> str:
        return "em_andamento"

    def concluir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        instante = relogio()
        if instante < sessao.fim_previsto:
            raise TransicaoInvalida("A sessão ainda não atingiu a duração planejada.")
        sessao._mudar_estado(Concluida(), instante)

    def podar(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        sessao._mudar_estado(Podada(), relogio())

    def desistir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        sessao._mudar_estado(Podada(), relogio())


class Concluida(EstadoSessao):
    """
    Estado final de sucesso.

    Representa uma sessão onde o tempo planejado foi totalmente cumprido e o
    neurônio foi formado com sucesso. Não aceita nenhuma nova transição.
    """

    @property
    def nome(self) -> str:
        return "concluída"

    @property
    def codigo(self) -> str:
        return "concluida"


class Podada(EstadoSessao):
    """
    Estado final de interrupção.

    Representa uma sessão que foi interrompida (seja pelo usuário saindo da tela
    no modo estrito ou por desistência manual). O neurônio correspondente morre
    e a sessão não aceita mais transições.
    """

    @property
    def nome(self) -> str:
        return "podada"

    @property
    def codigo(self) -> str:
        return "podada"


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
        estado: EstadoSessao | None = None,
        id: UUID | None = None,
        politica: PoliticaInterrupcao | None = None,
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
        self._estado = estado or EmAndamento()
        self._politica = politica or ModoEstrito()
        self._historico_interrupcoes: list[Interrupcao] = []

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
        return self._inicio + self._duracao.como_timedelta()

    @property
    def encerrada_em(self) -> datetime | None:
        return self._encerrada_em

    @property
    def estado(self) -> str:
        return self._estado.nome

    @property
    def codigo_estado(self) -> str:
        return self._estado.codigo

    @property
    def politica(self) -> PoliticaInterrupcao:
        return self._politica

    @property
    def historico_interrupcoes(self) -> list[Interrupcao]:
        return list(self._historico_interrupcoes)

    def _mudar_estado(self, novo_estado: EstadoSessao, instante: datetime) -> None:
        self._estado = novo_estado
        self._encerrada_em = instante

    def _relogio_validado(
        self, relogio: Callable[[], datetime]
    ) -> Callable[[], datetime]:
        """Garante que o instante lido do relógio tem fuso e não é anterior ao início,
        as mesmas regras que o construtor aplica a `encerrada_em`."""

        def ler() -> datetime:
            instante = exigir_fuso(relogio(), "instante")
            if instante < self._inicio:
                raise HorarioInvalido("A sessão não pode terminar antes de começar.")
            return instante

        return ler

    def concluir(self, relogio: Callable[[], datetime] = agora) -> None:
        self._estado.concluir(self, self._relogio_validado(relogio))

    def podar(self, relogio: Callable[[], datetime] = agora) -> None:
        self._estado.podar(self, self._relogio_validado(relogio))

    def desistir(self, relogio: Callable[[], datetime] = agora) -> None:
        self._estado.desistir(self, self._relogio_validado(relogio))

    def __repr__(self) -> str:
        return (
            f"SessaoFoco(id={self.id}, usuario_id={self._usuario_id}, "
            f"duracao={self._duracao.minutos} min, estado={self.estado})"
        )

    def registrar_interrupcao(
        self, interrupcao: Interrupcao, relogio: Callable[[], datetime] = agora
    ) -> None:
        """
        Recebe uma interrupção, delega a decisão de poda para a Strategy
        e salva no histórico se a sessão continuar viva.
        """
        if self._estado.codigo != "em_andamento":
            msg = f"Não é possível interromper uma sessão {self.estado}."
            raise TransicaoInvalida(msg)

        if self._politica.deve_podar(self, interrupcao, self._historico_interrupcoes):
            self.podar(relogio)
        else:
            self._historico_interrupcoes.append(interrupcao)
