from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import translation

from app.application.cadastro import ServicoSenhas
from app.domain.entidades.usuario import Usuario
from app.domain.excecoes import SenhaInvalida
from app.infra.modelos.usuario import UsuarioModel


class ServicoSenhasDjango(ServicoSenhas):
    """Senhas com as ferramentas do Django.

    A validação usa os `AUTH_PASSWORD_VALIDATORS` do settings (tamanho mínimo, senhas
    comuns, só números, parecida com o e-mail), e o hash usa o primeiro dos
    `PASSWORD_HASHERS` (Argon2).
    """

    def validar(self, senha: str, usuario: Usuario) -> None:
        # Model sem salvar, só para o validador comparar a senha com o e-mail.
        candidato = UsuarioModel(email=usuario.email, nome=usuario.nome)
        try:
            # As mensagens dos validadores vêm em português, como o resto da API.
            with translation.override("pt-br"):
                validate_password(senha, candidato)
        except ValidationError as erro:
            raise SenhaInvalida(" ".join(erro.messages)) from erro

    def definir(self, usuario: Usuario, senha: str) -> None:
        model = UsuarioModel.objects.get(id=usuario.id)
        model.set_password(senha)
        model.save(update_fields=["password"])
