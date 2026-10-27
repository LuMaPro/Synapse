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


class AvaliadorConquistas(ObservadorSessao):
    """Ao fim de cada sessão concluída, desbloqueia as conquistas que o estudante
    acabou de cumprir (#32), com a data da conclusão. As regras ficam no
    `ConquistaService`.

    Precisa ser inscrito depois do `AtualizadorRede`: as conquistas olham a rede, e
    o neurônio e as sinapses da sessão já têm de estar nela (ex.: "100 sinapses").
    """

    def __init__(self, conquistas):
        self.conquistas = conquistas

    def processar(self, evento):
        if isinstance(evento, SessaoConcluida):
            self.conquistas.avaliar(evento.usuario_id, evento.conclusao)


class CreditadorATP(ObservadorSessao):
    """Credita o ATP de cada sessão concluída na carteira do estudante (#34). Sessão
    podada não rende ATP. A quantia vem de `atp_da_sessao`, no `LojaService`."""

    def __init__(self, loja):
        self.loja = loja

    def processar(self, evento):
        if isinstance(evento, SessaoConcluida):
            self.loja.creditar_sessao(evento.usuario_id, evento.duracao_minutos)
