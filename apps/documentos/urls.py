from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("enviar/", views.enviar, name="enviar"),
    path("<int:pk>/", views.ver, name="ver"),
    path("<int:pk>/arquivo/", views.arquivo, name="arquivo"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
]
