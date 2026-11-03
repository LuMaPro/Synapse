"""Tradução dos erros para o formato da API: {"erro": ..., "mensagem": ...}."""

import logging

import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from app.api.erros import exception_handler

pytestmark = pytest.mark.django_db


def test_permissao_negada_vira_sem_permissao():
    resposta = exception_handler(PermissionDenied(), {"view": None})

    assert resposta.status_code == 403
    assert resposta.data == {
        "erro": "sem_permissao",
        "mensagem": "Você não tem permissão para esta ação.",
    }


def test_outros_erros_do_drf_mantem_o_status_e_a_mensagem():
    # O login só aceita POST: o DRF responde 405, no formato da API.
    resposta = APIClient().get("/auth/login")

    assert resposta.status_code == 405
    dados = resposta.json()
    assert dados["erro"] == "erro_requisicao"
    assert "GET" in dados["mensagem"]


def test_erro_inesperado_vira_500_sem_expor_o_detalhe(caplog):
    with caplog.at_level(logging.ERROR, logger="app.api.erros"):
        resposta = exception_handler(
            RuntimeError("senha do banco: 123"), {"view": "visao_qualquer"}
        )

    assert resposta.status_code == 500
    assert resposta.data == {
        "erro": "erro_interno",
        "mensagem": "Ocorreu um erro interno. Tente novamente mais tarde.",
    }
    # O detalhe fica só no log do servidor.
    assert "visao_qualquer" in caplog.text
