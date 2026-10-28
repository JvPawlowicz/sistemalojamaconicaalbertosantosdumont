from django.urls import path

from . import views

app_name = "agape"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.criar, name="criar"),
    path("caixa/", views.caixa, name="caixa"),
    path("inventario/", views.inventario, name="inventario"),
    path("inventario/item/novo/", views.item_form, name="item_novo"),
    path("inventario/item/<int:pk>/", views.item_form, name="item_editar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/confirmar/", views.confirmar, name="confirmar"),
    path("<int:pk>/participante/<int:irmao_pk>/", views.participante, name="participante"),
    path("<int:pk>/sincronizar/", views.sincronizar, name="sincronizar"),
    path("<int:pk>/visitante/", views.visitante_novo, name="visitante_novo"),
    path("<int:pk>/visitante/<int:visitante_pk>/excluir/", views.visitante_excluir, name="visitante_excluir"),
    path("<int:pk>/repasse/", views.repasse, name="repasse"),
    path("<int:pk>/encerrar/", views.encerrar, name="encerrar"),
]
