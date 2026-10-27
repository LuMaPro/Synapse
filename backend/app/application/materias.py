from uuid import UUID

from app.application.loja import LojaService
from app.domain.entidades.materia import Materia
from app.domain.excecoes import MateriaJaExiste, MateriaNaoEncontrada
from app.domain.repositorios import RepositorioMateria


class MateriaService:
    """Casos de uso para gerenciamento de matérias do estudante (#27).

    Com a `loja` (#34), a cor precisa ser uma da paleta: uma gratuita ou uma que o
    estudante comprou. Sem ela, vale qualquer hexadecimal.
    """

    def __init__(self, materias: RepositorioMateria, loja: LojaService | None = None):
        self._materias = materias
        self._loja = loja

    def criar(self, usuario_id: UUID, nome: str, cor: str) -> Materia:
        """Cria e persiste uma nova matéria para o estudante."""
        # A própria entidade valida e normaliza o nome e o formato da cor
        materia = Materia(usuario_id, nome, cor)
        self._exigir_cor_disponivel(usuario_id, materia.cor)
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

        if cor is not None:
            # A entidade valida e normaliza a cor nova antes de a matéria mudar. Uma
            # cor antiga, de fora da paleta, continua valendo enquanto não mudar.
            nova_cor = Materia(usuario_id, materia.nome, cor).cor
            if nova_cor != materia.cor:
                self._exigir_cor_disponivel(usuario_id, nova_cor)

        materia.atualizar(nome=nome, cor=cor)
        self._materias.salvar(materia)
        return materia

    def _exigir_cor_disponivel(self, usuario_id: UUID, cor: str) -> None:
        if self._loja is not None:
            self._loja.exigir_cor_disponivel(usuario_id, cor)

    def remover(self, usuario_id: UUID, materia_id: UUID) -> None:
        """Remove a matéria do estudante."""
        materia = self.buscar(usuario_id, materia_id)
        self._materias.remover(materia.id)
