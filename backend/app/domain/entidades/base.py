from uuid import UUID, uuid4


class Entidade:
    """Base das entidades: objetos com identidade própria.

    Duas entidades são iguais quando são do mesmo tipo e têm o mesmo id, mesmo que
    os outros atributos sejam diferentes. O id é gerado no próprio domínio, sem
    depender do banco.
    """

    def __init__(self, id: UUID | None = None):
        self._id = id if id is not None else uuid4()

    @property
    def id(self) -> UUID:
        return self._id

    def __eq__(self, outro: object) -> bool:
        return type(self) is type(outro) and self._id == outro._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))
