from abc import ABC, abstractmethod

from app.domain.entidades.usuario import Usuario
from app.domain.excecoes import EmailJaCadastrado
from app.domain.repositorios import RepositorioUsuario


class ServicoSenhas(ABC):
    """Regras e armazenamento de senhas.

    O domínio não guarda senha (o `Usuario` não tem esse atributo): validar e gerar
    o hash é papel da infraestrutura, que implementa esta interface com o Django.
    """

    @abstractmethod
    def validar(self, senha: str, usuario: Usuario) -> None:
        """Lança `SenhaInvalida` se a senha não atender às regras de segurança."""

    @abstractmethod
    def definir(self, usuario: Usuario, senha: str) -> None:
        """Guarda o hash da senha de um usuário já salvo no repositório."""


class CadastroUsuario:
    """Caso de uso: cadastrar um estudante com nome, e-mail e senha (issue #14).

    Depende só de interfaces (`RepositorioUsuario` e `ServicoSenhas`), então é
    testado com implementações em memória, sem banco e sem Django.
    """

    def __init__(self, repositorio: RepositorioUsuario, senhas: ServicoSenhas):
        self._repositorio = repositorio
        self._senhas = senhas

    def executar(self, nome: str, email: str, senha: str) -> Usuario:
        # A entidade valida e normaliza nome e e-mail (NomeInvalido, EmailInvalido).
        usuario = Usuario(nome, email)
        if self._repositorio.existe_com_email(usuario.email):
            raise EmailJaCadastrado(
                "E-mail já cadastrado. Tente fazer login ou use outro e-mail."
            )
        self._senhas.validar(senha, usuario)

        self._repositorio.salvar(usuario)
        self._senhas.definir(usuario, senha)
        return usuario
