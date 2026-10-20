from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.duracao import Duracao
from app.domain.entidades import Neuronio, Usuario
from app.domain.excecoes import DuracaoInvalida, HorarioInvalido


def test_cria_neuronio_ligado_a_sessao():
    usuario_id, sessao_id = uuid4(), uuid4()
    antes = datetime.now(UTC)

    neuronio = Neuronio(usuario_id, sessao_id, 60)

    assert isinstance(neuronio.id, UUID)
    assert neuronio.usuario_id == usuario_id
    assert neuronio.sessao_id == sessao_id
    assert neuronio.duracao == Duracao(60)
    assert antes <= neuronio.criado_em <= datetime.now(UTC)
    # Por padrão é vivo (sessão concluída) e sem matéria.
    assert neuronio.vivo is True
    assert neuronio.materia_id is None


def test_neuronio_morto_de_sessao_podada_com_materia():
    materia_id = uuid4()

    neuronio = Neuronio(uuid4(), uuid4(), 25, vivo=False, materia_id=materia_id)

    assert neuronio.vivo is False
    assert neuronio.materia_id == materia_id


def test_recusa_duracao_invalida():
    with pytest.raises(DuracaoInvalida):
        Neuronio(uuid4(), uuid4(), 7)


def test_recusa_data_de_criacao_sem_fuso():
    with pytest.raises(HorarioInvalido):
        Neuronio(uuid4(), uuid4(), 25, criado_em=datetime(2026, 10, 12, 14, 0))


@pytest.mark.parametrize(
    "atributo",
    ["id", "usuario_id", "sessao_id", "duracao", "vivo", "materia_id", "criado_em"],
)
def test_atributos_sao_somente_leitura(atributo):
    neuronio = Neuronio(uuid4(), uuid4(), 25)

    with pytest.raises(AttributeError):
        setattr(neuronio, atributo, "outro valor")


def test_entidades_de_tipos_diferentes_nunca_sao_iguais():
    id_comum = uuid4()

    assert Neuronio(uuid4(), uuid4(), 25, id=id_comum) != Usuario(
        "Julia", "julia@exemplo.com", id=id_comum
    )


def test_repr_mostra_id_e_sessao():
    neuronio = Neuronio(uuid4(), uuid4(), 25)

    assert repr(neuronio) == (
        f"Neuronio(id={neuronio.id}, sessao_id={neuronio.sessao_id})"
    )
