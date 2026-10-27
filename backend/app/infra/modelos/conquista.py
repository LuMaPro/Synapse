import uuid

from django.conf import settings
from django.db import models

from app.domain.entidades.conquista import ConquistaDesbloqueada


class ConquistaModel(models.Model):
    """Persistência das conquistas desbloqueadas pelo estudante (#32).

    Só o código da regra é guardado; nome, descrição e meta ficam no domínio
    (`app/domain/conquistas.py`). Cada conquista é desbloqueada uma vez por estudante.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conquistas",
        verbose_name="usuário",
    )
    codigo = models.CharField("código", max_length=50)
    desbloqueada_em = models.DateTimeField("desbloqueada em")

    class Meta:
        db_table = "conquistas"
        verbose_name = "conquista"
        verbose_name_plural = "conquistas"
        ordering = ["desbloqueada_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "codigo"], name="conquista_unica_por_usuario"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} ({self.desbloqueada_em:%d/%m/%Y})"

    def para_entidade(self) -> ConquistaDesbloqueada:
        return ConquistaDesbloqueada(
            self.usuario_id, self.codigo, self.desbloqueada_em, id=self.id
        )
