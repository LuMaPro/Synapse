from uuid import UUID

from django.db import transaction

from app.domain.carteira import Carteira
from app.domain.repositorios import RepositorioCarteira
from app.infra.modelos.carteira import CarteiraModel, TipoDesbloqueadoModel


class RepositorioCarteiraDjango(RepositorioCarteira):
    """Implementação de RepositorioCarteira com o ORM do Django (#34)."""

    def carregar(self, usuario_id: UUID, *, para_alterar: bool = False) -> Carteira:
        if para_alterar:
            # Cria a linha se for a primeira vez, para haver o que reservar
            # (SELECT ... FOR UPDATE) até o fim da transação.
            CarteiraModel.objects.get_or_create(usuario_id=usuario_id)
            modelo = CarteiraModel.objects.select_for_update().get(
                usuario_id=usuario_id
            )
        else:
            modelo = CarteiraModel.objects.filter(usuario_id=usuario_id).first()
        desbloqueados = {
            t.codigo: t.desbloqueado_em
            for t in TipoDesbloqueadoModel.objects.filter(usuario_id=usuario_id)
        }
        if modelo is None:
            return Carteira(usuario_id, desbloqueados=desbloqueados)
        return Carteira(usuario_id, modelo.saldo, desbloqueados, modelo.em_uso)

    def salvar(self, carteira: Carteira) -> None:
        with transaction.atomic():
            # Quase sempre a linha já existe (foi reservada ao carregar): um UPDATE
            # direto, sem o SELECT extra do update_or_create.
            dados = {"saldo": carteira.saldo, "em_uso": carteira.em_uso}
            if not CarteiraModel.objects.filter(usuario_id=carteira.usuario_id).update(
                **dados
            ):
                CarteiraModel.objects.create(usuario_id=carteira.usuario_id, **dados)
            # Um tipo comprado não é devolvido: só há inserções.
            gravados = set(
                TipoDesbloqueadoModel.objects.filter(
                    usuario_id=carteira.usuario_id
                ).values_list("codigo", flat=True)
            )
            TipoDesbloqueadoModel.objects.bulk_create(
                TipoDesbloqueadoModel(
                    usuario_id=carteira.usuario_id,
                    codigo=codigo,
                    desbloqueado_em=quando,
                )
                for codigo, quando in carteira.desbloqueados.items()
                if codigo not in gravados
            )
