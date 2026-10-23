import re
from datetime import datetime
from uuid import UUID

from app.domain.entidades.base import Entidade
from app.domain.excecoes import CorInvalida, NomeMateriaInvalido
from app.domain.tempo import agora, exigir_fuso

_HEX_COR = re.compile(r"^#[0-9a-fA-F]{6}$")


class Materia(Entidade):
    """Matéria (etiqueta) de estudo pertencente a um estudante (#27).

    Define nome e cor para organizar as sessões de foco e colorir os
    neurônios correspondentes na rede neural.
    """

    NOME_MAX = 100

    def __init__(
        self,
        usuario_id: UUID,
        nome: str,
        cor: str,
        *,
        id: UUID | None = None,
        criada_em: datetime | None = None,
    ):
        super().__init__(id)
        if not isinstance(usuario_id, UUID):
            raise TypeError("usuario_id deve ser um UUID.")
        self._usuario_id = usuario_id
        self._nome = self._validar_nome(nome)
        self._cor = self._normalizar_cor(cor)
        self._criada_em = (
            exigir_fuso(criada_em, "criada_em") if criada_em is not None else agora()
        )

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        self._nome = self._validar_nome(valor)

    @property
    def cor(self) -> str:
        return self._cor

    @cor.setter
    def cor(self, valor: str) -> None:
        self._cor = self._normalizar_cor(valor)

    @property
    def criada_em(self) -> datetime:
        return self._criada_em

    def atualizar(self, nome: str | None = None, cor: str | None = None) -> None:
        if nome is not None:
            self.nome = nome
        if cor is not None:
            self.cor = cor

    def __repr__(self) -> str:
        return f"Materia(id={self.id}, nome={self._nome!r}, cor={self._cor!r})"

    @classmethod
    def _validar_nome(cls, nome: str) -> str:
        if not isinstance(nome, str) or not nome.strip():
            raise NomeMateriaInvalido("O nome da matéria é obrigatório.")
        nome = nome.strip()
        if len(nome) > cls.NOME_MAX:
            raise NomeMateriaInvalido(
                f"O nome da matéria pode ter no máximo {cls.NOME_MAX} caracteres."
            )
        return nome

    @classmethod
    def _normalizar_cor(cls, cor: str) -> str:
        if not isinstance(cor, str) or not cor.strip():
            raise CorInvalida("A cor da matéria é obrigatória.")
        cor = cor.strip().upper()
        if not _HEX_COR.match(cor):
            raise CorInvalida(f"Cor inválida: {cor!r}. Use o formato #RRGGBB.")
        return cor
