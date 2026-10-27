from django.urls import path

from . import views

app_name = "atas"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/<int:sessao_pk>/", views.criar, name="criar"),
    path("modelos/", views.ModelosView.as_view(), name="modelos"),
    path("modelos/novo/", views.NovoModelo.as_view(), name="modelo_novo"),
    path("modelos/buscar/", views.buscar_modelos, name="modelos_buscar"),
    path("modelos/<int:pk>/", views.EditarModelo.as_view(), name="modelo_editar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/circular/", views.circular, name="circular"),
    path("<int:pk>/aprovar/", views.aprovar, name="aprovar"),
    path("<int:pk>/assinar/", views.assinar, name="assinar"),
    path("<int:pk>/nova-versao/", views.nova_versao, name="nova_versao"),
    path("<int:pk>/ata.pdf", views.pdf, name="pdf"),
]
