"""Sequência de dias e conquistas do estudante (#32)."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo

from app.domain.rede_neural import RedeNeural

# Os dias são contados no horário de Brasília: uma sessão concluída às 22h conta para
# aquele dia, e não para o seguinte, como seria em UTC. O Brasil não tem horário de
# verão desde 2019, então o deslocamento fixo basta.
FUSO_DOS_DIAS = timezone(timedelta(hours=-3), "Brasília")


@dataclass(frozen=True)
class Sequencia:
    """Dias seguidos com pelo menos uma sessão concluída."""

    atual: int = 0
    recorde: int = 0


def calcular_sequencia(dias: Iterable[date], hoje: date) -> Sequencia:
    """A sequência atual e a maior de todas, a partir dos dias com sessão concluída.

    A atual vai até hoje ou, se ainda não houve sessão hoje, até ontem: ela só se
    perde quando um dia inteiro passa sem sessão concluída.
    """
    recorde = seguidos = 0
    anterior: date | None = None
    for dia in sorted(set(dias)):
        emendou = anterior is not None and dia - anterior == timedelta(days=1)
        seguidos = seguidos + 1 if emendou else 1
        recorde = max(recorde, seguidos)
        anterior = dia
    em_dia = anterior is not None and hoje - anterior <= timedelta(days=1)
    return Sequencia(atual=seguidos if em_dia else 0, recorde=recorde)


@dataclass(frozen=True)
class ResumoFoco:
    """O que as regras de conquista olham: o foco do estudante até agora."""

    neuronios_vivos: int = 0
    minutos_focados: int = 0
    maior_sessao_minutos: int = 0
    sinapses: int = 0
    sequencia: Sequencia = field(default_factory=Sequencia)

    @classmethod
    def da_rede(
        cls, rede: RedeNeural, instante: datetime, fuso: tzinfo = FUSO_DOS_DIAS
    ) -> "ResumoFoco":
        """Monta o resumo a partir da rede neural do estudante.

        Cada neurônio vivo é uma sessão concluída, com a duração dela e criado no
        instante da conclusão (`FabricaNeuronio`), então a rede tem tudo de que as
        regras precisam. Os neurônios mortos (sessões podadas) não contam.
        """
        vivos = rede.vivos
        dias = (n.criado_em.astimezone(fuso).date() for n in vivos)
        return cls(
            neuronios_vivos=len(vivos),
            minutos_focados=sum(n.duracao.minutos for n in vivos),
            maior_sessao_minutos=max((n.duracao.minutos for n in vivos), default=0),
            sinapses=len(rede.sinapses),
            sequencia=calcular_sequencia(dias, instante.astimezone(fuso).date()),
        )


class RegraConquista(ABC):
    """Uma conquista e o que é preciso para desbloqueá-la (#32).

    Cada conquista é uma subclasse, que só diz o que medir no resumo (`medir`). A
    comparação com a meta é igual para todas e fica aqui (Template Method). Quem
    avalia (`ConquistaService`) trata todas as regras do mesmo jeito, então uma
    conquista nova é só uma classe nova no catálogo, sem um `if` para cada uma.
    """

    def __init__(
        self, codigo: str, nome: str, descricao: str, *, meta: int, unidade: str
    ):
        if meta < 1:
            raise ValueError("A meta da conquista precisa ser de 1 em diante.")
        self._codigo = codigo
        self._nome = nome
        self._descricao = descricao
        self._meta = meta
        self._unidade = unidade

    @property
    def codigo(self) -> str:
        """Identificador estável, guardado no banco e usado pela API."""
        return self._codigo

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def descricao(self) -> str:
        """Como desbloquear: a dica mostrada enquanto a conquista está bloqueada."""
        return self._descricao

    @property
    def meta(self) -> int:
        return self._meta

    @property
    def unidade(self) -> str:
        """Em que a meta e o progresso são contados (ex.: `minutos`, `dias`)."""
        return self._unidade

    @abstractmethod
    def medir(self, resumo: ResumoFoco) -> int:
        """O valor que a regra acompanha, na mesma unidade da meta."""

    def progresso(self, resumo: ResumoFoco) -> int:
        """Quanto já foi feito, de 0 até a meta (o que passa da meta não conta)."""
        return min(self.medir(resumo), self._meta)

    def cumprida(self, resumo: ResumoFoco) -> bool:
        return self.medir(resumo) >= self._meta

    def __repr__(self) -> str:
        return f"{type(self).__name__}(codigo={self._codigo!r})"


class PrimeiroNeuronio(RegraConquista):
    """A primeira sessão concluída, que forma o primeiro neurônio vivo."""

    def __init__(self):
        super().__init__(
            "primeiro_neuronio",
            "Primeiro neurônio",
            "Conclua sua primeira sessão de foco.",
            meta=1,
            unidade="neurônios",
        )

    def medir(self, resumo: ResumoFoco) -> int:
        return resumo.neuronios_vivos


class HorasFocadas(RegraConquista):
    """Horas somadas de todas as sessões concluídas."""

    def __init__(self, horas: int = 10):
        super().__init__(
            f"horas_focadas_{horas}",
            f"{horas} horas focadas",
            f"Some {horas} horas em sessões de foco concluídas.",
            meta=horas * 60,
            unidade="minutos",
        )

    def medir(self, resumo: ResumoFoco) -> int:
        return resumo.minutos_focados


class DiasSeguidos(RegraConquista):
    """Dias seguidos com pelo menos uma sessão concluída."""

    def __init__(self, dias: int = 7):
        super().__init__(
            f"dias_seguidos_{dias}",
            f"{dias} dias seguidos",
            f"Conclua pelo menos uma sessão por dia, {dias} dias seguidos.",
            meta=dias,
            unidade="dias",
        )

    def medir(self, resumo: ResumoFoco) -> int:
        # A maior sequência, e não a atual: quem já fez 7 dias seguidos cumpriu a
        # meta, mesmo que a sequência tenha sido quebrada depois.
        return resumo.sequencia.recorde


class SinapsesFormadas(RegraConquista):
    """Sinapses na rede do estudante."""

    def __init__(self, quantidade: int = 100):
        super().__init__(
            f"sinapses_{quantidade}",
            f"{quantidade} sinapses",
            f"Forme {quantidade} sinapses na sua rede neural.",
            meta=quantidade,
            unidade="sinapses",
        )

    def medir(self, resumo: ResumoFoco) -> int:
        return resumo.sinapses


class SessaoLongaSemPoda(RegraConquista):
    """Uma sessão longa concluída, sem ser podada no caminho."""

    def __init__(self, minutos: int = 120):
        duracao = f"{minutos // 60} h" if minutos % 60 == 0 else f"{minutos} min"
        super().__init__(
            f"sessao_sem_poda_{minutos}",
            f"{duracao} sem poda",
            f"Conclua uma sessão de {duracao} sem ser podado.",
            meta=minutos,
            unidade="minutos",
        )

    def medir(self, resumo: ResumoFoco) -> int:
        return resumo.maior_sessao_minutos


# As conquistas do Synapse, na ordem em que aparecem para o estudante.
CATALOGO_CONQUISTAS: tuple[RegraConquista, ...] = (
    PrimeiroNeuronio(),
    HorasFocadas(10),
    DiasSeguidos(7),
    SinapsesFormadas(100),
    SessaoLongaSemPoda(120),
)
