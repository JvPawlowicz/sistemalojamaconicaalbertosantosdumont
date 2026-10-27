from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("aceite-termo/", views.aceite_termo, name="aceite_termo"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("2fa/configurar/", views.configurar_2fa, name="2fa_configurar"),
    path("2fa/verificar/", views.verificar_2fa, name="2fa_verificar"),
    path("meus-dados/", views.meus_dados, name="meus_dados"),
    path("meus-dados/exportar/", views.exportar_meus_dados, name="exportar_meus_dados"),
    path("lgpd/solicitacoes/", views.solicitacoes_lgpd, name="solicitacoes_lgpd"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("configuracoes/termo/", views.novo_termo, name="novo_termo"),
    path("configuracoes/aceites/", views.relatorio_aceites, name="aceites"),
    path("configuracoes/emails/", views.emails_enviados, name="emails"),
]
