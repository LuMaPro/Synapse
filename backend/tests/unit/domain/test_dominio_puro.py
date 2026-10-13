import ast
from pathlib import Path

import pytest

PASTA_DOMINIO = Path(__file__).resolve().parents[3] / "app" / "domain"
PROIBIDOS = {"django", "rest_framework"}


def _modulos_importados(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    modulos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


ARQUIVOS = sorted(PASTA_DOMINIO.rglob("*.py"))


def test_pasta_do_dominio_foi_encontrada():
    assert ARQUIVOS, f"nenhum arquivo .py em {PASTA_DOMINIO}"


@pytest.mark.parametrize(
    "arquivo", ARQUIVOS, ids=lambda a: str(a.relative_to(PASTA_DOMINIO))
)
def test_dominio_nao_importa_django_nem_drf(arquivo):
    raizes = {modulo.split(".")[0] for modulo in _modulos_importados(arquivo)}

    assert not raizes & PROIBIDOS
