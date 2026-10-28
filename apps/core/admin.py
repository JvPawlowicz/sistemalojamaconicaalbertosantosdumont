"""Painel técnico (Django Admin): restrito ao perfil Desenvolvedor (superusuário)."""
from django.apps import apps
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.irmaos.models import Irmao

_APPS = {"core", "irmaos", "cargos", "sessoes", "atas", "tesouraria", "visitas", "documentos", "candidatos",
         "patrimonio", "expediente", "comissoes", "votacoes", "hospitalaria", "agape"}


class IrmaoAdmin(SimpleHistoryAdmin):
    list_display = ("nome_completo", "username", "grau", "situacao", "is_active")
    search_fields = ("nome_completo", "username", "email")
    exclude = ("password", "user_permissions", "groups")


admin.site.site_header = "Painel técnico — Sistema da Loja"
admin.site.register(Irmao, IrmaoAdmin)
for model in apps.get_models():
    if model._meta.app_label in _APPS and model is not Irmao and not model._meta.abstract \
            and not model.__name__.startswith("Historical"):
        base = SimpleHistoryAdmin if hasattr(model, "history") else admin.ModelAdmin
        try:
            admin.site.register(model, type(f"{model.__name__}Admin", (base,), {}))
        except admin.sites.AlreadyRegistered:
            pass
