from uuid import UUID

from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.repositorios import RepositorioConquista
from app.infra.modelos.conquista import ConquistaModel


class RepositorioConquistaDjango(RepositorioConquista):
    """Implementação de RepositorioConquista com o ORM do Django (#32)."""

    def listar_por_usuario(self, usuario_id: UUID) -> list[ConquistaDesbloqueada]:
        modelos = ConquistaModel.objects.filter(usuario_id=usuario_id)
        return [m.para_entidade() for m in modelos]

    def salvar(self, conquista: ConquistaDesbloqueada) -> None:
        ConquistaModel.objects.update_or_create(
            id=conquista.id,
            defaults={
                "usuario_id": conquista.usuario_id,
                "codigo": conquista.codigo,
                "desbloqueada_em": conquista.desbloqueada_em,
            },
        )
