import uuid

from django.conf import settings
from django.db import models


class CarteiraModel(models.Model):
    """Persistência do saldo de ATP do estudante (#34).

    As regras (saldo que não fica negativo, cor comprada uma vez só) ficam no
    agregado `Carteira`. O saldo positivo aqui é a última barreira.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="carteira",
        verbose_name="usuário",
    )
    saldo = models.PositiveIntegerField("saldo de ATP", default=0)

    class Meta:
        db_table = "carteiras"
        verbose_name = "carteira"
        verbose_name_plural = "carteiras"

    def __str__(self) -> str:
        return f"{self.saldo} ATP"


class CorDesbloqueadaModel(models.Model):
    """Cor comprada na loja pelo estudante (#34)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cores_desbloqueadas",
        verbose_name="usuário",
    )
    codigo = models.CharField("código", max_length=50)
    desbloqueada_em = models.DateTimeField("desbloqueada em")

    class Meta:
        db_table = "cores_desbloqueadas"
        verbose_name = "cor desbloqueada"
        verbose_name_plural = "cores desbloqueadas"
        ordering = ["desbloqueada_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "codigo"], name="cor_desbloqueada_uma_vez"
            ),
        ]

    def __str__(self) -> str:
        return self.codigo
