from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.entidades import Materia
from app.domain.excecoes import CorInvalida, HorarioInvalido, NomeMateriaInvalido


def test_cria_materia_com_id_e_data_de_criacao():
    usuario_id = uuid4()
    antes = datetime.now(UTC)
    materia = Materia(usuario_id, "Cálculo I", "#8b7bff")

    assert isinstance(materia.id, UUID)
    assert materia.usuario_id == usuario_id
    assert materia.nome == "Cálculo I"
    assert materia.cor == "#8B7BFF"
    assert antes <= materia.criada_em <= datetime.now(UTC)


def test_reconstroi_materia_com_id_e_data_existentes():
    id_existente = uuid4()
    usuario_id = uuid4()
    criada_em = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    materia = Materia(
        usuario_id,
        "POO",
        "#3EE6E0",
        id=id_existente,
        criada_em=criada_em,
    )

    assert materia.id == id_existente
    assert materia.usuario_id == usuario_id
    assert materia.criada_em == criada_em


def test_normaliza_nome_e_cor():
    materia = Materia(uuid4(), "  Física Quântica  ", "  #ffc857  ")

    assert materia.nome == "Física Quântica"
    assert materia.cor == "#FFC857"


@pytest.mark.parametrize("nome", ["", "   ", None, "a" * 101])
def test_recusa_nome_invalido(nome):
    with pytest.raises(NomeMateriaInvalido):
        Materia(uuid4(), nome, "#8B7BFF")


@pytest.mark.parametrize(
    "cor",
    [
        "",
        "   ",
        None,
        "8B7BFF",        # sem #
        "#123",          # 3 dígitos
        "#GGGGGG",       # hex inválido
        "#8B7BFF99",     # 8 dígitos
        "ciano",         # nome em vez de hex
        " #8B7BF ",      # 5 dígitos
    ],
)
def test_recusa_cor_invalida(cor):
    with pytest.raises(CorInvalida):
        Materia(uuid4(), "Cálculo", cor)


def test_recusa_usuario_id_invalido():
    with pytest.raises(TypeError):
        Materia("nao-e-uuid", "Cálculo", "#8B7BFF")  # type: ignore[arg-type]


def test_atualizacao_de_nome_e_cor():
    materia = Materia(uuid4(), "Cálculo I", "#8B7BFF")

    materia.nome = "  Cálculo II  "
    assert materia.nome == "Cálculo II"

    materia.cor = "#3ee6e0"
    assert materia.cor == "#3EE6E0"

    materia.atualizar(nome="Cálculo Avançado", cor="#5BE49B")
    assert materia.nome == "Cálculo Avançado"
    assert materia.cor == "#5BE49B"


def test_recusa_atualizacao_invalida():
    materia = Materia(uuid4(), "Cálculo", "#8B7BFF")

    with pytest.raises(NomeMateriaInvalido):
        materia.nome = "   "

    with pytest.raises(CorInvalida):
        materia.cor = "#INVALID"


def test_igualdade_por_id():
    id_comum = uuid4()
    usuario_id = uuid4()
    materia1 = Materia(usuario_id, "Cálculo", "#8B7BFF", id=id_comum)
    materia2 = Materia(uuid4(), "Álgebra", "#3EE6E0", id=id_comum)

    assert materia1 == materia2
    assert hash(materia1) == hash(materia2)

    materia_diferente = Materia(usuario_id, "Cálculo", "#8B7BFF")
    assert materia1 != materia_diferente


def test_representacao_em_string():
    materia = Materia(uuid4(), "Cálculo", "#8B7BFF")
    esperado = f"Materia(id={materia.id}, nome='Cálculo', cor='#8B7BFF')"
    assert repr(materia) == esperado


def test_recusa_criada_em_sem_fuso_horario():
    with pytest.raises(HorarioInvalido):
        Materia(
            uuid4(),
            "Cálculo",
            "#8B7BFF",
            criada_em=datetime(2026, 10, 1, 12, 0),  # naive
        )
