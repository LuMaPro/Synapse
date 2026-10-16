from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.entidades.usuario import Usuario


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
    def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
        """
        Retorna a sessão de foco atualmente em andamento para o usuário, se houver.
        Garante a regra de que um usuário não pode ter mais de uma sessão ativa por vez.
        """
        ...
