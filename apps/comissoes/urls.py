from django.urls import path

from . import views

app_name = "comissoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/", views.editar, name="nova"),
    path("<int:pk>/", views.editar, name="editar"),
]
