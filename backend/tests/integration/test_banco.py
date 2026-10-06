import pytest
from django.core.management import call_command
from django.db import connection


@pytest.mark.django_db
def test_testes_usam_banco_postgres_separado():
    assert connection.vendor == "postgresql"
    assert connection.settings_dict["NAME"].startswith("test_")


@pytest.mark.django_db
def test_nao_ha_migracoes_pendentes():
    # Falha (SystemExit) se algum model mudou sem a migração correspondente.
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
