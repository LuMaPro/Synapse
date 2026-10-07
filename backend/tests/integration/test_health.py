from rest_framework.test import APIClient


def test_health():
    resposta = APIClient().get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "erro"}
