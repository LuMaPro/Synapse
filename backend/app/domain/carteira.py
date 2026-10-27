"""A carteira de ATP do estudante (#34)."""

from collections.abc import Iterable, Mapping
from datetime import datetime
from uuid import UUID

from app.domain.entidades.neuronio import TipoNeuronio
from app.domain.excecoes import SaldoInsuficiente, TipoBloqueado, TipoJaDesbloqueado
from app.domain.loja import ItemLoja
from app.domain.tempo import exigir_fuso

ATP_POR_MINUTO = 1


def atp_da_sessao(duracao_minutos: int) -> int:
    """ATP que uma sessão concluída rende: proporcional à duração, 1 por minuto
    (uma sessão de 45 min rende 45 ATP, como no protótipo)."""
    return duracao_minutos * ATP_POR_MINUTO


class Carteira:
    """Agregado com o ATP do estudante e os tipos de neurônio que ele desbloqueou e
    escolheu na loja (#34).

    É a única porta de entrada para gastar ATP, então as regras valem sempre: o saldo
    nunca fica negativo, um tipo é comprado uma vez só e só se usa o que já é seu. Os
    tipos originais (preço 0) são de todos e ficam em uso enquanto o estudante não
    escolhe uma variação da mesma forma.
    """

    def __init__(
        self,
        usuario_id: UUID,
        saldo: int = 0,
        desbloqueados: Mapping[str, datetime] | None = None,
        em_uso: Mapping[str, str] | None = None,
    ):
        if saldo < 0:
            raise ValueError("O saldo de ATP não pode ser negativo.")
        self._usuario_id = usuario_id
        self._saldo = saldo
        self._desbloqueados = {
            codigo: exigir_fuso(quando, "desbloqueado_em")
            for codigo, quando in (desbloqueados or {}).items()
        }
        # Forma (granular, piramidal, purkinje) -> código da variação escolhida.
        self._em_uso = dict(em_uso or {})

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def saldo(self) -> int:
        return self._saldo

    @property
    def desbloqueados(self) -> dict[str, datetime]:
        """Os tipos comprados (código -> quando). Os originais não entram aqui."""
        return dict(self._desbloqueados)

    @property
    def em_uso(self) -> dict[str, str]:
        """As variações escolhidas, por forma. Forma ausente usa o tipo original."""
        return dict(self._em_uso)

    def creditar(self, quantidade: int) -> None:
        if quantidade < 1:
            raise ValueError("O crédito de ATP precisa ser de 1 em diante.")
        self._saldo += quantidade

    def possui(self, item: ItemLoja) -> bool:
        return item.gratuito or item.codigo in self._desbloqueados

    def comprar(self, item: ItemLoja, instante: datetime) -> None:
        """Desconta o preço, desbloqueia o tipo e já passa a usá-lo."""
        if self.possui(item):
            raise TipoJaDesbloqueado(f"Você já tem o {item.tipo.nome}.")
        if self._saldo < item.preco:
            falta = item.preco - self._saldo
            raise SaldoInsuficiente(
                f"Faltam {falta} ATP para comprar o {item.tipo.nome}."
            )
        self._saldo -= item.preco
        self._desbloqueados[item.codigo] = exigir_fuso(instante, "instante")
        self.usar(item)

    def usar(self, item: ItemLoja) -> None:
        """Passa a criar os neurônios da forma do item com este tipo."""
        if not self.possui(item):
            raise TipoBloqueado(f"Compre o {item.tipo.nome} na loja antes de usá-lo.")
        if item.gratuito:
            self._em_uso.pop(item.forma, None)
        else:
            self._em_uso[item.forma] = item.codigo

    def tipos_em_uso(self, catalogo: Iterable[ItemLoja]) -> tuple[TipoNeuronio, ...]:
        """Um tipo por forma: a variação escolhida ou, sem escolha, o original.

        Uma escolha que saiu do catálogo volta para o original, então sempre há um
        tipo para cada faixa de duração.
        """
        itens = tuple(catalogo)
        por_codigo = {item.codigo: item for item in itens}
        tipos = []
        for original in (item for item in itens if item.gratuito):
            escolhido = por_codigo.get(self._em_uso.get(original.forma, ""))
            usar_escolhido = escolhido is not None and self.possui(escolhido)
            tipos.append(escolhido.tipo if usar_escolhido else original.tipo)
        return tuple(tipos)

    def __repr__(self) -> str:
        return f"Carteira(saldo={self._saldo})"
