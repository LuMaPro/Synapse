from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.carteira import Carteira
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.entidades.materia import Materia
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.entidades.usuario import Usuario
from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.rede_neural import RedeNeural


class RepositorioUsuario(ABC):
    """
    Interface abstrata para persistência de Usuários (Padrão Repository).

    O domínio declara as operações de que necessita sem se acoplar a bancos
    de dados relacionais, ORMs ou frameworks externos (como o Django ORM).
    A implementação concreta reside na camada de infraestrutura.
    """

    @abstractmethod
    def salvar(self, usuario: Usuario) -> None:
        """Persiste um usuário novo ou atualiza um existente."""
        ...

    @abstractmethod
    def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Busca um usuário pelo seu identificador único (UUID)."""
        ...

    @abstractmethod
    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário pelo seu endereço de e-mail (case-insensitive)."""
        ...

    @abstractmethod
    def existe_com_email(self, email: str) -> bool:
        """Verifica se já existe algum usuário cadastrado com o e-mail informado."""
        ...


class RepositorioSessao(ABC):
    """
    Interface abstrata para persistência de Sessões de Foco (Padrão Repository).

    Permite consultar e salvar o ciclo de vida e estado das sessões de foco
    mantendo as regras e transições de estado puras no domínio.
    """

    @abstractmethod
    def salvar(self, sessao: SessaoFoco) -> None:
        """Persiste uma nova sessão ou atualiza o estado de uma sessão existente."""
        ...

    @abstractmethod
    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu identificador único (UUID)."""
        ...

    @abstractmethod
    def listar_por_usuario(self, usuario_id: UUID) -> list[SessaoFoco]:
        """Lista todas as sessões de foco pertencentes a um determinado usuário."""
        ...

    @abstractmethod
    def listar_por_periodo(
        self,
        usuario_id: UUID,
        *,
        de: datetime,
        ate: datetime,
    ) -> list[SessaoFoco]:
        """Lista as sessões iniciadas entre `de` e `ate` (inclusive), sem paginar
        (#30)."""
        ...

    @abstractmethod
    def listar_historico(
        self,
        usuario_id: UUID,
        *,
        de: datetime | None = None,
        ate: datetime | None = None,
        estado: str | None = None,
        deslocamento: int = 0,
        limite: int = 20,
    ) -> tuple[list[SessaoFoco], int]:
        """Uma página do histórico do estudante (#29): as sessões iniciadas entre
        `de` e `ate` (inclusive), no estado pedido, da mais recente para a mais
        antiga, pulando as `deslocamento` primeiras. Devolve a página e o total."""
        ...

    @abstractmethod
    def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
        """
        Retorna a sessão de foco atualmente em andamento para o usuário, se houver.
        Garante a regra de que um usuário não pode ter mais de uma sessão ativa por vez.
        """
        ...

    @abstractmethod
    def listar_em_andamento(self) -> list[SessaoFoco]:
        """Lista as sessões em andamento de todos os usuários.

        Usado pela varredura de sessões abandonadas (comando podar_sessoes_orfas).
        """
        ...

    @abstractmethod
    def remover(self, id: UUID) -> None:
        """Apaga a sessão e as saídas dela; não faz nada se ela não existir.

        Usado para a sessão podada antes de 5 min, que não fica registrada.
        """
        ...


class RepositorioNeuronio(ABC):
    """Interface abstrata para persistência dos neurônios (Padrão Repository)."""

    @abstractmethod
    def salvar(self, neuronio: Neuronio) -> None:
        """Persiste um neurônio novo."""
        ...

    @abstractmethod
    def buscar_por_sessao(self, sessao_id: UUID) -> Neuronio | None:
        """Busca o neurônio criado ao concluir a sessão, se houver."""
        ...

    @abstractmethod
    def listar_por_usuario(self, usuario_id: UUID) -> list[Neuronio]:
        """Lista os neurônios de um usuário, do mais recente para o mais antigo."""
        ...


class RepositorioRedeNeural(ABC):
    """Persistência do agregado RedeNeural (Padrão Repository, #23).

    Os neurônios e as sinapses de um estudante são carregados e gravados juntos,
    sempre passando pelo agregado, que é quem garante as regras da rede.
    """

    @abstractmethod
    def carregar(
        self, usuario_id: UUID, regra: RegraFormacaoSinapses | None = None
    ) -> RedeNeural:
        """Monta a rede do estudante com a regra de formação informada (ou a
        padrão)."""
        ...

    @abstractmethod
    def salvar(self, rede: RedeNeural) -> None:
        """Grava os neurônios e as sinapses adicionados desde o carregamento.

        Eles não mudam depois de criados, então só há inserções.
        """
        ...


class RepositorioMateria(ABC):
    """Interface abstrata para persistência das matérias (Padrão Repository, #27)."""

    @abstractmethod
    def salvar(self, materia: Materia) -> None:
        """Persiste uma nova matéria ou atualiza uma existente."""
        ...

    @abstractmethod
    def buscar_por_id(self, id: UUID) -> Materia | None:
        """Busca uma matéria pelo seu identificador único (UUID)."""
        ...

    @abstractmethod
    def buscar_por_usuario_e_id(self, usuario_id: UUID, id: UUID) -> Materia | None:
        """Busca uma matéria pertencente ao estudante informado."""
        ...

    @abstractmethod
    def listar_por_usuario(self, usuario_id: UUID) -> list[Materia]:
        """Lista todas as matérias pertencentes a um estudante, ordenadas por nome."""
        ...

    @abstractmethod
    def existe_com_nome(
        self, usuario_id: UUID, nome: str, ignorar_id: UUID | None = None
    ) -> bool:
        """Verifica se o estudante já possui matéria com este nome."""
        ...

    @abstractmethod
    def remover(self, id: UUID) -> None:
        """Remove a matéria do repositório."""
        ...


class RepositorioConquista(ABC):
    """Persistência das conquistas desbloqueadas (Padrão Repository, #32)."""

    @abstractmethod
    def listar_por_usuario(self, usuario_id: UUID) -> list[ConquistaDesbloqueada]:
        """Lista as conquistas que o estudante já desbloqueou."""
        ...

    @abstractmethod
    def salvar(self, conquista: ConquistaDesbloqueada) -> None:
        """Persiste uma conquista recém-desbloqueada."""
        ...


class RepositorioCarteira(ABC):
    """Persistência do agregado Carteira (Padrão Repository, #34)."""

    @abstractmethod
    def carregar(self, usuario_id: UUID, *, para_alterar: bool = False) -> Carteira:
        """A carteira do estudante; vazia (saldo 0) se ele nunca ganhou ATP.

        Com `para_alterar`, a carteira fica reservada até o fim da transação, para
        que duas compras ao mesmo tempo não gastem o mesmo ATP.
        """
        ...

    @abstractmethod
    def salvar(self, carteira: Carteira) -> None:
        """Grava o saldo, os tipos desbloqueados e os escolhidos."""
        ...
