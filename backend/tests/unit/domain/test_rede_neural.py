from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.entidades import Neuronio, Sinapse
from app.domain.excecoes import RedeNeuralInvalida, SinapseInvalida
from app.domain.formacao_sinapses import (
    Conexao,
    RegraFormacaoSinapses,
    RegraRecentesEMesmaMateria,
)
from app.domain.rede_neural import RedeNeural

INICIO = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
USUARIO = uuid4()
CALCULO, FISICA = uuid4(), uuid4()


class Construtor:
    """Cria neurônios em ordem, um por hora, como sessões em sequência."""

    def __init__(self) -> None:
        self._horas = 0

    def __call__(
        self, *, materia: UUID | None = None, vivo: bool = True, usuario=USUARIO
    ) -> Neuronio:
        self._horas += 1
        return Neuronio(
            usuario,
            uuid4(),
            25,
            vivo=vivo,
            materia_id=materia,
            criado_em=INICIO + timedelta(hours=self._horas),
        )


@pytest.fixture
def novo():
    return Construtor()


def ligacoes(sinapses: list[Sinapse]) -> dict[UUID, int]:
    """Origem e peso de cada sinapse formada por um neurônio novo."""
    return {s.origem_id: s.peso for s in sinapses}


# ==============================================================================
# Regra padrão: os 2 mais recentes e o último da mesma matéria
# ==============================================================================


def test_o_primeiro_neuronio_nao_tem_a_quem_se_ligar(novo):
    rede = RedeNeural(USUARIO)

    assert rede.adicionar(novo()) == []


def test_liga_aos_dois_neuronios_mais_recentes(novo):
    rede = RedeNeural(USUARIO)
    a, b, c = novo(), novo(), novo()
    for neuronio in (a, b, c):
        rede.adicionar(neuronio)

    d = novo()
    sinapses = rede.adicionar(d)

    assert ligacoes(sinapses) == {b.id: 1, c.id: 1}
    assert all(s.destino_id == d.id for s in sinapses)
    assert all(s.criada_em == d.criado_em for s in sinapses)


def test_liga_ao_ultimo_da_mesma_materia_mesmo_que_nao_seja_recente(novo):
    rede = RedeNeural(USUARIO)
    calculo = novo(materia=CALCULO)
    outras = [novo(materia=FISICA), novo(materia=FISICA), novo()]
    for neuronio in (calculo, *outras):
        rede.adicionar(neuronio)

    sinapses = rede.adicionar(novo(materia=CALCULO))

    # Os 2 recentes com peso 1 e a matéria reforçada com peso 2.
    assert ligacoes(sinapses) == {outras[1].id: 1, outras[2].id: 1, calculo.id: 2}


def test_criterio_peso_cresce_cada_vez_que_a_materia_volta_a_se_conectar(novo):
    rede = RedeNeural(USUARIO, regra=RegraRecentesEMesmaMateria(peso_maximo=4))
    anterior = novo(materia=CALCULO)
    rede.adicionar(anterior)
    pesos = []
    for _ in range(4):
        # Outra matéria no meio: a trilha de Cálculo continua mesmo assim.
        rede.adicionar(novo(materia=FISICA))
        atual = novo(materia=CALCULO)
        pesos.append(ligacoes(rede.adicionar(atual))[anterior.id])
        anterior = atual

    assert pesos == [2, 3, 4, 4]  # para no peso máximo


def test_ultimo_da_materia_entre_os_recentes_gera_uma_sinapse_so(novo):
    rede = RedeNeural(USUARIO)
    a, b = novo(), novo(materia=CALCULO)
    rede.adicionar(a)
    rede.adicionar(b)

    sinapses = rede.adicionar(novo(materia=CALCULO))

    assert len(sinapses) == 2
    assert ligacoes(sinapses) == {a.id: 1, b.id: 2}


def test_neuronio_sem_materia_so_liga_aos_recentes(novo):
    rede = RedeNeural(USUARIO)
    sem_materia = novo()
    rede.adicionar(sem_materia)
    for _ in range(2):
        rede.adicionar(novo(materia=FISICA))

    sinapses = rede.adicionar(novo())

    assert sem_materia.id not in ligacoes(sinapses)
    assert set(ligacoes(sinapses).values()) == {1}


def test_neuronios_mortos_nao_contam_como_recentes_nem_como_ultimo_da_materia(novo):
    rede = RedeNeural(USUARIO)
    vivo_calculo, vivo = novo(materia=CALCULO), novo()
    mortos = [novo(materia=CALCULO, vivo=False), novo(vivo=False)]
    for neuronio in (vivo_calculo, vivo, *mortos):
        rede.adicionar(neuronio)

    sinapses = rede.adicionar(novo(materia=CALCULO))

    assert ligacoes(sinapses) == {vivo_calculo.id: 2, vivo.id: 1}


def test_quantidade_de_recentes_e_configuravel(novo):
    neuronios = [novo() for _ in range(4)]
    rede = RedeNeural(USUARIO, neuronios, regra=RegraRecentesEMesmaMateria(recentes=3))

    assert set(ligacoes(rede.adicionar(novo()))) == {n.id for n in neuronios[1:]}

    sem_recentes = RedeNeural(
        USUARIO, neuronios, regra=RegraRecentesEMesmaMateria(recentes=0)
    )
    assert sem_recentes.adicionar(novo()) == []


@pytest.mark.parametrize(
    "argumentos", [{"recentes": -1}, {"peso_maximo": 0}], ids=["recentes", "peso"]
)
def test_recusa_configuracao_invalida_da_regra(argumentos):
    with pytest.raises(ValueError):
        RegraRecentesEMesmaMateria(**argumentos)


# ==============================================================================
# Agregado: invariantes que valem para qualquer regra
# ==============================================================================


def test_criterio_poda_sinaptica_neuronio_morto_entra_sem_sinapses(novo):
    rede = RedeNeural(USUARIO, [novo(), novo()])
    morto = novo(vivo=False)

    assert rede.adicionar(morto) == []
    assert rede.neuronio(morto.id) is morto
    assert rede.sinapses_de(morto.id) == []


def test_recusa_neuronio_de_outro_estudante(novo):
    rede = RedeNeural(USUARIO)

    with pytest.raises(RedeNeuralInvalida, match="outro estudante"):
        rede.adicionar(novo(usuario=uuid4()))


def test_recusa_neuronio_repetido_ou_da_mesma_sessao(novo):
    neuronio = novo()
    rede = RedeNeural(USUARIO, [neuronio])
    mesma_sessao = Neuronio(
        USUARIO, neuronio.sessao_id, 25, criado_em=neuronio.criado_em
    )

    for repetido in (neuronio, mesma_sessao):
        with pytest.raises(RedeNeuralInvalida, match="já está na rede"):
            rede.adicionar(repetido)


def test_neuronio_com_data_anterior_entra_na_posicao_certa(novo):
    # Ex.: a sessão abandonada é podada no limite (duração + 5 min), que pode ser
    # antes do neurônio de uma sessão concluída nesse meio-tempo.
    antigo_a, antigo_b, anterior, recente = novo(), novo(), novo(), novo()
    rede = RedeNeural(USUARIO, [antigo_a, antigo_b, recente])

    sinapses = rede.adicionar(anterior)

    assert rede.neuronios == [antigo_a, antigo_b, anterior, recente]
    # Só se liga aos que existiam antes dele, não ao mais recente.
    assert set(ligacoes(sinapses)) == {antigo_a.id, antigo_b.id}


class RegraFixa(RegraFormacaoSinapses):
    """Regra de teste que propõe exatamente as conexões informadas."""

    def __init__(self, *conexoes: Conexao):
        self._conexoes = list(conexoes)

    def conexoes(self, novo, rede):
        return self._conexoes


def test_criterio_sem_sinapses_repetidas_mesmo_que_a_regra_proponha(novo):
    a = novo()
    rede = RedeNeural(USUARIO, [a], regra=RegraFixa(Conexao(a.id, 1), Conexao(a.id, 2)))

    with pytest.raises(SinapseInvalida, match="já estão ligados"):
        rede.adicionar(novo())


def test_criterio_sem_autoconexao_mesmo_que_a_regra_proponha(novo):
    neuronio = novo()

    class LigaAoProprio(RegraFormacaoSinapses):
        def conexoes(self, novo, rede):
            return [Conexao(novo.id, 1)]

    rede = RedeNeural(USUARIO, regra=LigaAoProprio())

    with pytest.raises(SinapseInvalida, match="ele mesmo"):
        rede.adicionar(neuronio)


def test_recusa_ligacao_com_neuronio_morto_ou_fora_da_rede(novo):
    morto = novo(vivo=False)

    for alvo in (morto.id, uuid4()):
        rede = RedeNeural(USUARIO, [morto], regra=RegraFixa(Conexao(alvo, 1)))
        with pytest.raises(SinapseInvalida):
            rede.adicionar(novo())


def test_ligacao_invalida_nao_deixa_a_rede_pela_metade(novo):
    a = novo()
    rede = RedeNeural(
        USUARIO, [a], regra=RegraFixa(Conexao(a.id, 1), Conexao(uuid4(), 1))
    )

    with pytest.raises(SinapseInvalida):
        rede.adicionar(novo())

    assert len(rede) == 1
    assert rede.sinapses == []
    assert rede.neuronios_novos == []


def test_dados_carregados_passam_pelas_mesmas_regras(novo):
    vivo, morto = novo(), novo(vivo=False)

    with pytest.raises(SinapseInvalida, match="podado"):
        RedeNeural(USUARIO, [vivo, morto], [Sinapse(vivo.id, morto.id, 1)])
    with pytest.raises(SinapseInvalida, match="já estão ligados"):
        RedeNeural(
            USUARIO,
            [vivo, outro := novo()],
            [Sinapse(vivo.id, outro.id, 1), Sinapse(outro.id, vivo.id, 1)],
        )


def test_guarda_as_novidades_ate_serem_salvas(novo):
    a = novo()
    rede = RedeNeural(USUARIO, [a])
    b = novo()

    sinapses = rede.adicionar(b)

    assert rede.neuronios_novos == [b]
    assert rede.sinapses_novas == sinapses
    rede.marcar_como_salva()
    assert rede.neuronios_novos == []
    assert rede.sinapses_novas == []
    assert rede.neuronios == [a, b]


def test_listas_devolvidas_sao_copias(novo):
    a, b = novo(), novo()
    rede = RedeNeural(USUARIO, [a])
    rede.adicionar(b)

    rede.neuronios.clear()
    rede.sinapses.clear()
    rede.sinapses_de(a.id).clear()

    assert len(rede) == 2
    assert len(rede.sinapses) == 1
    assert rede.sinapses_de(a.id) == rede.sinapses_de(b.id) == rede.sinapses


def test_neuronios_ficam_em_ordem_cronologica(novo):
    a, b, c = novo(), novo(), novo(vivo=False)

    rede = RedeNeural(USUARIO, [c, a, b])

    assert rede.neuronios == [a, b, c]
    assert rede.vivos == [a, b]


def test_repr_resume_a_rede(novo):
    rede = RedeNeural(USUARIO, [novo(), novo()])
    rede.adicionar(novo())

    assert repr(rede) == f"RedeNeural(usuario_id={USUARIO}, neuronios=3, sinapses=2)"


# ==============================================================================
# Recorte para mostrar a rede (#25)
# ==============================================================================


def test_sem_filtros_o_recorte_e_a_rede_inteira(novo):
    rede = RedeNeural(USUARIO)
    for neuronio in (novo(), novo(), novo(vivo=False), novo()):
        rede.adicionar(neuronio)

    recorte = rede.recortar()

    assert recorte.neuronios == rede.neuronios
    assert recorte.sinapses == rede.sinapses


def test_recorte_por_periodo_inclui_as_pontas(novo):
    a, b, c, d = novo(), novo(), novo(), novo()
    rede = RedeNeural(USUARIO, [a, b, c, d])

    recorte = rede.recortar(de=b.criado_em, ate=c.criado_em)

    assert recorte.neuronios == [b, c]
    assert rede.recortar(de=c.criado_em).neuronios == [c, d]
    assert rede.recortar(ate=a.criado_em).neuronios == [a]


def test_recorte_por_materia(novo):
    calculo, fisica, sem_materia = novo(materia=CALCULO), novo(materia=FISICA), novo()
    rede = RedeNeural(USUARIO, [calculo, fisica, sem_materia])

    assert rede.recortar(materia_id=CALCULO).neuronios == [calculo]


def test_recorte_so_traz_sinapses_entre_neuronios_escolhidos(novo):
    rede = RedeNeural(USUARIO)
    a, b, c = novo(materia=CALCULO), novo(materia=FISICA), novo(materia=CALCULO)
    for neuronio in (a, b, c):
        rede.adicionar(neuronio)

    recorte = rede.recortar(materia_id=CALCULO)

    # c se liga a a (matéria) e a b (recente); b ficou de fora, então só a→c vem.
    assert [(s.origem_id, s.destino_id) for s in recorte.sinapses] == [(a.id, c.id)]
