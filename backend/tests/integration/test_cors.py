import pytest
from rest_framework.test import APIClient


@pytest.mark.parametrize("origem", ["http://localhost:5173", "http://localhost:4173"])
def test_o_frontend_de_desenvolvimento_e_o_de_producao_podem_chamar_a_api(origem):
    # 4173 é o `vite preview`, o build de produção com o service worker (#35).
    resposta = APIClient().options(
        "/health",
        HTTP_ORIGIN=origem,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )

    assert resposta.headers["Access-Control-Allow-Origin"] == origem


def test_outra_origem_nao_recebe_permissao():
    resposta = APIClient().options(
        "/health",
        HTTP_ORIGIN="http://outro-site.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )

    assert "Access-Control-Allow-Origin" not in resposta.headers
