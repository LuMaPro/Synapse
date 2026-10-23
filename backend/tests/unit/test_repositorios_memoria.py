from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entidades.materia import Materia
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.entidades.usuario import Usuario
from app.domain.repositorios import (
    RepositorioMateria,
    RepositorioSessao,
    RepositorioUsuario,
)
from tests.repositorios import (
    RepositorioMateriaMemoria,
    RepositorioSessaoMemoria,
    RepositorioUsuarioMemoria,
)


def test_repositorio_usuario_memoria_implementa_interface():
    repo = RepositorioUsuarioMemoria()
    assert isinstance(repo, RepositorioUsuario)


def test_repositorio_usuario_memoria_operacoes_basicas():
    repo = RepositorioUsuarioMemoria()
    usuario = Usuario(nome="Lucas", email="lucas@synapse.com")

    assert repo.buscar_por_id(usuario.id) is None
    assert repo.buscar_por_email("lucas@synapse.com") is None
    assert not repo.existe_com_email("lucas@synapse.com")
    assert len(repo) == 0

    repo.salvar(usuario)

    assert repo.buscar_por_id(usuario.id) == usuario
    assert repo.buscar_por_email("LUCAS@synapse.com") == usuario
    assert repo.existe_com_email("lucas@synapse.com")
    assert len(repo) == 1

    # Atualização
    usuario.nome = "Lucas Santos"
    repo.salvar(usuario)
    assert repo.buscar_por_id(usuario.id).nome == "Lucas Santos"

    repo.limpar()
    assert len(repo) == 0
    assert repo.buscar_por_id(usuario.id) is None


def test_repositorio_sessao_memoria_implementa_interface():
    repo = RepositorioSessaoMemoria()
    assert isinstance(repo, RepositorioSessao)


def test_repositorio_sessao_memoria_operacoes_basicas():
    repo = RepositorioSessaoMemoria()
    usuario_id = uuid4()
    outro_usuario_id = uuid4()

    agora = datetime.now(UTC)
    sessao1 = SessaoFoco(
        usuario_id=usuario_id,
        duracao_minutos=25,
        inicio=agora - timedelta(hours=2),
    )
    sessao2 = SessaoFoco(
        usuario_id=usuario_id,
        duracao_minutos=50,
        inicio=agora - timedelta(hours=1),
    )
    sessao_outro = SessaoFoco(
        usuario_id=outro_usuario_id,
        duracao_minutos=30,
        inicio=agora,
    )

    repo.salvar(sessao1)
    repo.salvar(sessao2)
    repo.salvar(sessao_outro)

    assert len(repo) == 3
    assert repo.buscar_por_id(sessao1.id) == sessao1
    assert repo.buscar_por_id(uuid4()) is None

    # Listar por usuário deve ordenar por início decrescente
    sessoes_usuario = repo.listar_por_usuario(usuario_id)
    assert sessoes_usuario == [sessao2, sessao1]

    # Sessão ativa
    assert repo.buscar_ativa_por_usuario(usuario_id) in (sessao1, sessao2)

    # Concluir sessões
    sessao1.concluir(relogio=lambda: sessao1.fim_previsto)
    sessao2.concluir(relogio=lambda: sessao2.fim_previsto)
    repo.salvar(sessao1)
    repo.salvar(sessao2)

    assert repo.buscar_ativa_por_usuario(usuario_id) is None

    repo.limpar()
    assert len(repo) == 0


def test_repositorio_materia_memoria_implementa_interface():
    repo = RepositorioMateriaMemoria()
    assert isinstance(repo, RepositorioMateria)


def test_repositorio_materia_memoria_operacoes_basicas():
    repo = RepositorioMateriaMemoria()
    usuario_id = uuid4()
    outro_usuario_id = uuid4()

    materia1 = Materia(usuario_id=usuario_id, nome="POO", cor="#3EE6E0")
    materia2 = Materia(usuario_id=usuario_id, nome="Cálculo", cor="#8B7BFF")
    materia_outro = Materia(usuario_id=outro_usuario_id, nome="Física", cor="#5BE49B")

    assert repo.buscar_por_id(materia1.id) is None
    assert repo.buscar_por_usuario_e_id(usuario_id, materia1.id) is None
    assert len(repo) == 0

    repo.salvar(materia1)
    repo.salvar(materia2)
    repo.salvar(materia_outro)

    assert len(repo) == 3
    assert repo.buscar_por_id(materia1.id) == materia1
    assert repo.buscar_por_usuario_e_id(usuario_id, materia1.id) == materia1
    assert repo.buscar_por_usuario_e_id(outro_usuario_id, materia1.id) is None

    # Listar por usuário ordenado por nome (Cálculo, POO)
    materias_usuario = repo.listar_por_usuario(usuario_id)
    assert materias_usuario == [materia2, materia1]

    # Checagem de existência por nome
    assert repo.existe_com_nome(usuario_id, "poo")
    assert repo.existe_com_nome(usuario_id, "POO")
    assert repo.existe_com_nome(usuario_id, "poo", ignorar_id=materia1.id) is False
    assert repo.existe_com_nome(usuario_id, "Física") is False

    # Remoção
    repo.remover(materia1.id)
    assert len(repo) == 2
    assert repo.buscar_por_id(materia1.id) is None

    repo.limpar()
    assert len(repo) == 0

