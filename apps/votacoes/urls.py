from django.urls import path

from . import views

app_name = "votacoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nova/", views.criar, name="criar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/votar/", views.votar, name="votar"),
    path("<int:pk>/abrir/", views.abrir, name="abrir"),
    path("<int:pk>/encerrar/", views.encerrar, name="encerrar"),
    path("<int:pk>/aplicar/", views.aplicar_resultado, name="aplicar"),
]
