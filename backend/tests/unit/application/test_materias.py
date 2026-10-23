from uuid import uuid4

import pytest

from app.application.materias import MateriaService
from app.domain.excecoes import (
    CorInvalida,
    MateriaJaExiste,
    MateriaNaoEncontrada,
    NomeMateriaInvalido,
)
from tests.repositorios import RepositorioMateriaMemoria


@pytest.fixture
def servico():
    return MateriaService(RepositorioMateriaMemoria())


def test_criar_materia_sucesso(servico):
    usuario_id = uuid4()
    materia = servico.criar(usuario_id, "Cálculo I", "#8B7BFF")

    assert materia.usuario_id == usuario_id
    assert materia.nome == "Cálculo I"
    assert materia.cor == "#8B7BFF"

    salva = servico.buscar(usuario_id, materia.id)
    assert salva == materia


def test_criar_materia_recusa_nome_duplicado_para_mesmo_usuario(servico):
    usuario_id = uuid4()
    servico.criar(usuario_id, "Cálculo I", "#8B7BFF")

    with pytest.raises(MateriaJaExiste):
        servico.criar(usuario_id, "cálculo i", "#3EE6E0")  # case-insensitive


def test_permite_mesmo_nome_para_usuarios_diferentes(servico):
    usuario1 = uuid4()
    usuario2 = uuid4()

    materia1 = servico.criar(usuario1, "Cálculo I", "#8B7BFF")
    materia2 = servico.criar(usuario2, "Cálculo I", "#3EE6E0")

    assert materia1.id != materia2.id
    assert materia1.nome == materia2.nome


def test_criar_materia_valida_campos_pelo_dominio(servico):
    usuario_id = uuid4()

    with pytest.raises(NomeMateriaInvalido):
        servico.criar(usuario_id, "   ", "#8B7BFF")

    with pytest.raises(CorInvalida):
        servico.criar(usuario_id, "Cálculo", "cor-invalida")


def test_listar_materias_do_usuario_ordenadas_por_nome(servico):
    usuario_id = uuid4()
    outro_usuario = uuid4()

    servico.criar(usuario_id, "POO", "#3EE6E0")
    servico.criar(usuario_id, "Álgebra Linear", "#FFC857")
    servico.criar(usuario_id, "Cálculo I", "#8B7BFF")
    servico.criar(outro_usuario, "Física", "#5BE49B")

    materias = servico.listar(usuario_id)

    assert len(materias) == 3
    assert [m.nome for m in materias] == ["Álgebra Linear", "Cálculo I", "POO"]


def test_buscar_materia_por_id_sucesso(servico):
    usuario_id = uuid4()
    materia = servico.criar(usuario_id, "POO", "#3EE6E0")

    encontrada = servico.buscar(usuario_id, materia.id)
    assert encontrada == materia


def test_buscar_materia_inexistente_lanca_erro(servico):
    usuario_id = uuid4()

    with pytest.raises(MateriaNaoEncontrada):
        servico.buscar(usuario_id, uuid4())


def test_buscar_materia_de_outro_usuario_lanca_materia_nao_encontrada(servico):
    usuario1 = uuid4()
    usuario2 = uuid4()

    materia = servico.criar(usuario1, "POO", "#3EE6E0")

    with pytest.raises(MateriaNaoEncontrada):
        servico.buscar(usuario2, materia.id)


def test_atualizar_materia_nome_e_cor(servico):
    usuario_id = uuid4()
    materia = servico.criar(usuario_id, "Cálculo I", "#8B7BFF")

    atualizada = servico.atualizar(
        usuario_id, materia.id, nome="Cálculo II", cor="#3EE6E0"
    )

    assert atualizada.nome == "Cálculo II"
    assert atualizada.cor == "#3EE6E0"

    consultada = servico.buscar(usuario_id, materia.id)
    assert consultada.nome == "Cálculo II"
    assert consultada.cor == "#3EE6E0"


def test_atualizar_recusa_nome_duplicado_de_outra_materia(servico):
    usuario_id = uuid4()
    servico.criar(usuario_id, "Cálculo", "#8B7BFF")
    poo = servico.criar(usuario_id, "POO", "#3EE6E0")

    with pytest.raises(MateriaJaExiste):
        servico.atualizar(usuario_id, poo.id, nome="cálculo")


def test_atualizar_permite_manter_mesmo_nome_ao_trocar_cor(servico):
    usuario_id = uuid4()
    materia = servico.criar(usuario_id, "Cálculo", "#8B7BFF")

    atualizada = servico.atualizar(usuario_id, materia.id, cor="#5BE49B")
    assert atualizada.cor == "#5BE49B"
    assert atualizada.nome == "Cálculo"


def test_remover_materia(servico):
    usuario_id = uuid4()
    materia = servico.criar(usuario_id, "Cálculo", "#8B7BFF")

    servico.remover(usuario_id, materia.id)

    with pytest.raises(MateriaNaoEncontrada):
        servico.buscar(usuario_id, materia.id)

    assert len(servico.listar(usuario_id)) == 0


def test_remover_materia_de_outro_usuario_recusado(servico):
    usuario1 = uuid4()
    usuario2 = uuid4()
    materia = servico.criar(usuario1, "Cálculo", "#8B7BFF")

    with pytest.raises(MateriaNaoEncontrada):
        servico.remover(usuario2, materia.id)
