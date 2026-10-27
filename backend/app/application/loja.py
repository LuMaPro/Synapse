from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.carteira import Carteira, atp_da_sessao
from app.domain.excecoes import CorBloqueada, CorInvalida, CorNaoEncontrada
from app.domain.loja import CATALOGO_CORES, CorLoja, cor_por_codigo, cor_por_hex
from app.domain.repositorios import RepositorioCarteira
from app.domain.tempo import agora


@dataclass(frozen=True)
class SituacaoCor:
    """Uma cor do catálogo, do ponto de vista de um estudante."""

    cor: CorLoja
    desbloqueada: bool


@dataclass(frozen=True)
class VitrineLoja:
    """O saldo de ATP e todas as cores, na ordem do catálogo (as gratuitas antes)."""

    saldo: int
    cores: list[SituacaoCor]


class LojaService:
    """Casos de uso da loja de ATP (#34): ganhar ATP e comprar cores para as matérias.

    O crédito de cada sessão concluída vem do observador `CreditadorATP` (#24). As
    regras de saldo e de posse ficam na `Carteira`; aqui só se carrega, chama e grava.
    """

    def __init__(
        self,
        carteiras: RepositorioCarteira,
        catalogo: Iterable[CorLoja] = CATALOGO_CORES,
        relogio: Callable[[], datetime] = agora,
    ):
        self._carteiras = carteiras
        self._catalogo = tuple(catalogo)
        self._relogio = relogio
        for campo in ("codigo", "hex"):
            valores = [getattr(cor, campo) for cor in self._catalogo]
            if len(set(valores)) != len(valores):
                raise ValueError(f"Cada cor do catálogo precisa de um {campo} próprio.")

    def consultar(self, usuario_id: UUID) -> VitrineLoja:
        return self._vitrine(self._carteiras.carregar(usuario_id))

    def comprar(self, usuario_id: UUID, codigo: str) -> VitrineLoja:
        cor = cor_por_codigo(codigo, self._catalogo)
        if cor is None:
            raise CorNaoEncontrada("Cor não encontrada na loja.")
        carteira = self._carteiras.carregar(usuario_id, para_alterar=True)
        carteira.comprar(cor, self._relogio())
        self._carteiras.salvar(carteira)
        return self._vitrine(carteira)

    def creditar_sessao(self, usuario_id: UUID, duracao_minutos: int) -> int:
        """Credita o ATP de uma sessão concluída e devolve a quantia."""
        quantia = atp_da_sessao(duracao_minutos)
        carteira = self._carteiras.carregar(usuario_id, para_alterar=True)
        carteira.creditar(quantia)
        self._carteiras.salvar(carteira)
        return quantia

    def exigir_cor_disponivel(self, usuario_id: UUID, hex_: str) -> CorLoja:
        """A cor do catálogo com este hexadecimal, se o estudante puder usá-la numa
        matéria: gratuita ou já comprada."""
        cor = cor_por_hex(hex_, self._catalogo)
        if cor is None:
            raise CorInvalida("Escolha uma das cores da paleta.")
        if not cor.gratuita and not self._carteiras.carregar(usuario_id).possui(cor):
            raise CorBloqueada(f"Compre a cor {cor.nome} na loja para usá-la.")
        return cor

    def _vitrine(self, carteira: Carteira) -> VitrineLoja:
        return VitrineLoja(
            carteira.saldo,
            [SituacaoCor(cor, carteira.possui(cor)) for cor in self._catalogo],
        )
