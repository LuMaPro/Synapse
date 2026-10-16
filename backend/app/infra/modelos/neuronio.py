import uuid

from django.conf import settings
from django.db import models

from app.domain.entidades.neuronio import Neuronio
from app.infra.modelos.sessao_foco import SessaoFocoModel


class NeuronioModel(models.Model):
    """Persistência do neurônio criado ao concluir uma sessão (#16)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="neuronios",
        verbose_name="usuário",
    )
    # Uma sessão concluída gera exatamente um neurônio.
    sessao = models.OneToOneField(
        SessaoFocoModel,
        on_delete=models.CASCADE,
        related_name="neuronio",
        verbose_name="sessão",
    )
    duracao_minutos = models.PositiveIntegerField("duração (minutos)")
    criado_em = models.DateTimeField("criado em")

    class Meta:
        db_table = "neuronios"
        verbose_name = "neurônio"
        verbose_name_plural = "neurônios"
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"Neurônio {self.id} ({self.duracao_minutos} min)"

    def para_entidade(self) -> Neuronio:
        return Neuronio(
            self.usuario_id,
            self.sessao_id,
            self.duracao_minutos,
            criado_em=self.criado_em,
            id=self.id,
        )
