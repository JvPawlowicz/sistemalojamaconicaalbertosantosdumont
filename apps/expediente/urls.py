from django.urls import path

from . import views

app_name = "expediente"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
    path("<int:pk>/arquivo/", views.arquivo, name="arquivo"),
]
