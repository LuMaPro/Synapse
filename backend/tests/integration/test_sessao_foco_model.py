import uuid
from datetime import datetime

import pytest
from django.utils import timezone

from app.domain.entidades.sessao_foco import SessaoFoco
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


def test_cria_sessao_foco_model(usuario):
    sessao = SessaoFocoModel.objects.create(
        usuario=usuario,
        duracao_minutos=25,
    )

    assert isinstance(sessao.id, uuid.UUID)
    assert sessao.usuario == usuario
    assert sessao.duracao_minutos == 25
    assert sessao.estado == "em_andamento"
    assert isinstance(sessao.inicio, datetime)
    assert sessao.encerrada_em is None
    assert "Sessão" in str(sessao)


def test_converte_model_para_entidade_de_dominio(usuario):
    sessao_model = SessaoFocoModel.objects.create(
        usuario=usuario,
        duracao_minutos=45,
    )

    entidade = sessao_model.para_entidade()

    assert isinstance(entidade, SessaoFoco)
    assert entidade.id == sessao_model.id
    assert entidade.usuario_id == usuario.id
    assert entidade.duracao.minutos == 45
    assert entidade.codigo_estado == "em_andamento"
    assert entidade.inicio == sessao_model.inicio


def test_cria_model_a_partir_de_entidade(usuario):
    entidade = SessaoFoco(
        usuario_id=usuario.id,
        duracao_minutos=30,
    )

    model = SessaoFocoModel.de_entidade(entidade)

    assert model.id == entidade.id
    assert model.usuario_id == usuario.id
    assert model.duracao_minutos == 30
    assert model.estado == "em_andamento"

    # Salva no banco de dados e verifica persistência
    model.save()
    recuperado = SessaoFocoModel.objects.get(id=entidade.id)
    assert recuperado.duracao_minutos == 30
    assert recuperado.usuario == usuario


def test_exclusao_de_usuario_em_cascata(usuario):
    sessao = SessaoFocoModel.objects.create(
        usuario=usuario,
        duracao_minutos=25,
    )

    usuario.delete()

    assert not SessaoFocoModel.objects.filter(id=sessao.id).exists()


def test_atualiza_estado_e_encerrada_em(usuario):
    sessao = SessaoFocoModel.objects.create(
        usuario=usuario,
        duracao_minutos=25,
    )

    agora = timezone.now()
    sessao.estado = SessaoFocoModel.Estado.CONCLUIDA
    sessao.encerrada_em = agora
    sessao.save()

    atualizado = SessaoFocoModel.objects.get(id=sessao.id)
    assert atualizado.estado == "concluida"
    assert atualizado.encerrada_em == agora
