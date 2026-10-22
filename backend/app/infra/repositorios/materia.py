from uuid import UUID

from app.domain.entidades.materia import Materia
from app.domain.repositorios import RepositorioMateria
from app.infra.modelos.materia import MateriaModel


class RepositorioMateriaDjango(RepositorioMateria):
    """Implementação concreta de RepositorioMateria utilizando o ORM do Django (#27)."""

    def salvar(self, materia: Materia) -> None:
        MateriaModel.objects.update_or_create(
            id=materia.id,
            defaults={
                "usuario_id": materia.usuario_id,
                "nome": materia.nome,
                "cor": materia.cor,
                "criada_em": materia.criada_em,
            },
        )

    def buscar_por_id(self, id: UUID) -> Materia | None:
        modelo = MateriaModel.objects.filter(id=id).first()
        if not modelo:
            return None
        return modelo.para_entidade()

    def buscar_por_usuario_e_id(self, usuario_id: UUID, id: UUID) -> Materia | None:
        modelo = MateriaModel.objects.filter(id=id, usuario_id=usuario_id).first()
        if not modelo:
            return None
        return modelo.para_entidade()

    def listar_por_usuario(self, usuario_id: UUID) -> list[Materia]:
        modelos = MateriaModel.objects.filter(usuario_id=usuario_id).order_by("nome")
        return [m.para_entidade() for m in modelos]

    def existe_com_nome(
        self, usuario_id: UUID, nome: str, ignorar_id: UUID | None = None
    ) -> bool:
        qs = MateriaModel.objects.filter(
            usuario_id=usuario_id, nome__iexact=nome.strip()
        )
        if ignorar_id is not None:
            qs = qs.exclude(id=ignorar_id)
        return qs.exists()

    def remover(self, id: UUID) -> None:
        MateriaModel.objects.filter(id=id).delete()
