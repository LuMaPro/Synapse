from uuid import uuid4

import pytest

from app.domain.entidades.sessao_foco import Concluida, EmAndamento, Podada, SessaoFoco
from app.domain.entidades.usuario import Usuario
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel
from app.infra.repositorios import RepositorioSessaoDjango, RepositorioUsuarioDjango

pytestmark = pytest.mark.django_db


class TestRepositorioUsuarioDjango:
    def test_salva_novo_usuario_e_busca_por_id(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Lucas Oliveira", email="lucas@synapse.com")

        repo.salvar(usuario)

        recuperado = repo.buscar_por_id(usuario.id)
        assert recuperado is not None
        assert isinstance(recuperado, Usuario)
        assert recuperado.id == usuario.id
        assert recuperado.nome == "Lucas Oliveira"
        assert recuperado.email == "lucas@synapse.com"

        # Confirma persistência direta no model
        model = UsuarioModel.objects.get(id=usuario.id)
        assert model.email == "lucas@synapse.com"

    def test_atualiza_usuario_existente(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Beatriz", email="bia@synapse.com")
        repo.salvar(usuario)

        usuario.nome = "Beatriz Lima"
        repo.salvar(usuario)

        recuperado = repo.buscar_por_id(usuario.id)
        assert recuperado is not None
        assert recuperado.nome == "Beatriz Lima"

    def test_busca_por_email_case_insensitive(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Carlos", email="carlos@synapse.com")
        repo.salvar(usuario)

        assert repo.buscar_por_email("CARLOS@synapse.com") == usuario
        assert repo.buscar_por_email("carlos@synapse.com") == usuario
        assert repo.buscar_por_email("inexistente@synapse.com") is None

    def test_existe_com_email(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Daniela", email="daniela@synapse.com")
        repo.salvar(usuario)

        assert repo.existe_com_email("DANIELA@synapse.com") is True
        assert repo.existe_com_email("outro@synapse.com") is False

    def test_buscar_por_id_inexistente_retorna_none(self):
        repo = RepositorioUsuarioDjango()
        assert repo.buscar_por_id(uuid4()) is None


class TestRepositorioSessaoDjango:
    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(
            email="foco@synapse.com",
            password="senha-123",
            nome="Foco Estudante",
        )

    def test_salva_nova_sessao_e_busca_por_id(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)

        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert isinstance(recuperada, SessaoFoco)
        assert recuperada.id == sessao.id
        assert recuperada.usuario_id == usuario.id
        assert recuperada.duracao.minutos == 25
        assert recuperada.codigo_estado == "em_andamento"
        assert isinstance(recuperada._estado, EmAndamento)

    def test_atualiza_sessao_para_concluida(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)
        repo.salvar(sessao)

        # Transição no domínio
        sessao.concluir(relogio=lambda: sessao.fim_previsto)
        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert recuperada.codigo_estado == "concluida"
        assert isinstance(recuperada._estado, Concluida)
        assert recuperada.encerrada_em is not None

        # Valida no model do Django
        model = SessaoFocoModel.objects.get(id=sessao.id)
        assert model.estado == "concluida"

    def test_atualiza_sessao_para_podada(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=30)
        repo.salvar(sessao)

        sessao.podar()
        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert recuperada.codigo_estado == "podada"
        assert isinstance(recuperada._estado, Podada)

    def test_listar_por_usuario(self, usuario):
        repo = RepositorioSessaoDjango()
        outro_usuario = UsuarioModel.objects.create_user(
            email="outro@synapse.com", password="x", nome="Outro"
        )

        sessao1 = SessaoFoco(usuario_id=usuario.id, duracao_minutos=20)
        sessao2 = SessaoFoco(usuario_id=usuario.id, duracao_minutos=40)
        sessao_outro = SessaoFoco(usuario_id=outro_usuario.id, duracao_minutos=50)

        repo.salvar(sessao1)
        repo.salvar(sessao2)
        repo.salvar(sessao_outro)

        sessoes_usuario = repo.listar_por_usuario(usuario.id)
        assert len(sessoes_usuario) == 2
        ids = {s.id for s in sessoes_usuario}
        assert ids == {sessao1.id, sessao2.id}

    def test_buscar_ativa_por_usuario(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)
        repo.salvar(sessao)

        ativa = repo.buscar_ativa_por_usuario(usuario.id)
        assert ativa is not None
        assert ativa.id == sessao.id

        # Quando a sessão é concluída, não há mais sessão ativa
        sessao.concluir(relogio=lambda: sessao.fim_previsto)
        repo.salvar(sessao)

        assert repo.buscar_ativa_por_usuario(usuario.id) is None

    def test_buscar_por_id_inexistente_retorna_none(self):
        repo = RepositorioSessaoDjango()
        assert repo.buscar_por_id(uuid4()) is None
