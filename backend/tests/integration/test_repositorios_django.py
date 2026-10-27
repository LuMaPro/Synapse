from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction

from app.domain.carteira import Carteira
from app.domain.entidades.conquista import ConquistaDesbloqueada
from app.domain.entidades.materia import Materia
from app.domain.entidades.neuronio import Neuronio
from app.domain.entidades.sessao_foco import Concluida, EmAndamento, Podada, SessaoFoco
from app.domain.entidades.usuario import Usuario
from app.domain.loja import cor_por_codigo
from app.domain.politica_interrupcao import Interrupcao, ModoTolerante
from app.infra.modelos.carteira import CarteiraModel, CorDesbloqueadaModel
from app.infra.modelos.neuronio import NeuronioModel
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.sinapse import SinapseModel
from app.infra.modelos.usuario import UsuarioModel
from app.infra.repositorios import (
    RepositorioCarteiraDjango,
    RepositorioConquistaDjango,
    RepositorioMateriaDjango,
    RepositorioNeuronioDjango,
    RepositorioRedeNeuralDjango,
    RepositorioSessaoDjango,
    RepositorioUsuarioDjango,
)

pytestmark = pytest.mark.django_db


class TestRepositorioUsuarioDjango:
    def test_salva_novo_usuario_e_busca_por_id(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Lucas Oliveira", email="lucas@synapse.com")

        repo.salvar(usuario)

        recuperado = repo.buscar_por_id(usuario.id)
        assert recuperado is not None
        assert isinstance(recuperado, Usuario)
        assert recuperado.id == usuario.id
        assert recuperado.nome == "Lucas Oliveira"
        assert recuperado.email == "lucas@synapse.com"

        # Confirma persistência direta no model
        model = UsuarioModel.objects.get(id=usuario.id)
        assert model.email == "lucas@synapse.com"

    def test_atualiza_usuario_existente(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Beatriz", email="bia@synapse.com")
        repo.salvar(usuario)

        usuario.nome = "Beatriz Lima"
        repo.salvar(usuario)

        recuperado = repo.buscar_por_id(usuario.id)
        assert recuperado is not None
        assert recuperado.nome == "Beatriz Lima"

    def test_busca_por_email_case_insensitive(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Carlos", email="carlos@synapse.com")
        repo.salvar(usuario)

        assert repo.buscar_por_email("CARLOS@synapse.com") == usuario
        assert repo.buscar_por_email("carlos@synapse.com") == usuario
        assert repo.buscar_por_email("inexistente@synapse.com") is None

    def test_existe_com_email(self):
        repo = RepositorioUsuarioDjango()
        usuario = Usuario(nome="Daniela", email="daniela@synapse.com")
        repo.salvar(usuario)

        assert repo.existe_com_email("DANIELA@synapse.com") is True
        assert repo.existe_com_email("outro@synapse.com") is False

    def test_buscar_por_id_inexistente_retorna_none(self):
        repo = RepositorioUsuarioDjango()
        assert repo.buscar_por_id(uuid4()) is None


class TestRepositorioSessaoDjango:
    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(
            email="foco@synapse.com",
            password="senha-123",
            nome="Foco Estudante",
        )

    def test_salva_nova_sessao_e_busca_por_id(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)

        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert isinstance(recuperada, SessaoFoco)
        assert recuperada.id == sessao.id
        assert recuperada.usuario_id == usuario.id
        assert recuperada.duracao.minutos == 25
        assert recuperada.codigo_estado == "em_andamento"
        assert isinstance(recuperada._estado, EmAndamento)

    def test_atualiza_sessao_para_concluida(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)
        repo.salvar(sessao)

        # Transição no domínio
        sessao.concluir(relogio=lambda: sessao.fim_previsto)
        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert recuperada.codigo_estado == "concluida"
        assert isinstance(recuperada._estado, Concluida)
        assert recuperada.encerrada_em is not None

        # Valida no model do Django
        model = SessaoFocoModel.objects.get(id=sessao.id)
        assert model.estado == "concluida"

    def test_atualiza_sessao_para_podada(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=30)
        repo.salvar(sessao)

        sessao.podar()
        repo.salvar(sessao)

        recuperada = repo.buscar_por_id(sessao.id)
        assert recuperada is not None
        assert recuperada.codigo_estado == "podada"
        assert isinstance(recuperada._estado, Podada)

    def test_listar_por_usuario(self, usuario):
        repo = RepositorioSessaoDjango()
        outro_usuario = UsuarioModel.objects.create_user(
            email="outro@synapse.com", password="x", nome="Outro"
        )

        sessao1 = SessaoFoco(usuario_id=usuario.id, duracao_minutos=20)
        sessao2 = SessaoFoco(usuario_id=usuario.id, duracao_minutos=40)
        sessao_outro = SessaoFoco(usuario_id=outro_usuario.id, duracao_minutos=50)

        repo.salvar(sessao1)
        repo.salvar(sessao2)
        repo.salvar(sessao_outro)

        sessoes_usuario = repo.listar_por_usuario(usuario.id)
        assert len(sessoes_usuario) == 2
        ids = {s.id for s in sessoes_usuario}
        assert ids == {sessao1.id, sessao2.id}

    def test_buscar_ativa_por_usuario(self, usuario):
        repo = RepositorioSessaoDjango()
        sessao = SessaoFoco(usuario_id=usuario.id, duracao_minutos=25)
        repo.salvar(sessao)

        ativa = repo.buscar_ativa_por_usuario(usuario.id)
        assert ativa is not None
        assert ativa.id == sessao.id

        # Quando a sessão é concluída, não há mais sessão ativa
        sessao.concluir(relogio=lambda: sessao.fim_previsto)
        repo.salvar(sessao)

        assert repo.buscar_ativa_por_usuario(usuario.id) is None

    def test_buscar_por_id_inexistente_retorna_none(self):
        repo = RepositorioSessaoDjango()
        assert repo.buscar_por_id(uuid4()) is None


INICIO = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)


class TestPersistenciaDaIssue16:
    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(email="ana@synapse.com", nome="Ana")

    def test_sessao_volta_do_banco_com_modo_e_historico(self, usuario):
        repo = RepositorioSessaoDjango()
        saida = INICIO + timedelta(minutes=2)
        sessao = SessaoFoco(
            usuario.id,
            25,
            inicio=INICIO,
            politica=ModoTolerante(),
            interrupcoes=[
                Interrupcao(saida=saida, retorno=saida + timedelta(seconds=30))
            ],
        )

        repo.salvar(sessao)
        recuperada = repo.buscar_por_id(sessao.id)

        assert recuperada.politica.codigo == "tolerante"
        assert recuperada.historico_interrupcoes == sessao.historico_interrupcoes
        assert recuperada.tempo_fora == timedelta(seconds=30)

    def test_listar_em_andamento_ignora_as_encerradas(self, usuario):
        repo = RepositorioSessaoDjango()
        ativa = SessaoFoco(usuario.id, 25, inicio=INICIO)
        podada = SessaoFoco(usuario.id, 25, inicio=INICIO, estado=Podada())
        repo.salvar(ativa)
        repo.salvar(podada)

        assert [s.id for s in repo.listar_em_andamento()] == [ativa.id]

    def test_neuronio_ida_e_volta(self, usuario):
        sessao = SessaoFoco(usuario.id, 25, inicio=INICIO, estado=Concluida())
        RepositorioSessaoDjango().salvar(sessao)
        repo = RepositorioNeuronioDjango()
        neuronio = Neuronio(usuario.id, sessao.id, 25, criado_em=INICIO)

        repo.salvar(neuronio)

        recuperado = repo.buscar_por_sessao(sessao.id)
        assert recuperado == neuronio
        assert recuperado.duracao.minutos == 25
        assert recuperado.criado_em == INICIO
        assert repo.listar_por_usuario(usuario.id) == [neuronio]
        assert repo.buscar_por_sessao(uuid4()) is None


class TestRepositorioRedeNeuralDjango:
    """Persistência da rede neural (issue #23)."""

    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(email="bia@synapse.com", nome="Bia")

    @staticmethod
    def _neuronio(usuario_id, horas, *, vivo=True, materia_id=None):
        # O neurônio aponta para uma sessão que precisa existir no banco.
        estado = Concluida() if vivo else Podada()
        sessao = SessaoFoco(usuario_id, 25, inicio=INICIO, estado=estado)
        RepositorioSessaoDjango().salvar(sessao)
        return Neuronio(
            usuario_id,
            sessao.id,
            25,
            vivo=vivo,
            materia_id=materia_id,
            criado_em=INICIO + timedelta(hours=horas),
        )

    def test_rede_ida_e_volta(self, usuario):
        repo = RepositorioRedeNeuralDjango()
        materia = uuid4()
        rede = repo.carregar(usuario.id)
        neuronios = [
            self._neuronio(usuario.id, 1, materia_id=materia),
            self._neuronio(usuario.id, 2),
            self._neuronio(usuario.id, 3, vivo=False),
            self._neuronio(usuario.id, 4, materia_id=materia),
        ]
        for neuronio in neuronios:
            rede.adicionar(neuronio)

        repo.salvar(rede)
        recuperada = repo.carregar(usuario.id)

        assert recuperada.neuronios == neuronios
        assert [(n.vivo, n.materia_id) for n in recuperada.neuronios] == [
            (True, materia),
            (True, None),
            (False, None),
            (True, materia),
        ]
        assert {(s.id, s.origem_id, s.destino_id, s.peso) for s in rede.sinapses} == {
            (s.id, s.origem_id, s.destino_id, s.peso) for s in recuperada.sinapses
        }
        assert len(recuperada.sinapses) == 3
        assert rede.neuronios_novos == []
        assert rede.sinapses_novas == []

    def test_salvar_de_novo_so_grava_as_novidades(self, usuario):
        repo = RepositorioRedeNeuralDjango()
        rede = repo.carregar(usuario.id)
        rede.adicionar(self._neuronio(usuario.id, 1))
        repo.salvar(rede)

        rede = repo.carregar(usuario.id)
        rede.adicionar(self._neuronio(usuario.id, 2))
        repo.salvar(rede)
        repo.salvar(rede)

        assert NeuronioModel.objects.filter(usuario=usuario).count() == 2
        assert SinapseModel.objects.filter(usuario=usuario).count() == 1

    def test_cada_estudante_tem_a_sua_rede(self, usuario):
        repo = RepositorioRedeNeuralDjango()
        outro = UsuarioModel.objects.create_user(email="caio@synapse.com", nome="Caio")
        rede_outro = repo.carregar(outro.id)
        rede_outro.adicionar(self._neuronio(outro.id, 1))
        repo.salvar(rede_outro)

        rede = repo.carregar(usuario.id)
        assert len(rede) == 0
        assert rede.adicionar(self._neuronio(usuario.id, 2)) == []

    def test_carrega_a_rede_em_duas_consultas(self, usuario, django_assert_num_queries):
        repo = RepositorioRedeNeuralDjango()
        rede = repo.carregar(usuario.id)
        for horas in range(1, 6):
            rede.adicionar(self._neuronio(usuario.id, horas))
        repo.salvar(rede)

        with django_assert_num_queries(2):
            assert len(repo.carregar(usuario.id).sinapses) == 7

    @pytest.mark.parametrize("caso", ["autoconexao", "repetida", "peso_zero"])
    def test_banco_tambem_recusa_sinapses_invalidas(self, usuario, caso):
        a = self._neuronio(usuario.id, 1)
        b = self._neuronio(usuario.id, 2)
        RepositorioNeuronioDjango().salvar(a)
        RepositorioNeuronioDjango().salvar(b)
        dados = {"usuario": usuario, "criada_em": INICIO, "peso": 1}
        SinapseModel.objects.create(origem_id=a.id, destino_id=b.id, **dados)
        invalida = {
            "autoconexao": {"origem_id": a.id, "destino_id": a.id},
            "repetida": {"origem_id": a.id, "destino_id": b.id},
            "peso_zero": {"origem_id": b.id, "destino_id": a.id, "peso": 0},
        }[caso]

        with pytest.raises(IntegrityError), transaction.atomic():
            SinapseModel.objects.create(**{**dados, **invalida})


class TestRepositorioMateriaDjango:
    """Persistência de matérias no Django ORM (#27)."""

    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(
            email="materia@synapse.com", nome="Estudante Matéria"
        )

    def test_salva_nova_materia_e_busca_por_id(self, usuario):
        repo = RepositorioMateriaDjango()
        materia = Materia(usuario.id, "Cálculo I", "#8B7BFF")

        repo.salvar(materia)

        recuperada = repo.buscar_por_id(materia.id)
        assert recuperada is not None
        assert recuperada == materia
        assert recuperada.nome == "Cálculo I"
        assert recuperada.cor == "#8B7BFF"
        assert recuperada.usuario_id == usuario.id

    def test_atualiza_materia_existente(self, usuario):
        repo = RepositorioMateriaDjango()
        materia = Materia(usuario.id, "Cálculo I", "#8B7BFF")
        repo.salvar(materia)

        materia.atualizar(nome="Cálculo II", cor="#3EE6E0")
        repo.salvar(materia)

        atualizada = repo.buscar_por_id(materia.id)
        assert atualizada.nome == "Cálculo II"
        assert atualizada.cor == "#3EE6E0"

    def test_buscar_por_usuario_e_id_isola_estudantes(self, usuario):
        outro = UsuarioModel.objects.create_user(
            email="outro_estudante@synapse.com", nome="Outro"
        )
        repo = RepositorioMateriaDjango()
        materia = Materia(usuario.id, "POO", "#3EE6E0")
        repo.salvar(materia)

        assert repo.buscar_por_usuario_e_id(usuario.id, materia.id) == materia
        assert repo.buscar_por_usuario_e_id(outro.id, materia.id) is None
        assert repo.buscar_por_usuario_e_id(usuario.id, uuid4()) is None

    def test_listar_por_usuario_ordena_por_nome(self, usuario):
        outro = UsuarioModel.objects.create_user(
            email="outro2@synapse.com", nome="Outro 2"
        )
        repo = RepositorioMateriaDjango()
        m1 = Materia(usuario.id, "POO", "#3EE6E0")
        m2 = Materia(usuario.id, "Álgebra Linear", "#FFC857")
        m3 = Materia(usuario.id, "Cálculo", "#8B7BFF")
        m_outro = Materia(outro.id, "Física", "#5BE49B")

        for m in (m1, m2, m3, m_outro):
            repo.salvar(m)

        materias = repo.listar_por_usuario(usuario.id)
        assert len(materias) == 3
        # O banco ordena por nome
        assert [m.nome for m in materias] == ["Cálculo", "POO", "Álgebra Linear"] or [
            m.nome for m in materias
        ] == ["Álgebra Linear", "Cálculo", "POO"]

    def test_existe_com_nome_case_insensitive_e_ignorar_id(self, usuario):
        repo = RepositorioMateriaDjango()
        materia = Materia(usuario.id, "POO", "#3EE6E0")
        repo.salvar(materia)

        assert repo.existe_com_nome(usuario.id, "poo")
        assert repo.existe_com_nome(usuario.id, "POO")
        assert repo.existe_com_nome(usuario.id, "poo", ignorar_id=materia.id) is False
        assert repo.existe_com_nome(usuario.id, "Cálculo") is False

    def test_remover_materia(self, usuario):
        repo = RepositorioMateriaDjango()
        materia = Materia(usuario.id, "POO", "#3EE6E0")
        repo.salvar(materia)

        assert repo.buscar_por_id(materia.id) is not None

        repo.remover(materia.id)

        assert repo.buscar_por_id(materia.id) is None


class TestRepositorioConquistaDjango:
    """Persistência das conquistas desbloqueadas (#32)."""

    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(
            email="conquista@synapse.com", nome="Estudante Conquista"
        )

    def test_salva_e_lista_as_conquistas_do_estudante(self, usuario):
        outro = UsuarioModel.objects.create_user(email="o@synapse.com", nome="Outro")
        repo = RepositorioConquistaDjango()
        quando = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        primeira = ConquistaDesbloqueada(usuario.id, "primeiro_neuronio", quando)
        repo.salvar(primeira)
        repo.salvar(
            ConquistaDesbloqueada(
                usuario.id, "dias_seguidos_7", quando + timedelta(days=6)
            )
        )
        repo.salvar(ConquistaDesbloqueada(outro.id, "primeiro_neuronio", quando))

        conquistas = repo.listar_por_usuario(usuario.id)

        assert [c.codigo for c in conquistas] == [
            "primeiro_neuronio",
            "dias_seguidos_7",
        ]
        assert conquistas[0] == primeira
        assert conquistas[0].usuario_id == usuario.id
        assert conquistas[0].desbloqueada_em == quando

    def test_o_banco_recusa_a_mesma_conquista_duas_vezes(self, usuario):
        repo = RepositorioConquistaDjango()
        quando = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        repo.salvar(ConquistaDesbloqueada(usuario.id, "primeiro_neuronio", quando))

        with pytest.raises(IntegrityError), transaction.atomic():
            repo.salvar(ConquistaDesbloqueada(usuario.id, "primeiro_neuronio", quando))


class TestRepositorioCarteiraDjango:
    """Persistência da carteira de ATP e das cores compradas (#34)."""

    @pytest.fixture
    def usuario(self):
        return UsuarioModel.objects.create_user(email="atp@synapse.com", nome="ATP")

    def test_estudante_sem_carteira_recebe_uma_vazia(self, usuario):
        carteira = RepositorioCarteiraDjango().carregar(usuario.id)

        assert carteira.saldo == 0
        assert carteira.desbloqueadas == {}
        assert not CarteiraModel.objects.filter(usuario=usuario).exists()

    def test_carteira_ida_e_volta(self, usuario):
        repo = RepositorioCarteiraDjango()
        quando = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        carteira = Carteira(usuario.id, saldo=400)
        carteira.comprar(cor_por_codigo("magenta_neon"), quando)
        carteira.comprar(cor_por_codigo("lavanda"), quando)
        repo.salvar(carteira)
        repo.salvar(carteira)  # Gravar de novo não duplica as cores.

        lida = repo.carregar(usuario.id)

        assert lida.saldo == 50
        assert lida.desbloqueadas == {"magenta_neon": quando, "lavanda": quando}

    def test_carregar_para_alterar_cria_a_carteira(self, usuario):
        with transaction.atomic():
            carteira = RepositorioCarteiraDjango().carregar(
                usuario.id, para_alterar=True
            )

        assert carteira.saldo == 0
        assert CarteiraModel.objects.get(usuario=usuario).saldo == 0

    def test_o_banco_recusa_saldo_negativo(self, usuario):
        with pytest.raises(IntegrityError), transaction.atomic():
            CarteiraModel.objects.create(usuario=usuario, saldo=-1)

    def test_o_banco_recusa_a_mesma_cor_duas_vezes(self, usuario):
        quando = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
        CorDesbloqueadaModel.objects.create(
            usuario=usuario, codigo="lavanda", desbloqueada_em=quando
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            CorDesbloqueadaModel.objects.create(
                usuario=usuario, codigo="lavanda", desbloqueada_em=quando
            )
