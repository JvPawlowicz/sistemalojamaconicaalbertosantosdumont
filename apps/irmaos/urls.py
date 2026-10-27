from django.urls import path

from . import views

app_name = "irmaos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.criar, name="criar"),
    path("meu-perfil/", views.meu_perfil, name="meu_perfil"),
    path("categorias/", views.categorias, name="categorias"),
    path("categorias/<int:pk>/", views.categoria_editar, name="categoria_editar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/convidar/", views.convidar, name="convidar"),
]
