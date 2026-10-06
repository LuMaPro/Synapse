from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

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
