from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.duracao import Duracao
from app.domain.entidades import SessaoFoco
from app.domain.excecoes import DuracaoInvalida, ErroDominio, HorarioInvalido

INICIO = datetime(2026, 10, 12, 14, 0, tzinfo=UTC)


def test_cria_sessao_com_duracao_e_horarios():
    usuario_id = uuid4()

    sessao = SessaoFoco(usuario_id, 25, inicio=INICIO)

    assert isinstance(sessao.id, UUID)
    assert sessao.usuario_id == usuario_id
    assert sessao.duracao == Duracao(25)
    assert sessao.inicio == INICIO
    assert sessao.fim_previsto == INICIO + timedelta(minutes=25)
    assert sessao.encerrada_em is None


def test_inicio_padrao_e_agora():
    antes = datetime.now(UTC)
    sessao = SessaoFoco(uuid4(), 25)

    assert antes <= sessao.inicio <= datetime.now(UTC)


@pytest.mark.parametrize("duracao", [0, 5, 9, 121, 23, 25.5, "25", None])
def test_duracao_invalida_lanca_excecao_de_dominio(duracao):
    with pytest.raises(DuracaoInvalida) as erro:
        SessaoFoco(uuid4(), duracao, inicio=INICIO)

    assert isinstance(erro.value, ErroDominio)


def test_recusa_inicio_sem_fuso():
    with pytest.raises(HorarioInvalido):
        SessaoFoco(uuid4(), 25, inicio=datetime(2026, 10, 12, 14, 0))


def test_reconstroi_sessao_encerrada():
    encerrada_em = INICIO + timedelta(minutes=25)

    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO, encerrada_em=encerrada_em)

    assert sessao.encerrada_em == encerrada_em


def test_recusa_sessao_que_termina_antes_de_comecar():
    with pytest.raises(HorarioInvalido, match="antes de começar"):
        SessaoFoco(
            uuid4(), 25, inicio=INICIO, encerrada_em=INICIO - timedelta(seconds=1)
        )


def test_recusa_encerramento_sem_fuso():
    with pytest.raises(HorarioInvalido):
        SessaoFoco(
            uuid4(), 25, inicio=INICIO, encerrada_em=datetime(2026, 10, 12, 15, 0)
        )


@pytest.mark.parametrize(
    "atributo",
    ["id", "usuario_id", "duracao", "inicio", "fim_previsto", "encerrada_em"],
)
def test_atributos_sao_somente_leitura(atributo):
    sessao = SessaoFoco(uuid4(), 25, inicio=INICIO)

    with pytest.raises(AttributeError):
        setattr(sessao, atributo, "outro valor")


def test_sessoes_sao_iguais_quando_tem_o_mesmo_id():
    id_comum = uuid4()

    assert SessaoFoco(uuid4(), 25, id=id_comum) == SessaoFoco(uuid4(), 60, id=id_comum)
    assert SessaoFoco(uuid4(), 25) != SessaoFoco(uuid4(), 25)


def test_repr_mostra_id_usuario_e_duracao():
    sessao = SessaoFoco(uuid4(), 25)

    assert repr(sessao) == (
        f"SessaoFoco(id={sessao.id}, usuario_id={sessao.usuario_id}, duracao=25 min)"
    )
