"""A carteira de ATP do estudante (#34)."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from app.domain.excecoes import CorJaDesbloqueada, SaldoInsuficiente
from app.domain.loja import CorLoja
from app.domain.tempo import exigir_fuso

ATP_POR_MINUTO = 1


def atp_da_sessao(duracao_minutos: int) -> int:
    """ATP que uma sessão concluída rende: proporcional à duração, 1 por minuto
    (uma sessão de 45 min rende 45 ATP, como no protótipo)."""
    return duracao_minutos * ATP_POR_MINUTO


class Carteira:
    """Agregado com o ATP do estudante e as cores que ele comprou na loja (#34).

    É a única porta de entrada para gastar ATP, então as regras valem sempre: o saldo
    nunca fica negativo e uma cor é comprada uma vez só. As cores gratuitas são de
    todos e não passam por aqui.
    """

    def __init__(
        self,
        usuario_id: UUID,
        saldo: int = 0,
        desbloqueadas: Mapping[str, datetime] | None = None,
    ):
        if saldo < 0:
            raise ValueError("O saldo de ATP não pode ser negativo.")
        self._usuario_id = usuario_id
        self._saldo = saldo
        self._desbloqueadas = {
            codigo: exigir_fuso(quando, "desbloqueada_em")
            for codigo, quando in (desbloqueadas or {}).items()
        }

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def saldo(self) -> int:
        return self._saldo

    @property
    def desbloqueadas(self) -> dict[str, datetime]:
        """As cores compradas (código -> quando). As gratuitas não entram aqui."""
        return dict(self._desbloqueadas)

    def creditar(self, quantidade: int) -> None:
        if quantidade < 1:
            raise ValueError("O crédito de ATP precisa ser de 1 em diante.")
        self._saldo += quantidade

    def possui(self, cor: CorLoja) -> bool:
        return cor.gratuita or cor.codigo in self._desbloqueadas

    def comprar(self, cor: CorLoja, instante: datetime) -> None:
        """Desconta o preço e desbloqueia a cor para as matérias do estudante."""
        if self.possui(cor):
            raise CorJaDesbloqueada(f"A cor {cor.nome} já é sua.")
        if self._saldo < cor.preco:
            falta = cor.preco - self._saldo
            raise SaldoInsuficiente(
                f"Faltam {falta} ATP para comprar a cor {cor.nome}."
            )
        self._saldo -= cor.preco
        self._desbloqueadas[cor.codigo] = exigir_fuso(instante, "instante")

    def __repr__(self) -> str:
        return f"Carteira(saldo={self._saldo})"
