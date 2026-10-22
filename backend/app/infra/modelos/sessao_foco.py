import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from app.domain.entidades.sessao_foco import (
    Concluida,
    EmAndamento,
    EstadoSessao,
    Podada,
    SessaoFoco,
)
from app.domain.politica_interrupcao import Interrupcao, politica_por_codigo


class SessaoFocoModel(models.Model):
    """
    Persistência da sessão de foco.

    As regras de negócio, ciclo de vida e transições de estado
    residem na entidade de domínio puro `SessaoFoco`.
    """

    class Estado(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        PODADA = "podada", "Podada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessoes_foco",
        verbose_name="usuário",
    )
    duracao_minutos = models.PositiveIntegerField("duração (minutos)")
    inicio = models.DateTimeField("início", default=timezone.now)
    encerrada_em = models.DateTimeField("encerrada em", null=True, blank=True)
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.EM_ANDAMENTO,
    )

    class Modo(models.TextChoices):
        ESTRITO = "estrito", "Estrito"
        TOLERANTE = "tolerante", "Tolerante"

    modo = models.CharField(
        "modo", max_length=20, choices=Modo.choices, default=Modo.ESTRITO
    )
    materia = models.ForeignKey(
        "app.MateriaModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_foco",
        verbose_name="matéria",
    )

    class Meta:
        db_table = "sessoes_foco"
        verbose_name = "sessão de foco"
        verbose_name_plural = "sessões de foco"
        ordering = ["-inicio"]

    def __str__(self) -> str:
        estado = self.get_estado_display()
        return f"Sessão {self.id} ({estado}) - {self.duracao_minutos} min"

    def para_entidade(self) -> SessaoFoco:
        """Converte o model do Django para a entidade de domínio puro SessaoFoco."""
        mapa_estados: dict[str, type[EstadoSessao]] = {
            self.Estado.EM_ANDAMENTO: EmAndamento,
            self.Estado.CONCLUIDA: Concluida,
            self.Estado.PODADA: Podada,
        }
        estado_cls = mapa_estados.get(self.estado, EmAndamento)
        return SessaoFoco(
            usuario_id=self.usuario_id,
            duracao_minutos=self.duracao_minutos,
            inicio=self.inicio,
            encerrada_em=self.encerrada_em,
            estado=estado_cls(),
            id=self.id,
            politica=politica_por_codigo(self.modo),
            interrupcoes=[
                Interrupcao(saida=i.saida, retorno=i.retorno)
                for i in self.interrupcoes.all()
            ],
            materia_id=self.materia_id,
        )

    @classmethod
    def de_entidade(cls, sessao: SessaoFoco) -> "SessaoFocoModel":
        """
        Cria uma instância do model a partir da entidade de domínio puro SessaoFoco.
        """
        return cls(
            id=sessao.id,
            usuario_id=sessao.usuario_id,
            duracao_minutos=sessao.duracao.minutos,
            inicio=sessao.inicio,
            encerrada_em=sessao.encerrada_em,
            estado=sessao.codigo_estado,
            modo=sessao.politica.codigo,
            materia_id=sessao.materia_id,
        )


class InterrupcaoModel(models.Model):
    """Saída da tela registrada numa sessão (histórico usado pelo modo tolerante)."""

    sessao = models.ForeignKey(
        SessaoFocoModel,
        on_delete=models.CASCADE,
        related_name="interrupcoes",
        verbose_name="sessão",
    )
    saida = models.DateTimeField("saída")
    retorno = models.DateTimeField("retorno", null=True, blank=True)

    class Meta:
        db_table = "interrupcoes"
        verbose_name = "interrupção"
        verbose_name_plural = "interrupções"
        ordering = ["saida"]

    def __str__(self) -> str:
        return f"Interrupção da sessão {self.sessao_id} às {self.saida:%H:%M:%S}"


# Alias de conveniência caso seja referenciado como SessaoModel
SessaoModel = SessaoFocoModel
