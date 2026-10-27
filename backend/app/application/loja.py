from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.carteira import Carteira, atp_da_sessao
from app.domain.entidades.neuronio import FabricaNeuronio, Neuronio, TipoNeuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.excecoes import TipoNaoEncontrado
from app.domain.loja import CATALOGO_LOJA, ItemLoja, item_por_codigo
from app.domain.repositorios import RepositorioCarteira
from app.domain.tempo import agora


@dataclass(frozen=True)
class SituacaoItem:
    """Um item do catálogo, do ponto de vista de um estudante."""

    item: ItemLoja
    desbloqueado: bool
    em_uso: bool


@dataclass(frozen=True)
class VitrineLoja:
    """O saldo de ATP e todos os itens da loja, na ordem do catálogo."""

    saldo: int
    itens: list[SituacaoItem]


class LojaService:
    """Casos de uso da loja de ATP (#34): ganhar ATP, comprar e escolher tipos de
    neurônio.

    O crédito de cada sessão concluída vem do observador `CreditadorATP` (#24). As
    regras de saldo e de posse ficam na `Carteira`; aqui só se carrega, chama e grava.
    """

    def __init__(
        self,
        carteiras: RepositorioCarteira,
        catalogo: Iterable[ItemLoja] = CATALOGO_LOJA,
        relogio: Callable[[], datetime] = agora,
    ):
        self._carteiras = carteiras
        self._catalogo = tuple(catalogo)
        self._relogio = relogio
        codigos = [item.codigo for item in self._catalogo]
        if len(set(codigos)) != len(codigos):
            raise ValueError("Cada item do catálogo precisa de um código próprio.")
        originais = [item.forma for item in self._catalogo if item.gratuito]
        if len(set(originais)) != len(originais) or {
            item.forma for item in self._catalogo
        } - set(originais):
            raise ValueError("Cada forma precisa de exatamente um tipo gratuito.")

    def consultar(self, usuario_id: UUID) -> VitrineLoja:
        return self._vitrine(self._carteiras.carregar(usuario_id))

    def comprar(self, usuario_id: UUID, codigo: str) -> VitrineLoja:
        item = self._item(codigo)
        carteira = self._carteiras.carregar(usuario_id, para_alterar=True)
        carteira.comprar(item, self._relogio())
        self._carteiras.salvar(carteira)
        return self._vitrine(carteira)

    def usar(self, usuario_id: UUID, codigo: str) -> VitrineLoja:
        item = self._item(codigo)
        carteira = self._carteiras.carregar(usuario_id, para_alterar=True)
        carteira.usar(item)
        self._carteiras.salvar(carteira)
        return self._vitrine(carteira)

    def creditar_sessao(self, usuario_id: UUID, duracao_minutos: int) -> int:
        """Credita o ATP de uma sessão concluída e devolve a quantia."""
        quantia = atp_da_sessao(duracao_minutos)
        carteira = self._carteiras.carregar(usuario_id, para_alterar=True)
        carteira.creditar(quantia)
        self._carteiras.salvar(carteira)
        return quantia

    def tipos_em_uso(self, usuario_id: UUID) -> tuple[TipoNeuronio, ...]:
        return self._carteiras.carregar(usuario_id).tipos_em_uso(self._catalogo)

    def _item(self, codigo: str) -> ItemLoja:
        item = item_por_codigo(codigo, self._catalogo)
        if item is None:
            raise TipoNaoEncontrado("Tipo de neurônio não encontrado na loja.")
        return item

    def _vitrine(self, carteira: Carteira) -> VitrineLoja:
        em_uso = carteira.tipos_em_uso(self._catalogo)
        return VitrineLoja(
            carteira.saldo,
            [
                SituacaoItem(item, carteira.possui(item), item.tipo in em_uso)
                for item in self._catalogo
            ],
        )


class FabricaDoEstudante:
    """Cria o neurônio com os tipos que o estudante escolheu na loja (#34).

    Para o `SessaoService`, é uma fábrica como outra qualquer (`criar(sessao)`): ela
    monta uma `FabricaNeuronio` (#22) com os tipos em uso do dono da sessão e repassa
    a chamada. A faixa de duração continua decidindo a forma do neurônio.
    """

    def __init__(self, loja: LojaService):
        self._loja = loja

    def criar(self, sessao: SessaoFoco) -> Neuronio:
        tipos = self._loja.tipos_em_uso(sessao.usuario_id)
        return FabricaNeuronio(tipos).criar(sessao)
