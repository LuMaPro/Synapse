import uuid

from django.conf import settings
from django.db import models

from app.domain.entidades.neuronio import Neuronio
from app.infra.modelos.sessao_foco import SessaoFocoModel


class NeuronioModel(models.Model):
    """Persistência do neurônio criado quando uma sessão termina (#16 e #23)."""

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
    # Neurônio morto vem de sessão podada: fica cinza e sem sinapses (#23).
    vivo = models.BooleanField(default=True)
    # Vira chave estrangeira para as matérias na #27.
    materia_id = models.UUIDField("matéria", null=True, blank=True)
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
            vivo=self.vivo,
            materia_id=self.materia_id,
            criado_em=self.criado_em,
            id=self.id,
        )
