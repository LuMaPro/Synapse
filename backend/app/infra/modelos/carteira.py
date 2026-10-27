import uuid

from django.conf import settings
from django.db import models


class CarteiraModel(models.Model):
    """Persistência do saldo de ATP e dos tipos escolhidos na loja (#34).

    As regras (saldo que não fica negativo, só usar o que é seu) ficam no agregado
    `Carteira`. O saldo positivo aqui é a última barreira.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="carteira",
        verbose_name="usuário",
    )
    saldo = models.PositiveIntegerField("saldo de ATP", default=0)
    # Forma do neurônio -> código da variação escolhida (ex.: {"piramidal":
    # "piramidal_rosa"}). Forma ausente usa o tipo original.
    em_uso = models.JSONField("tipos em uso", default=dict, blank=True)

    class Meta:
        db_table = "carteiras"
        verbose_name = "carteira"
        verbose_name_plural = "carteiras"

    def __str__(self) -> str:
        return f"{self.saldo} ATP"


class TipoDesbloqueadoModel(models.Model):
    """Tipo de neurônio comprado na loja pelo estudante (#34)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tipos_desbloqueados",
        verbose_name="usuário",
    )
    codigo = models.CharField("código", max_length=50)
    desbloqueado_em = models.DateTimeField("desbloqueado em")

    class Meta:
        db_table = "tipos_desbloqueados"
        verbose_name = "tipo desbloqueado"
        verbose_name_plural = "tipos desbloqueados"
        ordering = ["desbloqueado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "codigo"], name="tipo_desbloqueado_uma_vez"
            ),
        ]

    def __str__(self) -> str:
        return self.codigo
