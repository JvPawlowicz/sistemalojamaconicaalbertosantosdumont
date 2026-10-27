from django.urls import path

from . import views

app_name = "candidatos"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("novo/", views.criar, name="criar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/mover/", views.mover, name="mover"),
]
