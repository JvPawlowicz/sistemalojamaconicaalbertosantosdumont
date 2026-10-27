from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.indice, name="indice"),
    path("pacote-fiscal.pdf", views.pacote_fiscal, name="pacote_fiscal"),
    path("<slug:slug>/", views.ver, name="ver"),
]
