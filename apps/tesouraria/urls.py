from django.urls import path

from . import views

app_name = "tesouraria"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("mensalidades/", views.mensalidades, name="mensalidades"),
    path("mensalidades/gerar/", views.gerar, name="gerar"),
    path("mensalidades/cobrar-todos/", views.cobrar_todos, name="cobrar_todos"),
    path("mensalidades/<int:pk>/baixa/", views.baixa, name="baixa"),
    path("mensalidades/<int:pk>/estornar/", views.estornar, name="estornar"),
    path("mensalidades/<int:pk>/dispensar/", views.dispensar, name="dispensar"),
    path("mensalidades/<int:pk>/cobrar/", views.cobrar_email, name="cobrar_email"),
    path("mensalidades/<int:pk>/boleto/", views.boleto, name="boleto"),
    path("caixa/", views.caixa, name="caixa"),
    path("caixa/<int:pk>/comprovante/", views.comprovante, name="comprovante"),
    path("categorias/", views.categorias, name="categorias"),
    path("orcamento/", views.orcamento, name="orcamento"),
    path("minhas/", views.minhas, name="minhas"),
    path("extrato/<int:pk>.pdf", views.extrato_pdf, name="extrato_pdf"),
]
