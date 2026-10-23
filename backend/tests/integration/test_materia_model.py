import uuid
from datetime import datetime

import pytest
from django.db.utils import IntegrityError

from app.domain.entidades.materia import Materia
from app.infra.modelos.materia import MateriaModel
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario():
    return UsuarioModel.objects.create_user(
        email="estudante@synapse.com",
        password="senha-segura-123",
        nome="Estudante Foco",
    )


def test_cria_materia_model(usuario):
    materia = MateriaModel.objects.create(
        usuario=usuario,
        nome="Cálculo I",
        cor="#8B7BFF",
    )

    assert isinstance(materia.id, uuid.UUID)
    assert materia.usuario == usuario
    assert materia.nome == "Cálculo I"
    assert materia.cor == "#8B7BFF"
    assert isinstance(materia.criada_em, datetime)
    assert str(materia) == "Cálculo I (#8B7BFF)"


def test_converte_model_para_entidade_de_dominio(usuario):
    model = MateriaModel.objects.create(
        usuario=usuario,
        nome="POO",
        cor="#3EE6E0",
    )

    entidade = model.para_entidade()

    assert isinstance(entidade, Materia)
    assert entidade.id == model.id
    assert entidade.usuario_id == usuario.id
    assert entidade.nome == "POO"
    assert entidade.cor == "#3EE6E0"
    assert entidade.criada_em == model.criada_em


def test_cria_model_a_partir_de_entidade(usuario):
    entidade = Materia(
        usuario_id=usuario.id,
        nome="Física",
        cor="#5BE49B",
    )

    model = MateriaModel.de_entidade(entidade)

    assert model.id == entidade.id
    assert model.usuario_id == usuario.id
    assert model.nome == "Física"
    assert model.cor == "#5BE49B"
    assert model.criada_em == entidade.criada_em


def test_unicidade_nome_case_insensitive_por_usuario(usuario):
    MateriaModel.objects.create(usuario=usuario, nome="Cálculo", cor="#8B7BFF")

    with pytest.raises(IntegrityError):
        MateriaModel.objects.create(usuario=usuario, nome="cálculo", cor="#3EE6E0")


def test_usuarios_diferentes_podem_ter_materia_com_mesmo_nome(usuario):
    outro_usuario = UsuarioModel.objects.create_user(
        email="outro@synapse.com", password="senha-segura-123", nome="Outro"
    )

    m1 = MateriaModel.objects.create(usuario=usuario, nome="Cálculo", cor="#8B7BFF")
    m2 = MateriaModel.objects.create(
        usuario=outro_usuario, nome="Cálculo", cor="#3EE6E0"
    )

    assert m1.id != m2.id
    assert m1.nome == m2.nome


def test_exclusao_de_usuario_em_cascata(usuario):
    materia = MateriaModel.objects.create(usuario=usuario, nome="POO", cor="#3EE6E0")

    usuario.delete()

    assert not MateriaModel.objects.filter(id=materia.id).exists()


def test_exclusao_de_materia_desvincula_sessao_sem_apagar_sessao(usuario):
    materia = MateriaModel.objects.create(usuario=usuario, nome="POO", cor="#3EE6E0")
    sessao = SessaoFocoModel.objects.create(
        usuario=usuario,
        duracao_minutos=25,
        materia=materia,
    )

    assert sessao.materia_id == materia.id

    # Apagar a matéria NÃO apaga a sessão (#27)
    materia.delete()

    sessao.refresh_from_db()
    assert sessao.materia is None
    assert sessao.materia_id is None
    assert SessaoFocoModel.objects.filter(id=sessao.id).exists()
