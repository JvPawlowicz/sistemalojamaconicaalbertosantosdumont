from django.urls import path

from . import views, views_extra

app_name = "sessoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/", views.criar, name="criar"),
    path("frequencia/", views.frequencia, name="frequencia"),
    path("agenda/", views_extra.agenda, name="agenda"),
    path("agenda.ics", views_extra.agenda_ics, name="agenda_ics"),
    path("eventos/", views_extra.eventos, name="eventos"),
    path("eventos/novo/", views_extra.evento_form, name="evento_novo"),
    path("eventos/<int:pk>/", views_extra.evento, name="evento"),
    path("eventos/<int:pk>/excluir/", views_extra.evento_excluir, name="evento_excluir"),
    path("eventos/<int:pk>/editar/", views_extra.evento_form, name="evento_editar"),
    path("<int:sessao_pk>/cerimonias/", views_extra.cerimonias_sessao, name="cerimonias"),
    path("<int:sessao_pk>/iniciar/", views_extra.iniciar, name="iniciar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/escala/", views.escala, name="escala"),
    path("<int:pk>/presenca/", views.presenca, name="presenca"),
    path("<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("<int:pk>/concluir/", views.concluir, name="concluir"),
    path("<int:pk>/convocacao.pdf", views.convocacao_pdf, name="convocacao_pdf"),
    path("<int:pk>/convocacao/enviar/", views.enviar_convocacao, name="enviar_convocacao"),
]
