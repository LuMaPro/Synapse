from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from app.infra.modelos.materia import MateriaModel
from app.infra.modelos.sessao_foco import SessaoFocoModel
from app.infra.modelos.usuario import UsuarioModel


class FormularioCriacaoUsuario(AdminUserCreationForm):
    class Meta:
        model = UsuarioModel
        fields = ("email", "nome")
        field_classes = {}


class FormularioEdicaoUsuario(UserChangeForm):
    class Meta:
        model = UsuarioModel
        fields = "__all__"
        field_classes = {}


@admin.register(UsuarioModel)
class UsuarioAdmin(UserAdmin):
    add_form = FormularioCriacaoUsuario
    form = FormularioEdicaoUsuario

    list_display = ("email", "nome", "is_staff", "is_active", "criado_em")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "nome")
    ordering = ("email",)
    readonly_fields = ("criado_em", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("nome",)}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "criado_em")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(SessaoFocoModel)
class SessaoFocoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "duracao_minutos",
        "estado",
        "inicio",
        "encerrada_em",
    )
    list_filter = ("estado", "inicio")
    search_fields = ("usuario__email", "usuario__nome")
    readonly_fields = ("inicio",)


@admin.register(MateriaModel)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cor", "usuario", "criada_em")
    list_filter = ("criada_em",)
    search_fields = ("nome", "usuario__email", "usuario__nome")
    readonly_fields = ("criada_em",)

