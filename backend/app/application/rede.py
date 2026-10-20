from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sinapse import Sinapse
from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.repositorios import RepositorioRedeNeural


class RedeNeuralService:
    """Casos de uso da rede neural (issue #23).

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
