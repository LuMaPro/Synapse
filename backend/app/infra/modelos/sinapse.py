import uuid

from django.conf import settings
from django.db import models

from app.domain.entidades.sinapse import Sinapse
from app.infra.modelos.neuronio import NeuronioModel


class SinapseModel(models.Model):
    """Persistência da sinapse entre dois neurônios do estudante (#23).

    As regras (quem se liga a quem, o peso) ficam no domínio, em `RedeNeural`. As
    restrições do banco repetem as invariantes como última barreira: sem ligação
    repetida e sem neurônio ligado a ele mesmo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Repete o dono dos neurônios para carregar a rede numa consulta só.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sinapses",
        verbose_name="usuário",
    )
    origem = models.ForeignKey(
        NeuronioModel,
        on_delete=models.CASCADE,
        related_name="sinapses_de_saida",
        verbose_name="neurônio de origem",
    )
    destino = models.ForeignKey(
        NeuronioModel,
        on_delete=models.CASCADE,
        related_name="sinapses_de_entrada",
        verbose_name="neurônio de destino",
    )
    peso = models.PositiveSmallIntegerField()
    criada_em = models.DateTimeField("criada em")

    class Meta:
        db_table = "sinapses"
        verbose_name = "sinapse"
        verbose_name_plural = "sinapses"
        ordering = ["criada_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["origem", "destino"], name="sinapse_sem_repeticao"
            ),
            models.CheckConstraint(
                condition=~models.Q(origem=models.F("destino")),
                name="sinapse_sem_autoconexao",
            ),
            models.CheckConstraint(
                condition=models.Q(peso__gte=1), name="sinapse_peso_positivo"
            ),
        ]

    def __str__(self) -> str:
        return f"Sinapse {self.origem_id} → {self.destino_id} (peso {self.peso})"

    def para_entidade(self) -> Sinapse:
        return Sinapse(
            self.origem_id,
            self.destino_id,
            self.peso,
            criada_em=self.criada_em,
            id=self.id,
        )
