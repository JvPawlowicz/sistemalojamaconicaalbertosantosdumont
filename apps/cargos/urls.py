from django.urls import path

from . import views

app_name = "cargos"

urlpatterns = [
    path("", views.quadro, name="quadro"),
    path("copiar/", views.copiar_gestao, name="copiar"),
    path("catalogo/", views.CatalogoView.as_view(), name="catalogo"),
    path("catalogo/novo/", views.NovoCargo.as_view(), name="novo"),
    path("catalogo/<int:pk>/", views.EditarCargo.as_view(), name="editar"),
]
