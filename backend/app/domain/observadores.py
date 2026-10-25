from app.domain.entidades.neuronio import Neuronio
from app.application.rede import RedeNeuralService
from app.domain.eventos import ObservadorSessao, SessaoConcluida, SessaoPodada

class AtualizadorRede(ObservadorSessao):

    def __init__(self, rede_neuronio):
        self.rede = rede_neuronio

    def processar(self, evento):
        if(isinstance(evento, SessaoConcluida)):

            # Instancia novo neurônio e adiciona a rede neural
            neuronio = Neuronio(
                usuario_id=evento.usuario_id,
                sessao_id=evento.sessao_id,
                duracao_minutos=evento.duracao_minutos,
                materia_id=evento.materia_id,
                criado_em=evento.conclusao
            )

            self.rede.registrar(neuronio)

        elif isinstance(evento, SessaoPodada):
            neuronio = Neuronio(
                evento.usuario_id,
                evento.sessao_id,
                evento.duracao_minutos,
                vivo=False,
                materia_id=evento.materia_id,
                criado_em=evento.podada_em
            )
            self.rede.registrar(neuronio)