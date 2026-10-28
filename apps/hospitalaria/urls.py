from django.urls import path

from . import views

app_name = "hospitalaria"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("caso/novo/", views.caso_novo, name="caso_novo"),
    path("caso/<int:pk>/", views.caso, name="caso"),
    path("caso/<int:pk>/status/", views.caso_status, name="caso_status"),
    path("tronco/", views.tronco, name="tronco"),
    path("tronco/sessao/<int:sessao_pk>/", views.tronco_rapido, name="tronco_rapido"),
    path("tronco/<int:pk>/comprovante/", views.comprovante, name="comprovante"),
]
