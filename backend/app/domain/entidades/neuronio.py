from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from types import MethodType
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.duracao import Duracao
from app.domain.entidades.base import Entidade
from app.domain.excecoes import DuracaoInvalida
from app.domain.tempo import agora, exigir_fuso

if TYPE_CHECKING:
    from app.domain.entidades.sessao_foco import SessaoFoco

COR_PODADO = "#4A4F6E"


class TipoNeuronio(ABC):
    """Base abstrata das espécies de neurônio (issue #22).

    Cada tipo concreto define a faixa de duração que o gera (`duracao_minima` e
    `duracao_maxima`, em minutos) e os atributos visuais usados na rede e na
    animação: `nome`, `cor`, `numero_dendritos` e `raio`.
    """

    duracao_minima: int = Duracao.MINIMA
    duracao_maxima: int | None = None

    @property
    @abstractmethod
    def nome(self) -> str: ...

    @property
    @abstractmethod
    def cor(self) -> str: ...

    @property
    @abstractmethod
    def numero_dendritos(self) -> int: ...

    @property
    @abstractmethod
    def raio(self) -> float: ...

    @property
    def codigo(self) -> str:
        """Identificador estável em minúsculas para a API."""
        return self.nome.lower()

    def aceita(self, duracao_minutos: int) -> bool:
        """Indica se a duração (em minutos) cai na faixa deste tipo."""
        if duracao_minutos < self.duracao_minima:
            return False
        if self.duracao_maxima is not None and duracao_minutos > self.duracao_maxima:
            return False
        return True

    def __eq__(self, outro: object) -> bool:
        return type(self) is type(outro)

    def __hash__(self) -> int:
        return hash(type(self))

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class Granular(TipoNeuronio):
    """Neurônio de sessões curtas (10 a 24 min): corpo pequeno e dendritos curtos."""

    duracao_minima = 10
    duracao_maxima = 24

    @property
    def nome(self) -> str:
        return "Granular"

    @property
    def cor(self) -> str:
        return "#3EE6E0"

    @property
    def numero_dendritos(self) -> int:
        return 3

    @property
    def raio(self) -> float:
        return 4.5


class Piramidal(TipoNeuronio):
    """Neurônio de sessões médias (25 a 59 min): corpo triangular e dendrito apical."""

    duracao_minima = 25
    duracao_maxima = 59

    @property
    def nome(self) -> str:
        return "Piramidal"

    @property
    def cor(self) -> str:
        return "#8B7BFF"

    @property
    def numero_dendritos(self) -> int:
        return 5

    @property
    def raio(self) -> float:
        return 6.5


class Purkinje(TipoNeuronio):
    """Neurônio de sessões longas (60+ min): corpo grande e dendritos em leque."""

    duracao_minima = 60
    duracao_maxima = None

    @property
    def nome(self) -> str:
        return "Purkinje"

    @property
    def cor(self) -> str:
        return "#FFC857"

    @property
    def numero_dendritos(self) -> int:
        return 8

    @property
    def raio(self) -> float:
        return 9.0


class Neuronio(Entidade):
    """Neurônio que nasce quando uma sessão de foco termina (#16, #22 e #23).

    A duração é a da sessão. Sessão concluída gera um neurônio vivo; sessão podada
    gera um neurônio morto (`vivo=False`), que aparece cinza na rede e não forma
    sinapses (poda sináptica, #23). A matéria vem da sessão (#27), e o tipo visual
    (`Granular`, `Piramidal`, `Purkinje`) é escolhido pela `FabricaNeuronio` (#22).
    """

    def __init__(
        self,
        usuario_id: UUID,
        sessao_id: UUID,
        duracao_minutos: int,
        *,
        tipo: TipoNeuronio | None = None,
        vivo: bool = True,
        materia_id: UUID | None = None,
        criado_em: datetime | None = None,
        id: UUID | None = None,
    ):
        super().__init__(id)
        self._usuario_id = usuario_id
        self._sessao_id = sessao_id
        self._duracao = Duracao(duracao_minutos)
        if tipo is not None and not isinstance(tipo, TipoNeuronio):
            raise TypeError("O tipo do neurônio precisa ser um TipoNeuronio.")
        self._tipo = (
            tipo
            if tipo is not None
            else FabricaNeuronio.tipo_para(self._duracao.minutos)
        )
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
    def tipo(self) -> TipoNeuronio:
        return self._tipo

    @property
    def cor(self) -> str:
        """Cor do tipo quando vivo; neurônio podado é sempre cinza (#23)."""
        return self._tipo.cor if self._vivo else COR_PODADO

    @property
    def numero_dendritos(self) -> int:
        return self._tipo.numero_dendritos

    @property
    def raio(self) -> float:
        return self._tipo.raio

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


class _MetodoFabrica:
    """Permite chamar `FabricaNeuronio.criar(sessao)` direto na classe ou numa
    instância configurada com outros tipos (`FabricaNeuronio(tipos).criar(sessao)`)."""

    def __init__(self, func):
        self._func = func

    def __get__(self, instancia, dono=None):
        alvo = instancia if instancia is not None else dono()
        return MethodType(self._func, alvo)


class FabricaNeuronio:
    """Decide qual `TipoNeuronio` criar a partir da sessão (Factory Method, #22).

    Quem chama (`SessaoService`) só entrega a `SessaoFoco` para `criar(sessao)` e
    recebe o `Neuronio` pronto, sem conhecer as faixas de duração nem as classes
    concretas de tipo. Novos tipos entram na fábrica sem alterar quem a chama.
    """

    TIPOS_PADRAO: tuple[TipoNeuronio, ...] = (Granular(), Piramidal(), Purkinje())

    def __init__(self, tipos: Iterable[TipoNeuronio] | None = None):
        escolhidos = tuple(self.TIPOS_PADRAO if tipos is None else tipos)
        if not escolhidos:
            raise ValueError("A fábrica precisa de pelo menos um tipo de neurônio.")
        # Tipos com faixa mais específica (maior duração mínima, ou limite máximo
        # definido) vêm primeiro, então um tipo novo pode especializar uma subfaixa
        # sem precisar alterar os existentes.
        self._tipos = tuple(
            sorted(
                escolhidos,
                key=lambda t: (-t.duracao_minima, t.duracao_maxima is None),
            )
        )

    @property
    def tipos(self) -> tuple[TipoNeuronio, ...]:
        return self._tipos

    @_MetodoFabrica
    def tipo_para(self, duracao_minutos: int) -> TipoNeuronio:
        """Escolhe o `TipoNeuronio` pela faixa de duração (em minutos)."""
        if isinstance(duracao_minutos, bool) or not isinstance(duracao_minutos, int):
            raise DuracaoInvalida("A duração precisa ser um número inteiro de minutos.")
        for tipo in self._tipos:
            if tipo.aceita(duracao_minutos):
                return tipo
        raise DuracaoInvalida(
            f"Nenhum tipo de neurônio definido para {duracao_minutos} minutos."
        )

    @_MetodoFabrica
    def criar(self, sessao: "SessaoFoco") -> Neuronio:
        """Cria o `Neuronio` correspondente à `sessao`."""
        tipo = self.tipo_para(sessao.duracao.minutos)
        return Neuronio(
            sessao.usuario_id,
            sessao.id,
            sessao.duracao.minutos,
            tipo=tipo,
            vivo=sessao.codigo_estado != "podada",
            materia_id=sessao.materia_id,
            criado_em=sessao.encerrada_em,
        )
