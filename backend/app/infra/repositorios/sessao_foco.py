from datetime import datetime
from uuid import UUID

from django.db import transaction

from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.repositorios import RepositorioSessao
from app.infra.modelos.sessao_foco import InterrupcaoModel, SessaoFocoModel


class RepositorioSessaoDjango(RepositorioSessao):
    """
    Implementação concreta de RepositorioSessao utilizando o ORM do Django.

    Responsável por converter SessaoFocoModel (infraestrutura/ORM) ↔
    SessaoFoco (entidade pura de domínio).
    """

    def salvar(self, sessao: SessaoFoco) -> None:
        """Persiste uma nova sessão ou atualiza o estado de uma sessão existente,
        junto com o histórico de interrupções."""
        with transaction.atomic():
            sessao_model, _ = SessaoFocoModel.objects.update_or_create(
                id=sessao.id,
                defaults={
                    "usuario_id": sessao.usuario_id,
                    "duracao_minutos": sessao.duracao.minutos,
                    "inicio": sessao.inicio,
                    "encerrada_em": sessao.encerrada_em,
                    "estado": sessao.codigo_estado,
                    "modo": sessao.politica.codigo,
                    "materia_id": sessao.materia_id,
                },
            )
            # O histórico é da entidade: o banco espelha a lista atual.
            sessao_model.interrupcoes.all().delete()
            InterrupcaoModel.objects.bulk_create(
                InterrupcaoModel(sessao=sessao_model, saida=i.saida, retorno=i.retorno)
                for i in sessao.historico_interrupcoes
            )

    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu identificador único (UUID)."""
        sessao_model = SessaoFocoModel.objects.filter(id=id).first()
        if not sessao_model:
            return None
        return sessao_model.para_entidade()

    def listar_por_usuario(self, usuario_id: UUID) -> list[SessaoFoco]:
        """Lista todas as sessões de foco pertencentes a um determinado usuário."""
        qs = (
            SessaoFocoModel.objects.filter(usuario_id=usuario_id)
            .order_by("-inicio")
            .prefetch_related("interrupcoes")
        )
        return [s.para_entidade() for s in qs]

    def listar_por_periodo(
        self,
        usuario_id: UUID,
        *,
        de: datetime,
        ate: datetime,
    ) -> list[SessaoFoco]:
        """Lista as sessões iniciadas entre `de` e `ate` (inclusive) numa consulta."""
        qs = (
            SessaoFocoModel.objects.filter(
                usuario_id=usuario_id,
                inicio__gte=de,
                inicio__lte=ate,
            )
            .order_by("inicio")
            .prefetch_related("interrupcoes")
        )
        return [s.para_entidade() for s in qs]

    def listar_historico(
        self,
        usuario_id: UUID,
        *,
        de: datetime | None = None,
        ate: datetime | None = None,
        estado: str | None = None,
        deslocamento: int = 0,
        limite: int = 20,
    ) -> tuple[list[SessaoFoco], int]:
        """Filtra, conta e pagina no banco; as interrupções vêm numa consulta só."""
        qs = SessaoFocoModel.objects.filter(usuario_id=usuario_id)
        if de is not None:
            qs = qs.filter(inicio__gte=de)
        if ate is not None:
            qs = qs.filter(inicio__lte=ate)
        if estado is not None:
            qs = qs.filter(estado=estado)
        total = qs.count()
        pagina = qs.order_by("-inicio").prefetch_related("interrupcoes")[
            deslocamento : deslocamento + limite
        ]
        return [s.para_entidade() for s in pagina], total

    def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
        """
        Retorna a sessão de foco atualmente em andamento para o usuário, se houver.
        """
        sessao_model = SessaoFocoModel.objects.filter(
            usuario_id=usuario_id,
            estado=SessaoFocoModel.Estado.EM_ANDAMENTO,
        ).first()
        if not sessao_model:
            return None
        return sessao_model.para_entidade()

    def listar_em_andamento(self) -> list[SessaoFoco]:
        """Lista as sessões em andamento de todos os usuários."""
        qs = SessaoFocoModel.objects.filter(estado=SessaoFocoModel.Estado.EM_ANDAMENTO)
        return [s.para_entidade() for s in qs]

    def remover(self, id: UUID) -> None:
        """Apaga a sessão; as interrupções vão junto (CASCADE)."""
        SessaoFocoModel.objects.filter(id=id).delete()


# Alias de conveniência
RepositorioSessaoFocoDjango = RepositorioSessaoDjango
