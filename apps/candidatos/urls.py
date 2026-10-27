from django.urls import path

from . import views

app_name = "candidatos"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("novo/", views.criar, name="criar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
    path("<int:pk>/mover/", views.mover, name="mover"),
]
