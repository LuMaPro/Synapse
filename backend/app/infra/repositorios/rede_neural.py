from uuid import UUID

from django.db import transaction

from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.rede_neural import RedeNeural
from app.domain.repositorios import RepositorioRedeNeural
from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sinapse import SinapseModel


class RepositorioRedeNeuralDjango(RepositorioRedeNeural):
    """Implementação de RepositorioRedeNeural com o ORM do Django.

    Carrega a rede em duas consultas (neurônios e sinapses do estudante) e grava só
    as novidades, em lote.
    """

    def carregar(
        self, usuario_id: UUID, regra: RegraFormacaoSinapses | None = None
    ) -> RedeNeural:
        neuronios = NeuronioModel.objects.filter(usuario_id=usuario_id).order_by(
            "criado_em"
        )
        sinapses = SinapseModel.objects.filter(usuario_id=usuario_id)
        return RedeNeural(
            usuario_id,
            [n.para_entidade() for n in neuronios],
            [s.para_entidade() for s in sinapses],
            regra=regra,
        )

    def salvar(self, rede: RedeNeural) -> None:
        with transaction.atomic():
            NeuronioModel.objects.bulk_create(
                NeuronioModel(
                    id=n.id,
                    usuario_id=n.usuario_id,
                    sessao_id=n.sessao_id,
                    duracao_minutos=n.duracao.minutos,
                    vivo=n.vivo,
                    materia_id=n.materia_id,
                    criado_em=n.criado_em,
                    tipo=n.tipo.codigo,
                )
                for n in rede.neuronios_novos
            )
            SinapseModel.objects.bulk_create(
                SinapseModel(
                    id=s.id,
                    usuario_id=rede.usuario_id,
                    origem_id=s.origem_id,
                    destino_id=s.destino_id,
                    peso=s.peso,
                    criada_em=s.criada_em,
                )
                for s in rede.sinapses_novas
            )
        rede.marcar_como_salva()
