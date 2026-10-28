from django.urls import path

from . import views, views_extra

app_name = "irmaos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.criar, name="criar"),
    path("meu-perfil/", views.meu_perfil, name="meu_perfil"),
    path("carteirinha/", views_extra.carteirinha, name="carteirinha"),
    path("carteirinha/pdf/", views_extra.carteirinha_pdf, name="carteirinha_pdf"),
    path("importar/", views_extra.importar, name="importar"),
    path("importar/modelo.csv", views_extra.modelo_importacao, name="modelo_importacao"),
    path("categorias/", views.categorias, name="categorias"),
    path("categorias/<int:pk>/", views.categoria_editar, name="categoria_editar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/resetar-2fa/", views_extra.resetar_2fa, name="resetar_2fa"),
    path("<int:pk>/alternar-acesso/", views_extra.alternar_acesso, name="alternar_acesso"),
    path("<int:pk>/convidar/", views.convidar, name="convidar"),
]
