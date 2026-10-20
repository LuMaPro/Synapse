from bisect import insort
from collections.abc import Iterable
from uuid import UUID

from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sinapse import Sinapse
from app.domain.excecoes import RedeNeuralInvalida, SinapseInvalida
from app.domain.formacao_sinapses import (
    RegraFormacaoSinapses,
    RegraRecentesEMesmaMateria,
)


class RedeNeural:
    """Agregado com a rede neural de um estudante: os neurônios e as sinapses entre
    eles (#23).

    É a única porta de entrada para mudar a rede. `adicionar` pergunta à regra de
    formação (Strategy) a quem o neurônio novo se liga e garante as invariantes,
    valha a regra que valer:

    - todos os neurônios são do mesmo estudante, e cada sessão aparece uma vez só;
    - nenhuma sinapse liga um neurônio a ele mesmo nem repete uma ligação;
    - poda sináptica: neurônio morto (de sessão podada) fica na rede, mas sem
      sinapses, e não conta para as ligações dos próximos.

    Os neurônios ficam em ordem cronológica. Um neurônio pode chegar com data
    anterior à do último (ex.: uma poda vale a partir da saída da tela, e a sessão
    abandonada é podada no limite de duração + 5 min); ele entra na posição certa e
    a regra só o liga aos que já existiam antes dele.

    Neurônios e sinapses não mudam depois de criados, então a rede só cresce. O que
    foi adicionado desde o carregamento fica em `neuronios_novos` e `sinapses_novas`
    para o repositório gravar.
    """

    def __init__(
        self,
        usuario_id: UUID,
        neuronios: Iterable[Neuronio] = (),
        sinapses: Iterable[Sinapse] = (),
        *,
        regra: RegraFormacaoSinapses | None = None,
    ):
        self._usuario_id = usuario_id
        self._regra = regra if regra is not None else RegraRecentesEMesmaMateria()
        self._neuronios: dict[UUID, Neuronio] = {}
        self._em_ordem: list[Neuronio] = []
        self._sessoes: set[UUID] = set()
        self._sinapses: list[Sinapse] = []
        self._sinapses_por_neuronio: dict[UUID, list[Sinapse]] = {}
        self._pares: set[frozenset[UUID]] = set()

        # O que vem do banco passa pelas mesmas regras de quem é adicionado agora.
        for neuronio in neuronios:
            self._exigir_admissivel(neuronio)
            self._incluir_neuronio(neuronio)
        for sinapse in sinapses:
            self._exigir_ligavel(sinapse)
            self._incluir_sinapse(sinapse)

        self._neuronios_novos: list[Neuronio] = []
        self._sinapses_novas: list[Sinapse] = []

    @property
    def usuario_id(self) -> UUID:
        return self._usuario_id

    @property
    def neuronios(self) -> list[Neuronio]:
        """Todos os neurônios, do mais antigo para o mais recente."""
        return list(self._em_ordem)

    @property
    def vivos(self) -> list[Neuronio]:
        """Os neurônios vivos, do mais antigo para o mais recente."""
        return [n for n in self._em_ordem if n.vivo]

    @property
    def sinapses(self) -> list[Sinapse]:
        return list(self._sinapses)

    @property
    def neuronios_novos(self) -> list[Neuronio]:
        return list(self._neuronios_novos)

    @property
    def sinapses_novas(self) -> list[Sinapse]:
        return list(self._sinapses_novas)

    def neuronio(self, neuronio_id: UUID) -> Neuronio | None:
        return self._neuronios.get(neuronio_id)

    def sinapses_de(self, neuronio_id: UUID) -> list[Sinapse]:
        """As sinapses que chegam ao neurônio ou saem dele."""
        return list(self._sinapses_por_neuronio.get(neuronio_id, []))

    def adicionar(self, neuronio: Neuronio) -> list[Sinapse]:
        """Coloca o neurônio na rede e devolve as sinapses que ele formou.

        Tudo é validado antes de mudar a rede: se a regra propuser uma ligação
        inválida, nada é adicionado.
        """
        self._exigir_admissivel(neuronio)
        sinapses: list[Sinapse] = []
        if neuronio.vivo:
            sinapses = [
                Sinapse(
                    conexao.alvo_id,
                    neuronio.id,
                    conexao.peso,
                    criada_em=neuronio.criado_em,
                )
                for conexao in self._regra.conexoes(neuronio, self)
            ]
        pares_novos: set[frozenset[UUID]] = set()
        for sinapse in sinapses:
            self._exigir_ligavel(sinapse, novo=neuronio, pares_novos=pares_novos)
            pares_novos.add(sinapse.par)

        self._incluir_neuronio(neuronio)
        self._neuronios_novos.append(neuronio)
        for sinapse in sinapses:
            self._incluir_sinapse(sinapse)
            self._sinapses_novas.append(sinapse)
        return sinapses

    def marcar_como_salva(self) -> None:
        """Chamado pelo repositório depois de gravar as novidades."""
        self._neuronios_novos.clear()
        self._sinapses_novas.clear()

    def _exigir_admissivel(self, neuronio: Neuronio) -> None:
        if neuronio.usuario_id != self._usuario_id:
            raise RedeNeuralInvalida("O neurônio é de outro estudante.")
        if neuronio.id in self._neuronios or neuronio.sessao_id in self._sessoes:
            raise RedeNeuralInvalida("O neurônio desta sessão já está na rede.")

    def _exigir_ligavel(
        self,
        sinapse: Sinapse,
        *,
        novo: Neuronio | None = None,
        pares_novos: set[frozenset[UUID]] | None = None,
    ) -> None:
        for neuronio_id in (sinapse.origem_id, sinapse.destino_id):
            if novo is not None and novo.id == neuronio_id:
                neuronio: Neuronio | None = novo
            else:
                neuronio = self._neuronios.get(neuronio_id)
            if neuronio is None:
                raise SinapseInvalida("A sinapse liga um neurônio fora da rede.")
            if not neuronio.vivo:
                raise SinapseInvalida("Neurônio podado não forma sinapses.")
        if sinapse.par in self._pares or sinapse.par in (pares_novos or set()):
            raise SinapseInvalida("Esses dois neurônios já estão ligados.")

    def _incluir_neuronio(self, neuronio: Neuronio) -> None:
        self._neuronios[neuronio.id] = neuronio
        # Com datas iguais, quem chegou depois fica depois.
        insort(self._em_ordem, neuronio, key=lambda n: n.criado_em)
        self._sessoes.add(neuronio.sessao_id)

    def _incluir_sinapse(self, sinapse: Sinapse) -> None:
        self._sinapses.append(sinapse)
        self._pares.add(sinapse.par)
        for neuronio_id in (sinapse.origem_id, sinapse.destino_id):
            self._sinapses_por_neuronio.setdefault(neuronio_id, []).append(sinapse)

    def __len__(self) -> int:
        return len(self._neuronios)

    def __repr__(self) -> str:
        return (
            f"RedeNeural(usuario_id={self._usuario_id}, "
            f"neuronios={len(self._neuronios)}, sinapses={len(self._sinapses)})"
        )
