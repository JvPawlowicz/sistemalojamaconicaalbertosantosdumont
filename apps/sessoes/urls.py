from django.urls import path

from . import views

app_name = "sessoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/", views.criar, name="criar"),
    path("frequencia/", views.frequencia, name="frequencia"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/escala/", views.escala, name="escala"),
    path("<int:pk>/presenca/", views.presenca, name="presenca"),
    path("<int:pk>/concluir/", views.concluir, name="concluir"),
    path("<int:pk>/convocacao.pdf", views.convocacao_pdf, name="convocacao_pdf"),
    path("<int:pk>/convocacao/enviar/", views.enviar_convocacao, name="enviar_convocacao"),
]
