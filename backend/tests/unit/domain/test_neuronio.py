from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.duracao import Duracao
from app.domain.entidades import (
    FabricaNeuronio,
    Granular,
    Neuronio,
    Piramidal,
    Purkinje,
    SessaoFoco,
    TipoNeuronio,
    Usuario,
)
from app.domain.entidades.neuronio import COR_PODADO
from app.domain.entidades.sessao_foco import Concluida, Podada
from app.domain.excecoes import DuracaoInvalida, HorarioInvalido

INICIO = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)
FIM = datetime(2026, 10, 16, 14, 25, tzinfo=UTC)


def test_cria_neuronio_ligado_a_sessao():
    usuario_id, sessao_id = uuid4(), uuid4()
    antes = datetime.now(UTC)

    neuronio = Neuronio(usuario_id, sessao_id, 60)

    assert isinstance(neuronio.id, UUID)
    assert neuronio.usuario_id == usuario_id
    assert neuronio.sessao_id == sessao_id
    assert neuronio.duracao == Duracao(60)
    assert neuronio.tipo == Purkinje()
    assert neuronio.cor == "#FFC857"
    assert neuronio.numero_dendritos == 8
    assert neuronio.raio == 9.0
    assert antes <= neuronio.criado_em <= datetime.now(UTC)
    # Por padrão é vivo (sessão concluída) e sem matéria.
    assert neuronio.vivo is True
    assert neuronio.materia_id is None


def test_neuronio_morto_de_sessao_podada_com_materia():
    materia_id = uuid4()

    neuronio = Neuronio(uuid4(), uuid4(), 25, vivo=False, materia_id=materia_id)

    assert neuronio.vivo is False
    assert neuronio.tipo == Piramidal()
    assert neuronio.cor == COR_PODADO
    assert neuronio.materia_id == materia_id


def test_recusa_duracao_invalida():
    with pytest.raises(DuracaoInvalida):
        Neuronio(uuid4(), uuid4(), 7)


def test_recusa_tipo_que_nao_e_tipo_neuronio():
    with pytest.raises(TypeError, match="TipoNeuronio"):
        Neuronio(uuid4(), uuid4(), 25, tipo="piramidal")  # type: ignore[arg-type]


def test_recusa_data_de_criacao_sem_fuso():
    with pytest.raises(HorarioInvalido):
        Neuronio(uuid4(), uuid4(), 25, criado_em=datetime(2026, 10, 12, 14, 0))


@pytest.mark.parametrize(
    "atributo",
    [
        "id",
        "usuario_id",
        "sessao_id",
        "duracao",
        "tipo",
        "cor",
        "numero_dendritos",
        "raio",
        "vivo",
        "materia_id",
        "criado_em",
    ],
)
def test_atributos_sao_somente_leitura(atributo):
    neuronio = Neuronio(uuid4(), uuid4(), 25)

    with pytest.raises(AttributeError):
        setattr(neuronio, atributo, "outro valor")


def test_entidades_de_tipos_diferentes_nunca_sao_iguais():
    id_comum = uuid4()

    assert Neuronio(uuid4(), uuid4(), 25, id=id_comum) != Usuario(
        "Julia", "julia@exemplo.com", id=id_comum
    )


def test_repr_mostra_id_e_sessao():
    neuronio = Neuronio(uuid4(), uuid4(), 25)

    assert repr(neuronio) == (
        f"Neuronio(id={neuronio.id}, sessao_id={neuronio.sessao_id})"
    )


# ==============================================================================
# TipoNeuronio e tipos concretos (#22)
# ==============================================================================


def test_tipo_neuronio_e_abstrato():
    with pytest.raises(TypeError):
        TipoNeuronio()  # type: ignore[abstract]

    class TipoIncompleto(TipoNeuronio):
        @property
        def nome(self) -> str:
            return "Incompleto"

    with pytest.raises(TypeError):
        TipoIncompleto()  # type: ignore[abstract]


@pytest.mark.parametrize(
    ("classe", "nome", "codigo", "cor", "dendritos", "raio"),
    [
        (Granular, "Granular", "granular", "#3EE6E0", 3, 4.5),
        (Piramidal, "Piramidal", "piramidal", "#8B7BFF", 5, 6.5),
        (Purkinje, "Purkinje", "purkinje", "#FFC857", 8, 9.0),
    ],
)
def test_atributos_visuais_dos_tipos_concretos(
    classe, nome, codigo, cor, dendritos, raio
):
    tipo = classe()

    assert isinstance(tipo, TipoNeuronio)
    assert tipo.nome == nome
    assert tipo.codigo == codigo
    assert tipo.cor == cor
    assert tipo.numero_dendritos == dendritos
    assert tipo.raio == raio
    assert repr(tipo) == f"{classe.__name__}()"


def test_complexidade_visual_cresce_com_a_faixa_de_duracao():
    granular, piramidal, purkinje = Granular(), Piramidal(), Purkinje()

    assert granular.numero_dendritos < piramidal.numero_dendritos
    assert piramidal.numero_dendritos < purkinje.numero_dendritos
    assert granular.raio < piramidal.raio < purkinje.raio


def test_cada_tipo_aceita_apenas_sua_faixa():
    assert not Granular().aceita(9)
    assert Granular().aceita(10)
    assert Granular().aceita(24)
    assert not Granular().aceita(25)

    assert not Piramidal().aceita(24)
    assert Piramidal().aceita(25)
    assert Piramidal().aceita(59)
    assert not Piramidal().aceita(60)

    assert not Purkinje().aceita(59)
    assert Purkinje().aceita(60)
    assert Purkinje().aceita(120)


@pytest.mark.parametrize(
    "atributo", ["nome", "codigo", "cor", "numero_dendritos", "raio"]
)
def test_atributos_do_tipo_sao_somente_leitura(atributo):
    tipo = Piramidal()

    with pytest.raises(AttributeError):
        setattr(tipo, atributo, "outro")


def test_igualdade_e_hash_dos_tipos():
    assert Granular() == Granular()
    assert Granular() != Piramidal()
    assert len({Granular(), Granular(), Piramidal(), Purkinje()}) == 3


# ==============================================================================
# FabricaNeuronio e faixas de duração (#22)
# ==============================================================================


@pytest.mark.parametrize(
    ("minutos", "esperado"),
    [
        # Limites e interior da faixa Granular (10 a 24 min)
        (10, Granular()),
        (15, Granular()),
        (20, Granular()),
        (24, Granular()),
        # Limites e interior da faixa Piramidal (25 a 59 min)
        (25, Piramidal()),
        (30, Piramidal()),
        (45, Piramidal()),
        (55, Piramidal()),
        (59, Piramidal()),
        # Limites e interior da faixa Purkinje (60+ min)
        (60, Purkinje()),
        (90, Purkinje()),
        (120, Purkinje()),
    ],
)
def test_fabrica_escolhe_o_tipo_pela_faixa_inclusive_nos_limites(minutos, esperado):
    tipo = FabricaNeuronio.tipo_para(minutos)

    assert tipo == esperado
    assert type(tipo) is type(esperado)


@pytest.mark.parametrize("minutos", [0, 5, 9, -10, True, "25"])
def test_fabrica_recusa_duracao_fora_das_faixas_ou_nao_inteira(minutos):
    with pytest.raises(DuracaoInvalida):
        FabricaNeuronio.tipo_para(minutos)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("duracao_minutos", "esperado"),
    [
        (10, Granular()),
        (15, Granular()),
        (20, Granular()),
        (25, Piramidal()),
        (30, Piramidal()),
        (55, Piramidal()),
        (60, Purkinje()),
        (90, Purkinje()),
        (120, Purkinje()),
    ],
)
def test_fabrica_cria_neuronio_a_partir_da_sessao_em_cada_faixa(
    duracao_minutos, esperado
):
    materia_id = uuid4()
    sessao = SessaoFoco(
        uuid4(),
        duracao_minutos,
        inicio=INICIO,
        encerrada_em=FIM,
        estado=Concluida(),
        materia_id=materia_id,
    )

    neuronio = FabricaNeuronio.criar(sessao)

    assert isinstance(neuronio, Neuronio)
    assert neuronio.usuario_id == sessao.usuario_id
    assert neuronio.sessao_id == sessao.id
    assert neuronio.duracao.minutos == duracao_minutos
    assert neuronio.tipo == esperado
    assert neuronio.cor == esperado.cor
    assert neuronio.numero_dendritos == esperado.numero_dendritos
    assert neuronio.raio == esperado.raio
    assert neuronio.vivo is True
    assert neuronio.materia_id == materia_id
    assert neuronio.criado_em == FIM


def test_fabrica_cria_neuronio_morto_quando_a_sessao_foi_podada():
    sessao = SessaoFoco(
        uuid4(),
        60,
        inicio=INICIO,
        encerrada_em=FIM,
        estado=Podada(),
    )

    neuronio = FabricaNeuronio.criar(sessao)

    assert neuronio.tipo == Purkinje()
    assert neuronio.vivo is False
    assert neuronio.cor == COR_PODADO
    assert neuronio.criado_em == FIM


def test_fabrica_recusa_lista_vazia_de_tipos():
    with pytest.raises(ValueError, match="pelo menos um tipo"):
        FabricaNeuronio([])


def test_criterio_adicionar_tipo_novo_nao_altera_quem_chama_a_fabrica():
    class Estrelado(TipoNeuronio):
        duracao_minima = 90
        duracao_maxima = None

        @property
        def nome(self) -> str:
            return "Estrelado"

        @property
        def cor(self) -> str:
            return "#FF6FB5"

        @property
        def numero_dendritos(self) -> int:
            return 12

        @property
        def raio(self) -> float:
            return 11.0

    # Quem chama só conhece o contrato `fabrica.criar(sessao)`.
    def registrar_fim_da_sessao(
        sessao: SessaoFoco,
        fabrica: FabricaNeuronio | type[FabricaNeuronio] = FabricaNeuronio,
    ) -> Neuronio:
        return fabrica.criar(sessao)

    fabrica_estendida = FabricaNeuronio((*FabricaNeuronio.TIPOS_PADRAO, Estrelado()))
    sessao_60 = SessaoFoco(uuid4(), 60, inicio=INICIO)
    sessao_90 = SessaoFoco(uuid4(), 90, inicio=INICIO)

    assert FabricaNeuronio.TIPOS_PADRAO == (Granular(), Piramidal(), Purkinje())
    assert len(fabrica_estendida.tipos) == 4
    assert registrar_fim_da_sessao(sessao_60, fabrica_estendida).tipo == Purkinje()
    novo = registrar_fim_da_sessao(sessao_90, fabrica_estendida)
    assert novo.tipo == Estrelado()
    assert novo.cor == "#FF6FB5"
    assert novo.numero_dendritos == 12
    assert novo.raio == 11.0
