import uuid

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError

from app.infra.modelos.usuario import UsuarioModel

pytestmark = pytest.mark.django_db


def test_modelo_de_usuario_do_projeto_e_o_customizado():
    assert get_user_model() is UsuarioModel
    assert UsuarioModel.USERNAME_FIELD == "email"


def test_create_user_normaliza_email_e_guarda_hash_da_senha():
    usuario = UsuarioModel.objects.create_user(
        email="Ana@Email.COM", password="senha-forte-123", nome="Ana"
    )

    assert isinstance(usuario.id, uuid.UUID)
    assert usuario.email == "ana@email.com"
    assert usuario.password != "senha-forte-123"
    assert usuario.check_password("senha-forte-123")
    assert not usuario.is_staff
    assert not usuario.is_superuser


def test_create_user_exige_email():
    with pytest.raises(ValueError):
        UsuarioModel.objects.create_user(email="", password="x", nome="Sem e-mail")


def test_email_e_unico():
    UsuarioModel.objects.create_user(email="ana@email.com", password="x", nome="Ana")

    with pytest.raises(IntegrityError):
        UsuarioModel.objects.create_user(
            email="ANA@email.com", password="y", nome="Outra"
        )


def test_create_superuser_acessa_o_admin():
    admin = UsuarioModel.objects.create_superuser(
        email="admin@email.com", password="x", nome="Admin"
    )

    assert admin.is_staff
    assert admin.is_superuser


def test_create_superuser_recusa_flags_falsas():
    with pytest.raises(ValueError):
        UsuarioModel.objects.create_superuser(
            email="admin@email.com", password="x", nome="Admin", is_staff=False
        )


def test_login_por_email_e_senha():
    UsuarioModel.objects.create_user(
        email="ana@email.com", password="senha-123", nome="Ana"
    )

    assert authenticate(email="ana@email.com", password="senha-123") is not None
    assert authenticate(email="ana@email.com", password="errada") is None
