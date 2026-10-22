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
        qs = SessaoFocoModel.objects.filter(usuario_id=usuario_id).order_by("-inicio")
        return [s.para_entidade() for s in qs]

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


# Alias de conveniência
RepositorioSessaoFocoDjango = RepositorioSessaoDjango
