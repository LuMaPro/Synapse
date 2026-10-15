import re
from datetime import datetime
from uuid import UUID

from app.domain.entidades.base import Entidade
from app.domain.excecoes import EmailInvalido, NomeInvalido
from app.domain.politica_interrupcao import ModoEstrito, PoliticaInterrupcao
from app.domain.tempo import agora, exigir_fuso

_FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Usuario(Entidade):
    """Estudante que usa o Synapse.

    Não guarda senha: o hash fica com o Django, na camada de infraestrutura.
    """

    NOME_MAX = 150
    EMAIL_MAX = 254

    def __init__(
        self,
        nome: str,
        email: str,
        *,
        id: UUID | None = None,
        criado_em: datetime | None = None,
        politica_padrao: PoliticaInterrupcao | None = None,
    ):
        super().__init__(id)
        self._nome = self._validar_nome(nome)
        self._email = self._normalizar_email(email)
        self._criado_em = (
            exigir_fuso(criado_em, "criado_em") if criado_em is not None else agora()
        )
        self._politica_padrao = politica_padrao or ModoEstrito()

    @property
    def politica_padrao(self) -> PoliticaInterrupcao:
        return self._politica_padrao

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        self._nome = self._validar_nome(valor)

    @property
    def email(self) -> str:
        return self._email

    @property
    def criado_em(self) -> datetime:
        return self._criado_em

    def __repr__(self) -> str:
        return f"Usuario(id={self.id}, email={self._email!r})"

    @classmethod
    def _validar_nome(cls, nome: str) -> str:
        if not isinstance(nome, str) or not nome.strip():
            raise NomeInvalido("O nome é obrigatório.")
        nome = nome.strip()
        if len(nome) > cls.NOME_MAX:
            raise NomeInvalido(f"O nome pode ter no máximo {cls.NOME_MAX} caracteres.")
        return nome

    @classmethod
    def _normalizar_email(cls, email: str) -> str:
        """Guarda o e-mail em minúsculas, como o UsuarioModel faz no banco."""
        if not isinstance(email, str) or not email.strip():
            raise EmailInvalido("O e-mail é obrigatório.")
        email = email.strip().lower()
        if len(email) > cls.EMAIL_MAX or not _FORMATO_EMAIL.match(email):
            raise EmailInvalido(f"E-mail inválido: {email!r}.")
        return email
