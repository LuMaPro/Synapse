from uuid import UUID

from app.domain.entidades.neuronio import Neuronio
from app.domain.repositorios import RepositorioNeuronio
from app.infra.modelos.neuronio import NeuronioModel


class RepositorioNeuronioDjango(RepositorioNeuronio):
    """Implementação de RepositorioNeuronio com o ORM do Django."""

    def salvar(self, neuronio: Neuronio) -> None:
        NeuronioModel.objects.update_or_create(
            id=neuronio.id,
            defaults={
                "usuario_id": neuronio.usuario_id,
                "sessao_id": neuronio.sessao_id,
                "duracao_minutos": neuronio.duracao.minutos,
                "vivo": neuronio.vivo,
                "materia_id": neuronio.materia_id,
                "criado_em": neuronio.criado_em,
            },
        )

    def buscar_por_sessao(self, sessao_id: UUID) -> Neuronio | None:
        model = NeuronioModel.objects.filter(sessao_id=sessao_id).first()
        return model.para_entidade() if model else None

    def listar_por_usuario(self, usuario_id: UUID) -> list[Neuronio]:
        qs = NeuronioModel.objects.filter(usuario_id=usuario_id)
        return [n.para_entidade() for n in qs]
