import pytest

from app.application.cadastro import CadastroUsuario, ServicoSenhas
from app.domain.entidades.usuario import Usuario
from app.domain.excecoes import (
    EmailInvalido,
    EmailJaCadastrado,
    NomeInvalido,
    SenhaInvalida,
)
from tests.repositorios import RepositorioUsuarioMemoria


class ServicoSenhasFalso(ServicoSenhas):
    """Recusa senhas com menos de 8 caracteres e guarda as senhas em texto, só para
    os testes conferirem o que foi definido (a implementação real guarda o hash)."""

    def __init__(self):
        self.senhas: dict = {}

    def validar(self, senha: str, usuario: Usuario) -> None:
        if len(senha) < 8:
            raise SenhaInvalida("A senha precisa ter pelo menos 8 caracteres.")

    def definir(self, usuario: Usuario, senha: str) -> None:
        self.senhas[usuario.id] = senha


@pytest.fixture
def repositorio():
    return RepositorioUsuarioMemoria()


@pytest.fixture
def senhas():
    return ServicoSenhasFalso()


@pytest.fixture
def cadastro(repositorio, senhas):
    return CadastroUsuario(repositorio, senhas)


def test_cadastra_usuario_normalizado_e_define_a_senha(cadastro, repositorio, senhas):
    usuario = cadastro.executar("  Julia  ", " Julia@Exemplo.COM ", "senha-segura-123")

    assert usuario.nome == "Julia"
    assert usuario.email == "julia@exemplo.com"
    assert repositorio.buscar_por_id(usuario.id) == usuario
    assert senhas.senhas[usuario.id] == "senha-segura-123"


def test_recusa_email_ja_cadastrado_sem_diferenciar_maiusculas(cadastro, repositorio):
    cadastro.executar("Julia", "julia@exemplo.com", "senha-segura-123")

    with pytest.raises(EmailJaCadastrado):
        cadastro.executar("Outra", "JULIA@exemplo.com", "outra-senha-123")

    assert len(repositorio) == 1


def test_senha_invalida_nao_salva_nada(cadastro, repositorio, senhas):
    with pytest.raises(SenhaInvalida):
        cadastro.executar("Julia", "julia@exemplo.com", "curta")

    assert len(repositorio) == 0
    assert senhas.senhas == {}


@pytest.mark.parametrize(
    ("nome", "email", "excecao"),
    [("   ", "julia@exemplo.com", NomeInvalido), ("Julia", "julia@", EmailInvalido)],
)
def test_usa_as_regras_da_entidade_para_nome_e_email(cadastro, nome, email, excecao):
    with pytest.raises(excecao):
        cadastro.executar(nome, email, "senha-segura-123")
