from datetime import datetime
from uuid import UUID

from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sinapse import Sinapse
from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.rede_neural import RecorteRede
from app.domain.repositorios import RepositorioRedeNeural


class RedeNeuralService:
    """Casos de uso da rede neural (issues #23 e #25).

    A regra de formação das sinapses é escolhida aqui, na montagem do serviço. Quem
    registra neurônios (o `SessaoService`) não sabe qual regra está valendo, então
    ela pode ser trocada sem mexer nele.
    """

    def __init__(
        self,
        redes: RepositorioRedeNeural,
        regra: RegraFormacaoSinapses | None = None,
    ):
        self._redes = redes
        self._regra = regra

    def registrar(self, neuronio: Neuronio) -> list[Sinapse]:
        """Coloca o neurônio na rede do estudante e devolve as sinapses formadas."""
        rede = self._redes.carregar(neuronio.usuario_id, self._regra)
        sinapses = rede.adicionar(neuronio)
        self._redes.salvar(rede)
        return sinapses

    def consultar(
        self,
        usuario_id: UUID,
        *,
        de: datetime | None = None,
        ate: datetime | None = None,
        materia_id: UUID | None = None,
    ) -> RecorteRede:
        """A rede do estudante para mostrar, com os filtros de período e matéria."""
        rede = self._redes.carregar(usuario_id, self._regra)
        return rede.recortar(de=de, ate=ate, materia_id=materia_id)
