from app.domain.eventos import ObservadorSessao, SessaoConcluida, SessaoPodada


class AtualizadorRede(ObservadorSessao):
    """Coloca na rede do estudante o neurônio da sessão que terminou (#23 e #24): vivo
    se ela foi concluída, morto e sem sinapses se foi podada. As sinapses são formadas
    pela rede (`RedeNeuralService.registrar`)."""

    def __init__(self, rede_neuronio):
        self.rede = rede_neuronio

    def processar(self, evento):
        if isinstance(evento, SessaoConcluida | SessaoPodada) and evento.neuronio:
            self.rede.registrar(evento.neuronio)
