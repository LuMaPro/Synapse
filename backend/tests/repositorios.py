from datetime import datetime
from uuid import UUID

from app.domain.carteira import Carteira
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.entidades.materia import Materia
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import SessaoFoco
from app.domain.entidades.sinapse import Sinapse
from app.domain.entidades.usuario import Usuario
from app.domain.formacao_sinapses import RegraFormacaoSinapses
from app.domain.rede_neural import RedeNeural
from app.domain.repositorios import (
    RepositorioCarteira,
    RepositorioConquista,
    RepositorioMateria,
    RepositorioNeuronio,
    RepositorioRedeNeural,
    RepositorioSessao,
    RepositorioUsuario,
)


class RepositorioUsuarioMemoria(RepositorioUsuario):
    """
    Implementação em memória de RepositorioUsuario para testes unitários.

    Permite testar casos de uso e serviços da camada de aplicação sem necessidade
    de banco de dados relacional ou ORM, garantindo velocidade e isolamento.
    """

    def __init__(self) -> None:
        self._usuarios: dict[UUID, Usuario] = {}

    def salvar(self, usuario: Usuario) -> None:
        """Persiste um usuário novo ou atualiza um existente em memória."""
        self._usuarios[usuario.id] = usuario

    def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Busca um usuário pelo seu UUID em memória."""
        return self._usuarios.get(id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário pelo seu e-mail (case-insensitive) em memória."""
        email_normalizado = email.strip().lower()
        for usuario in self._usuarios.values():
            if usuario.email == email_normalizado:
                return usuario
        return None

    def existe_com_email(self, email: str) -> bool:
        """Verifica se já existe usuário cadastrado com o e-mail em memória."""
        return self.buscar_por_email(email) is not None

    def limpar(self) -> None:
        """Esvazia o repositório em memória."""
        self._usuarios.clear()

    def __len__(self) -> int:
        return len(self._usuarios)


class RepositorioSessaoMemoria(RepositorioSessao):
    """
    Implementação em memória de RepositorioSessao para testes unitários.

    Permite testar fluxos de sessão (iniciar, concluir, podar, registrar saídas)
    em memória, de forma determinística e sem dependência do PostgreSQL.
    """

    def __init__(self) -> None:
        self._sessoes: dict[UUID, SessaoFoco] = {}

    def salvar(self, sessao: SessaoFoco) -> None:
        """Persiste uma nova sessão ou atualiza uma existente em memória."""
        self._sessoes[sessao.id] = sessao

    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu UUID em memória."""
        return self._sessoes.get(id)

    def listar_por_usuario(self, usuario_id: UUID) -> list[SessaoFoco]:
        """
        Lista todas as sessões de foco de um usuário em ordem decrescente de início.
        """
        sessoes = [s for s in self._sessoes.values() if s.usuario_id == usuario_id]
        return sorted(sessoes, key=lambda s: s.inicio, reverse=True)

    def listar_por_periodo(
        self,
        usuario_id: UUID,
        *,
        de: datetime,
        ate: datetime,
    ) -> list[SessaoFoco]:
        """Lista as sessões iniciadas entre `de` e `ate` (inclusive) em ordem
        crescente de início."""
        sessoes = [
            s
            for s in self._sessoes.values()
            if s.usuario_id == usuario_id and de <= s.inicio <= ate
        ]
        return sorted(sessoes, key=lambda s: s.inicio)

    def listar_historico(
        self,
        usuario_id: UUID,
        *,
        de: datetime | None = None,
        ate: datetime | None = None,
        estado: str | None = None,
        deslocamento: int = 0,
        limite: int = 20,
    ) -> tuple[list[SessaoFoco], int]:
        """Uma página do histórico, filtrada e da mais recente para a mais antiga."""
        sessoes = [
            s
            for s in self.listar_por_usuario(usuario_id)
            if (de is None or s.inicio >= de)
            and (ate is None or s.inicio <= ate)
            and (estado is None or s.codigo_estado == estado)
        ]
        return sessoes[deslocamento : deslocamento + limite], len(sessoes)

    def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
        """
        Retorna a sessão de foco atualmente em andamento do usuário, se houver.
        """
        for sessao in self._sessoes.values():
            if (
                sessao.usuario_id == usuario_id
                and sessao.codigo_estado == "em_andamento"
            ):
                return sessao
        return None

    def listar_em_andamento(self) -> list[SessaoFoco]:
        """Lista as sessões em andamento de todos os usuários em memória."""
        return [s for s in self._sessoes.values() if s.codigo_estado == "em_andamento"]

    def remover(self, id: UUID) -> None:
        """Apaga a sessão da memória, se existir."""
        self._sessoes.pop(id, None)

    def limpar(self) -> None:
        """Esvazia o repositório em memória."""
        self._sessoes.clear()

    def __len__(self) -> int:
        return len(self._sessoes)


class RepositorioNeuronioMemoria(RepositorioNeuronio):
    """Implementação em memória de RepositorioNeuronio para testes unitários."""

    def __init__(self) -> None:
        self._neuronios: dict[UUID, Neuronio] = {}

    def salvar(self, neuronio: Neuronio) -> None:
        self._neuronios[neuronio.id] = neuronio

    def buscar_por_sessao(self, sessao_id: UUID) -> Neuronio | None:
        for neuronio in self._neuronios.values():
            if neuronio.sessao_id == sessao_id:
                return neuronio
        return None

    def listar_por_usuario(self, usuario_id: UUID) -> list[Neuronio]:
        neuronios = [n for n in self._neuronios.values() if n.usuario_id == usuario_id]
        return sorted(neuronios, key=lambda n: n.criado_em, reverse=True)

    def __len__(self) -> int:
        return len(self._neuronios)


class RepositorioRedeNeuralMemoria(RepositorioRedeNeural):
    """Implementação em memória de RepositorioRedeNeural para testes unitários."""

    def __init__(self) -> None:
        self._neuronios: dict[UUID, list[Neuronio]] = {}
        self._sinapses: dict[UUID, list[Sinapse]] = {}

    def carregar(
        self, usuario_id: UUID, regra: RegraFormacaoSinapses | None = None
    ) -> RedeNeural:
        return RedeNeural(
            usuario_id,
            self._neuronios.get(usuario_id, []),
            self._sinapses.get(usuario_id, []),
            regra=regra,
        )

    def salvar(self, rede: RedeNeural) -> None:
        self._neuronios.setdefault(rede.usuario_id, []).extend(rede.neuronios_novos)
        self._sinapses.setdefault(rede.usuario_id, []).extend(rede.sinapses_novas)
        rede.marcar_como_salva()


class RepositorioMateriaMemoria(RepositorioMateria):
    """Implementação em memória de RepositorioMateria para testes unitários."""

    def __init__(self) -> None:
        self._materias: dict[UUID, Materia] = {}

    def salvar(self, materia: Materia) -> None:
        self._materias[materia.id] = materia

    def buscar_por_id(self, id: UUID) -> Materia | None:
        return self._materias.get(id)

    def buscar_por_usuario_e_id(self, usuario_id: UUID, id: UUID) -> Materia | None:
        materia = self._materias.get(id)
        if materia is not None and materia.usuario_id == usuario_id:
            return materia
        return None

    def listar_por_usuario(self, usuario_id: UUID) -> list[Materia]:
        import unicodedata

        def chave(m: Materia) -> str:
            return (
                unicodedata.normalize("NFKD", m.nome)
                .encode("ASCII", "ignore")
                .decode()
                .lower()
            )

        materias = [m for m in self._materias.values() if m.usuario_id == usuario_id]
        return sorted(materias, key=chave)

    def existe_com_nome(
        self, usuario_id: UUID, nome: str, ignorar_id: UUID | None = None
    ) -> bool:
        nome_normalizado = nome.strip().lower()
        for materia in self._materias.values():
            if (
                materia.usuario_id == usuario_id
                and materia.id != ignorar_id
                and materia.nome.lower() == nome_normalizado
            ):
                return True
        return False

    def remover(self, id: UUID) -> None:
        self._materias.pop(id, None)

    def limpar(self) -> None:
        self._materias.clear()

    def __len__(self) -> int:
        return len(self._materias)


# Aliases de conveniência
RepositorioUsuarioEmMemoria = RepositorioUsuarioMemoria
RepositorioSessaoEmMemoria = RepositorioSessaoMemoria
RepositorioMateriaEmMemoria = RepositorioMateriaMemoria


class RepositorioConquistaMemoria(RepositorioConquista):
    """Implementação em memória de RepositorioConquista para testes unitários."""

    def __init__(self) -> None:
        self._conquistas: dict[UUID, ConquistaDesbloqueada] = {}

    def listar_por_usuario(self, usuario_id: UUID) -> list[ConquistaDesbloqueada]:
        return [c for c in self._conquistas.values() if c.usuario_id == usuario_id]

    def salvar(self, conquista: ConquistaDesbloqueada) -> None:
        # O banco recusa a mesma conquista duas vezes para o estudante; aqui também.
        if any(
            c.codigo == conquista.codigo and c.id != conquista.id
            for c in self.listar_por_usuario(conquista.usuario_id)
        ):
            raise ValueError(f"Conquista {conquista.codigo!r} já desbloqueada.")
        self._conquistas[conquista.id] = conquista

    def __len__(self) -> int:
        return len(self._conquistas)


class RepositorioCarteiraMemoria(RepositorioCarteira):
    """Implementação em memória de RepositorioCarteira para testes unitários.

    Guarda cópias, como o banco: mudar uma carteira carregada não muda a guardada
    até ela ser salva.
    """

    def __init__(self) -> None:
        self._carteiras: dict[UUID, Carteira] = {}

    def carregar(self, usuario_id: UUID, *, para_alterar: bool = False) -> Carteira:
        guardada = self._carteiras.get(usuario_id)
        if guardada is None:
            return Carteira(usuario_id)
        return self._copia(guardada)

    def salvar(self, carteira: Carteira) -> None:
        self._carteiras[carteira.usuario_id] = self._copia(carteira)

    @staticmethod
    def _copia(carteira: Carteira) -> Carteira:
        return Carteira(carteira.usuario_id, carteira.saldo, carteira.desbloqueadas)
