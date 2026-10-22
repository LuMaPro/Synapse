from uuid import UUID

from app.domain.entidades.materia import Materia
from app.domain.excecoes import MateriaJaExiste, MateriaNaoEncontrada
from app.domain.repositorios import RepositorioMateria


class MateriaService:
    """Casos de uso para gerenciamento de matérias do estudante (#27)."""

    def __init__(self, materias: RepositorioMateria):
        self._materias = materias

    def criar(self, usuario_id: UUID, nome: str, cor: str) -> Materia:
        """Cria e persiste uma nova matéria para o estudante."""
        # A própria entidade valida e normaliza o nome e o formato da cor
        materia = Materia(usuario_id, nome, cor)
        if self._materias.existe_com_nome(usuario_id, materia.nome):
            raise MateriaJaExiste(f"Você já tem uma matéria chamada {materia.nome!r}.")
        self._materias.salvar(materia)
        return materia

    def listar(self, usuario_id: UUID) -> list[Materia]:
        """Lista todas as matérias pertencentes ao estudante, ordenadas por nome."""
        return self._materias.listar_por_usuario(usuario_id)

    def buscar(self, usuario_id: UUID, materia_id: UUID) -> Materia:
        """Busca uma matéria pelo id garantindo que pertença ao estudante."""
        materia = self._materias.buscar_por_usuario_e_id(usuario_id, materia_id)
        if materia is None:
            raise MateriaNaoEncontrada("Matéria não encontrada.")
        return materia

    def atualizar(
        self,
        usuario_id: UUID,
        materia_id: UUID,
        *,
        nome: str | None = None,
        cor: str | None = None,
    ) -> Materia:
        """Atualiza nome e/ou cor de uma matéria existente do estudante."""
        materia = self.buscar(usuario_id, materia_id)

        if nome is not None:
            nome_normalizado = nome.strip()
            if self._materias.existe_com_nome(
                usuario_id, nome_normalizado, ignorar_id=materia_id
            ):
                raise MateriaJaExiste(
                    f"Você já tem uma matéria chamada {nome_normalizado!r}."
                )

        materia.atualizar(nome=nome, cor=cor)
        self._materias.salvar(materia)
        return materia

    def remover(self, usuario_id: UUID, materia_id: UUID) -> None:
        """Remove a matéria do estudante."""
        materia = self.buscar(usuario_id, materia_id)
        self._materias.remover(materia.id)
