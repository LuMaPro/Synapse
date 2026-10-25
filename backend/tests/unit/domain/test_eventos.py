from datetime import datetime
from uuid import uuid4

from app.domain.eventos import (
    ObservadorSessao,
    PublicadorEventos,
    SessaoConcluida,
    SessaoPodada,
)

class ObservadorEspiao(ObservadorSessao):
    """Observador falso usado apenas para registar chamadas nos testes."""
    def __init__(self):
        self.eventos_recebidos = []

    def processar(self, evento) -> None:
        self.eventos_recebidos.append(evento)

def test_publicar_evento_notifica_observadores_inscritos():
    publicador = PublicadorEventos()
    espiao = ObservadorEspiao()
    
    publicador.inscrever(SessaoConcluida, espiao)
    
    evento = SessaoConcluida(
        sessao_id=uuid4(),
        usuario_id=uuid4(),
        duracao_minutos=25,
        conclusao=datetime.now()
    )
    
    publicador.publicar(evento)
    
    assert len(espiao.eventos_recebidos) == 1
    assert espiao.eventos_recebidos[0] == evento

def test_publicar_evento_ignora_observadores_de_outros_tipos():
    publicador = PublicadorEventos()
    espiao_conclusao = ObservadorEspiao()
    
    publicador.inscrever(SessaoConcluida, espiao_conclusao)
    
    evento_podada = SessaoPodada(
        sessao_id=uuid4(),
        usuario_id=uuid4(),
        duracao_minutos=10,
        podada_em=datetime.now()
    )
    
    # Publica um evento de poda, mas o espião só quer saber de conclusões
    publicador.publicar(evento_podada)
    
    assert len(espiao_conclusao.eventos_recebidos) == 0

def test_publicar_evento_sem_inscritos_nao_causa_erro():
    publicador = PublicadorEventos()
    evento = SessaoConcluida(uuid4(), uuid4(), 25, datetime.now())
    
    # Executa sem quebrar a aplicação
    publicador.publicar(evento)