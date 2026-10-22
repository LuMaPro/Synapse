import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from app.domain.entidades.materia import Materia


class MateriaModel(models.Model):
    """Persistência da matéria (etiqueta) pertencente ao estudante (#27)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="materias",
        verbose_name="usuário",
    )
    nome = models.CharField("nome", max_length=100)
    cor = models.CharField("cor", max_length=7)
    criada_em = models.DateTimeField("criada em", default=timezone.now)

    class Meta:
        db_table = "materias"
        verbose_name = "matéria"
        verbose_name_plural = "matérias"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                "usuario",
                name="materia_nome_unico_por_usuario",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.cor})"

    def para_entidade(self) -> Materia:
        return Materia(
            usuario_id=self.usuario_id,
            nome=self.nome,
            cor=self.cor,
            criada_em=self.criada_em,
            id=self.id,
        )

    @classmethod
    def de_entidade(cls, materia: Materia) -> "MateriaModel":
        return cls(
            id=materia.id,
            usuario_id=materia.usuario_id,
            nome=materia.nome,
            cor=materia.cor,
            criada_em=materia.criada_em,
        )
