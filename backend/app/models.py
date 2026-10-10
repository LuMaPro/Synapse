# O Django procura os models em app.models. Eles ficam em app/infra/modelos/
# (camada de infraestrutura) e são reexportados aqui.
from app.infra.modelos.usuario import UsuarioModel

__all__ = ["UsuarioModel"]
