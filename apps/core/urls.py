from django.urls import path

from . import views, views_avisos

app_name = "core"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("midia/brasao/", views.brasao, name="brasao"),
    path("midia/irmao/<int:pk>/foto/", views.foto_irmao, name="foto_irmao"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
    path("avisos/", views_avisos.avisos, name="avisos"),
    path("avisos/novo/", views_avisos.aviso_form, name="aviso_novo"),
    path("avisos/<int:pk>/", views_avisos.aviso_form, name="aviso_editar"),
    path("avisos/<int:pk>/excluir/", views_avisos.aviso_excluir, name="aviso_excluir"),
    path("busca/", views.busca, name="busca"),
    path("aceite-termo/", views.aceite_termo, name="aceite_termo"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("2fa/configurar/", views.configurar_2fa, name="2fa_configurar"),
    path("2fa/verificar/", views.verificar_2fa, name="2fa_verificar"),
    path("meus-dados/", views.meus_dados, name="meus_dados"),
    path("meus-dados/exportar/", views.exportar_meus_dados, name="exportar_meus_dados"),
    path("lgpd/solicitacoes/", views.solicitacoes_lgpd, name="solicitacoes_lgpd"),
    path("configuracoes/", views.configuracoes, name="configuracoes"),
    path("configuracoes/testar-email/", views.testar_email, name="testar_email"),
    path("configuracoes/testar-whatsapp/", views.testar_whatsapp, name="testar_whatsapp"),
    path("configuracoes/termo/", views.novo_termo, name="novo_termo"),
    path("configuracoes/aceites/", views.relatorio_aceites, name="aceites"),
    path("configuracoes/emails/", views.emails_enviados, name="emails"),
]
