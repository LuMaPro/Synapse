from uuid import UUID

from django.db import transaction

from app.domain.carteira import Carteira
from app.domain.repositorios import RepositorioCarteira
from app.infra.modelos.carteira import CarteiraModel, CorDesbloqueadaModel


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
        desbloqueadas = {
            c.codigo: c.desbloqueada_em
            for c in CorDesbloqueadaModel.objects.filter(usuario_id=usuario_id)
        }
        saldo = modelo.saldo if modelo else 0
        return Carteira(usuario_id, saldo, desbloqueadas)

    def salvar(self, carteira: Carteira) -> None:
        with transaction.atomic():
            # Quase sempre a linha já existe (foi reservada ao carregar): um UPDATE
            # direto, sem o SELECT extra do update_or_create.
            if not CarteiraModel.objects.filter(usuario_id=carteira.usuario_id).update(
                saldo=carteira.saldo
            ):
                CarteiraModel.objects.create(
                    usuario_id=carteira.usuario_id, saldo=carteira.saldo
                )
            # Uma cor comprada não é devolvida: só há inserções.
            gravadas = set(
                CorDesbloqueadaModel.objects.filter(
                    usuario_id=carteira.usuario_id
                ).values_list("codigo", flat=True)
            )
            CorDesbloqueadaModel.objects.bulk_create(
                CorDesbloqueadaModel(
                    usuario_id=carteira.usuario_id,
                    codigo=codigo,
                    desbloqueada_em=quando,
                )
                for codigo, quando in carteira.desbloqueadas.items()
                if codigo not in gravadas
            )
