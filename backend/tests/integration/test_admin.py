import pytest
from django.core.management import call_command
from django.test import Client

from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente_admin():
    admin = UsuarioModel.objects.create_superuser(
        email="admin@email.com", password="senha-admin-123", nome="Admin"
    )
    cliente = Client()
    cliente.force_login(admin)
    return cliente


def test_admin_exige_login():
    resposta = Client().get("/admin/")

    assert resposta.status_code == 302
    assert "/admin/login/" in resposta["Location"]


def test_admin_lista_usuarios(cliente_admin):
    assert cliente_admin.get("/admin/").status_code == 200
    assert cliente_admin.get("/admin/app/usuariomodel/").status_code == 200


def test_admin_cria_usuario(cliente_admin):
    assert cliente_admin.get("/admin/app/usuariomodel/add/").status_code == 200

    resposta = cliente_admin.post(
        "/admin/app/usuariomodel/add/",
        {
            "email": "bruno@email.com",
            "nome": "Bruno",
            "usable_password": "true",
            "password1": "uma-senha-bem-forte-123",
            "password2": "uma-senha-bem-forte-123",
        },
    )

    assert resposta.status_code == 302
    criado = UsuarioModel.objects.get(email="bruno@email.com")
    assert criado.check_password("uma-senha-bem-forte-123")


def test_admin_abre_edicao_de_usuario(cliente_admin):
    usuario = UsuarioModel.objects.create_user(
        email="ana@email.com", password="x", nome="Ana"
    )

    resposta = cliente_admin.get(f"/admin/app/usuariomodel/{usuario.pk}/change/")

    assert resposta.status_code == 200


def test_comando_createsuperuser(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "senha-super-123")

    call_command(
        "createsuperuser",
        interactive=False,
        email="dono@email.com",
        nome="Dono",
        verbosity=0,
    )

    dono = UsuarioModel.objects.get(email="dono@email.com")
    assert dono.is_superuser
    assert dono.check_password("senha-super-123")
