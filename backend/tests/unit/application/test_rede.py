from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.application.rede import RedeNeuralService
from app.domain.entidades import Neuronio
from tests.repositorios import RepositorioRedeNeuralMemoria

INICIO = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)


def test_registrar_grava_o_neuronio_e_as_sinapses():
    redes = RepositorioRedeNeuralMemoria()
    servico = RedeNeuralService(redes)
    usuario_id = uuid4()
    primeiro = Neuronio(usuario_id, uuid4(), 25, criado_em=INICIO)
    segundo = Neuronio(usuario_id, uuid4(), 25, criado_em=INICIO + timedelta(hours=1))

    assert servico.registrar(primeiro) == []
    [sinapse] = servico.registrar(segundo)

    rede = redes.carregar(usuario_id)
    assert rede.neuronios == [primeiro, segundo]
    assert rede.sinapses == [sinapse]


def test_consultar_aplica_os_filtros_na_rede_do_estudante():
    redes = RepositorioRedeNeuralMemoria()
    servico = RedeNeuralService(redes)
    usuario_id = uuid4()
    neuronios = [
        Neuronio(usuario_id, uuid4(), 25, criado_em=INICIO + timedelta(days=dia))
        for dia in range(3)
    ]
    for neuronio in neuronios:
        servico.registrar(neuronio)
    servico.registrar(Neuronio(uuid4(), uuid4(), 25, criado_em=INICIO))

    recorte = servico.consultar(usuario_id, de=INICIO + timedelta(days=1))

    assert recorte.neuronios == neuronios[1:]
    assert len(recorte.sinapses) == 1
