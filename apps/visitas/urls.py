from django.urls import path

from . import views

app_name = "visitas"

urlpatterns = [
    path("", views.realizadas, name="realizadas"),
    path("nova/", views.nova_realizada, name="nova_realizada"),
    path("<int:pk>/certificado/", views.certificado_recebido, name="certificado_recebido"),
    path("visitantes/", views.VisitantesView.as_view(), name="visitantes"),
    path("visitantes/novo/", views.NovoVisitante.as_view(), name="visitante_novo"),
    path("visitantes/<int:pk>/", views.EditarVisitante.as_view(), name="visitante_editar"),
    path("sessao/<int:sessao_pk>/", views.sessao_visitantes, name="sessao"),
    path("sessao/<int:sessao_pk>/gerar/", views.gerar_certificados, name="gerar_certificados"),
    path("sessao/<int:sessao_pk>/assinar/", views.assinar_lote, name="assinar_lote"),
    path("sessao/<int:sessao_pk>/enviar/", views.enviar_lote, name="enviar_lote"),
    path("recebida/<int:pk>/remover/", views.remover_visita, name="remover"),
    path("certificado/<int:pk>.pdf", views.certificado_pdf, name="certificado_pdf"),
]
