from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.atas import views as atas_views
from apps.irmaos import views_extra as irmaos_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("senha/alterar/", auth_views.PasswordChangeView.as_view(success_url="/"), name="password_change"),
    path("senha/recuperar/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt"), name="password_reset"),
    path("senha/recuperar/enviado/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("senha/redefinir/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html"), name="password_reset_confirm"),
    path("senha/redefinida/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("verificar/<str:codigo>/", atas_views.verificar, name="verificar"),
    path("carteirinha/", irmaos_views.carteirinha, name="carteirinha_atalho"),
    path("carteirinha/verificar/<str:codigo>/", irmaos_views.verificar_carteirinha, name="verificar_carteirinha_publica"),
    path("irmaos/", include("apps.irmaos.urls")),
    path("cargos/", include("apps.cargos.urls")),
    path("sessoes/", include("apps.sessoes.urls")),
    path("atas/", include("apps.atas.urls")),
    path("tesouraria/", include("apps.tesouraria.urls")),
    path("visitas/", include("apps.visitas.urls")),
    path("documentos/", include("apps.documentos.urls")),
    path("candidatos/", include("apps.candidatos.urls")),
    path("patrimonio/", include("apps.patrimonio.urls")),
    path("expediente/", include("apps.expediente.urls")),
    path("comissoes/", include("apps.comissoes.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("", include("apps.core.urls")),
]
