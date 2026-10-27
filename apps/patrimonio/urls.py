from django.urls import path

from . import views

app_name = "patrimonio"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
    path("<int:pk>/", views.editar, name="editar"),
    path("emprestimo/<int:pk>/devolver/", views.devolver, name="devolver"),
]
