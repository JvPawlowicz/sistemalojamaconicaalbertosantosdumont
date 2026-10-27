from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.indice, name="indice"),
    path("<slug:slug>/", views.ver, name="ver"),
]
