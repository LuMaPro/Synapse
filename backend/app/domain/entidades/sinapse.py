from datetime import datetime
from uuid import UUID

from app.domain.entidades.base import Entidade
from app.domain.excecoes import SinapseInvalida
from app.domain.tempo import agora, exigir_fuso


class Sinapse(Entidade):
    """Ligação entre dois neurônios da rede do estudante (#23).

    Vai do neurônio mais antigo (`origem_id`) para o que acabou de nascer
    (`destino_id`). O peso diz quão forte é a ligação: começa em 1 e cresce nas
    ligações da mesma matéria (ver `RegraRecentesEMesmaMateria`). Uma sinapse não
    muda depois de criada; quem garante que ela liga dois neurônios vivos da mesma
    rede, sem repetir, é o agregado `RedeNeural`.
    """

    def __init__(
        self,
        origem_id: UUID,
        destino_id: UUID,
        peso: int,
        *,
        criada_em: datetime | None = None,
        id: UUID | None = None,
    ):
        super().__init__(id)
        if origem_id == destino_id:
            raise SinapseInvalida("Um neurônio não pode se ligar a ele mesmo.")
        # bool é subclasse de int, mas True não é um peso.
        if isinstance(peso, bool) or not isinstance(peso, int) or peso < 1:
            raise SinapseInvalida(
                "O peso da sinapse deve ser um inteiro de 1 em diante."
            )
        self._origem_id = origem_id
        self._destino_id = destino_id
        self._peso = peso
        self._criada_em = (
            exigir_fuso(criada_em, "criada_em") if criada_em is not None else agora()
        )

    @property
    def origem_id(self) -> UUID:
        return self._origem_id

    @property
    def destino_id(self) -> UUID:
        return self._destino_id

    @property
    def peso(self) -> int:
        return self._peso

    @property
    def criada_em(self) -> datetime:
        return self._criada_em

    @property
    def par(self) -> frozenset[UUID]:
        """Os dois neurônios ligados, sem ordem: A→B e B→A são a mesma ligação."""
        return frozenset((self._origem_id, self._destino_id))

    def __repr__(self) -> str:
        return (
            f"Sinapse(origem_id={self._origem_id}, destino_id={self._destino_id}, "
            f"peso={self._peso})"
        )
