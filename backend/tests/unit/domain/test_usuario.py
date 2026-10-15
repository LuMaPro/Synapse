from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.entidades import Usuario
from app.domain.excecoes import EmailInvalido, HorarioInvalido, NomeInvalido
from app.domain.politica_interrupcao import ModoEstrito, ModoTolerante


def test_cria_usuario_com_id_e_data_de_criacao():
    antes = datetime.now(UTC)
    usuario = Usuario("Julia", "julia@exemplo.com")

    assert isinstance(usuario.id, UUID)
    assert usuario.nome == "Julia"
    assert usuario.email == "julia@exemplo.com"
    assert antes <= usuario.criado_em <= datetime.now(UTC)


def test_reconstroi_usuario_com_id_e_data_existentes():
    id_existente = uuid4()
    criado_em = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    usuario = Usuario(
        "Julia", "julia@exemplo.com", id=id_existente, criado_em=criado_em
    )

    assert usuario.id == id_existente
    assert usuario.criado_em == criado_em


def test_normaliza_nome_e_email():
    usuario = Usuario("  Julia  ", "  Julia@Exemplo.COM ")

    assert usuario.nome == "Julia"
    assert usuario.email == "julia@exemplo.com"


@pytest.mark.parametrize("nome", ["", "   ", None, "a" * 151])
def test_recusa_nome_invalido(nome):
    with pytest.raises(NomeInvalido):
        Usuario(nome, "julia@exemplo.com")


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        None,
        "sem-arroba",
        "julia@exemplo",
        "ju lia@exemplo.com",
        "a" * 250 + "@x.com",
    ],
)
def test_recusa_email_invalido(email):
    with pytest.raises(EmailInvalido):
        Usuario("Julia", email)


def test_recusa_data_de_criacao_sem_fuso():
    with pytest.raises(HorarioInvalido):
        Usuario("Julia", "julia@exemplo.com", criado_em=datetime(2026, 10, 1, 12, 0))


def test_nome_pode_mudar_mas_continua_validado():
    usuario = Usuario("Julia", "julia@exemplo.com")

    usuario.nome = "  Julia Souza "
    assert usuario.nome == "Julia Souza"

    with pytest.raises(NomeInvalido):
        usuario.nome = ""
    assert usuario.nome == "Julia Souza"


@pytest.mark.parametrize("atributo", ["id", "email", "criado_em"])
def test_atributos_sao_somente_leitura(atributo):
    usuario = Usuario("Julia", "julia@exemplo.com")

    with pytest.raises(AttributeError):
        setattr(usuario, atributo, "outro valor")


def test_usuarios_sao_iguais_quando_tem_o_mesmo_id():
    id_comum = uuid4()
    usuario = Usuario("Julia", "julia@exemplo.com", id=id_comum)
    mesmo_usuario = Usuario("Outro nome", "outro@exemplo.com", id=id_comum)

    assert usuario == mesmo_usuario
    assert hash(usuario) == hash(mesmo_usuario)
    assert usuario != Usuario("Julia", "julia@exemplo.com")


def test_repr_mostra_id_e_email():
    usuario = Usuario("Julia", "julia@exemplo.com")

    assert repr(usuario) == f"Usuario(id={usuario.id}, email='julia@exemplo.com')"


def test_politica_padrao_e_o_modo_estrito_e_pode_ser_escolhida():
    assert isinstance(
        Usuario("Julia", "julia@exemplo.com").politica_padrao, ModoEstrito
    )

    tolerante = ModoTolerante()
    usuario = Usuario("Julia", "julia@exemplo.com", politica_padrao=tolerante)

    assert usuario.politica_padrao is tolerante
