from uuid import UUID

from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.entidades.usuario import Usuario
from app.domain.repositorios import RepositorioSessao, RepositorioUsuario


class RepositorioUsuarioMemoria(RepositorioUsuario):
    """
    Implementação em memória de RepositorioUsuario para testes unitários.

    Permite testar casos de uso e serviços da camada de aplicação sem necessidade
    de banco de dados relacional ou ORM, garantindo velocidade e isolamento.
    """

    def __init__(self) -> None:
        self._usuarios: dict[UUID, Usuario] = {}

    def salvar(self, usuario: Usuario) -> None:
        """Persiste um usuário novo ou atualiza um existente em memória."""
        self._usuarios[usuario.id] = usuario

    def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Busca um usuário pelo seu UUID em memória."""
        return self._usuarios.get(id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário pelo seu e-mail (case-insensitive) em memória."""
        email_normalizado = email.strip().lower()
        for usuario in self._usuarios.values():
            if usuario.email == email_normalizado:
                return usuario
        return None

    def existe_com_email(self, email: str) -> bool:
        """Verifica se já existe usuário cadastrado com o e-mail em memória."""
        return self.buscar_por_email(email) is not None

    def limpar(self) -> None:
        """Esvazia o repositório em memória."""
        self._usuarios.clear()

    def __len__(self) -> int:
        return len(self._usuarios)


class RepositorioSessaoMemoria(RepositorioSessao):
    """
    Implementação em memória de RepositorioSessao para testes unitários.

    Permite testar fluxos de sessão (iniciar, concluir, podar, registrar saídas)
    em memória, de forma determinística e sem dependência do PostgreSQL.
    """

    def __init__(self) -> None:
        self._sessoes: dict[UUID, SessaoFoco] = {}

    def salvar(self, sessao: SessaoFoco) -> None:
        """Persiste uma nova sessão ou atualiza uma existente em memória."""
        self._sessoes[sessao.id] = sessao

    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu UUID em memória."""
        return self._sessoes.get(id)

    def listar_por_usuario(self, usuario_id: UUID) -> list[SessaoFoco]:
        """
        Lista todas as sessões de foco de um usuário em ordem decrescente de início.
        """
        sessoes = [s for s in self._sessoes.values() if s.usuario_id == usuario_id]
        return sorted(sessoes, key=lambda s: s.inicio, reverse=True)

    def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
        """
        Retorna a sessão de foco atualmente em andamento do usuário, se houver.
        """
        for sessao in self._sessoes.values():
            if (
                sessao.usuario_id == usuario_id
                and sessao.codigo_estado == "em_andamento"
            ):
                return sessao
        return None

    def limpar(self) -> None:
        """Esvazia o repositório em memória."""
        self._sessoes.clear()

    def __len__(self) -> int:
        return len(self._sessoes)


# Aliases de conveniência
RepositorioUsuarioEmMemoria = RepositorioUsuarioMemoria
RepositorioSessaoEmMemoria = RepositorioSessaoMemoria
