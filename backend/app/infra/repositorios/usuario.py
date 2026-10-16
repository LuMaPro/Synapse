from uuid import UUID

from app.domain.entidades.usuario import Usuario
from app.domain.repositorios import RepositorioUsuario
from app.infra.modelos.usuario import UsuarioModel


class RepositorioUsuarioDjango(RepositorioUsuario):
    """
    Implementação concreta de RepositorioUsuario utilizando o ORM do Django.

    Responsável por converter UsuarioModel (infraestrutura/ORM) ↔
    Usuario (entidade pura de domínio).
    """

    def salvar(self, usuario: Usuario) -> None:
        """Persiste um usuário novo ou atualiza um existente."""
        usuario_model = UsuarioModel.objects.filter(id=usuario.id).first()
        if usuario_model:
            usuario_model.nome = usuario.nome
            usuario_model.email = usuario.email
            usuario_model.save(update_fields=["nome", "email"])
        else:
            UsuarioModel.objects.create(
                id=usuario.id,
                nome=usuario.nome,
                email=usuario.email,
                criado_em=usuario.criado_em,
            )

    def buscar_por_id(self, id: UUID) -> Usuario | None:
        """Busca um usuário pelo seu identificador único (UUID)."""
        usuario_model = UsuarioModel.objects.filter(id=id).first()
        if not usuario_model:
            return None
        return self._model_para_entidade(usuario_model)

    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário pelo seu endereço de e-mail (case-insensitive)."""
        email_normalizado = email.strip().lower()
        usuario_model = UsuarioModel.objects.filter(email=email_normalizado).first()
        if not usuario_model:
            return None
        return self._model_para_entidade(usuario_model)

    def existe_com_email(self, email: str) -> bool:
        """Verifica se já existe algum usuário cadastrado com o e-mail informado."""
        email_normalizado = email.strip().lower()
        return UsuarioModel.objects.filter(email=email_normalizado).exists()

    @staticmethod
    def _model_para_entidade(model: UsuarioModel) -> Usuario:
        """Converte uma instância de UsuarioModel para a entidade Usuario de domínio."""
        return Usuario(
            nome=model.nome,
            email=model.email,
            id=model.id,
            criado_em=model.criado_em,
        )
