from app.infra.repositorios.carteira import RepositorioCarteiraDjango
from app.infra.repositorios.conquista import RepositorioConquistaDjango
from app.infra.repositorios.materia import RepositorioMateriaDjango
from app.infra.repositorios.neuronio import RepositorioNeuronioDjango
from app.infra.repositorios.rede_neural import RepositorioRedeNeuralDjango
from app.infra.repositorios.sessao_foco import (
    RepositorioSessaoDjango,
    RepositorioSessaoFocoDjango,
)
from app.infra.repositorios.usuario import RepositorioUsuarioDjango

__all__ = [
    "RepositorioCarteiraDjango",
    "RepositorioConquistaDjango",
    "RepositorioMateriaDjango",
    "RepositorioNeuronioDjango",
    "RepositorioRedeNeuralDjango",
    "RepositorioUsuarioDjango",
    "RepositorioSessaoDjango",
    "RepositorioSessaoFocoDjango",
]

