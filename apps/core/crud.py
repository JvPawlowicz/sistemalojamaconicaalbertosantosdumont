"""Blocos reutilizáveis para listas, formulários e confirmações."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from .mixins import PerfilRequeridoMixin


def paginar(request, queryset, por_pagina=25):
    """Página atual de um queryset/lista (?pagina=N), tolerante a valores inválidos."""
    return Paginator(queryset, por_pagina).get_page(request.GET.get("pagina"))


class ListaView(PerfilRequeridoMixin, TemplateView):
    """Lista genérica: subclasses definem titulo, colunas e get_objetos()."""

    template_name = "crud/lista.html"
    titulo = ""
    subtitulo = ""
    colunas: list = []
    url_novo = None
    rotulo_novo = "Novo"
    vazio = "Nada cadastrado ainda."
    acoes_extra: list = []
    por_pagina = 25

    def get_objetos(self):
        raise NotImplementedError

    def linha(self, obj):
        """Devolve (células, url). Padrão: usa self.colunas = [(rótulo, função)]."""
        return [fn(obj) for _, fn in self.colunas], self.url_de(obj)

    def url_de(self, obj):
        return None

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["titulo"] = self.titulo
        ctx["subtitulo"] = self.subtitulo
        ctx["cabecalho"] = [c for c, _ in self.colunas]
        pagina = paginar(self.request, self.get_objetos(), self.por_pagina)
        ctx["pagina"] = pagina
        ctx["linhas"] = [self.linha(o) for o in pagina]
        ctx["url_novo"] = self.url_novo
        ctx["rotulo_novo"] = self.rotulo_novo
        ctx["vazio"] = self.vazio
        ctx["acoes_extra"] = self.acoes_extra
        ctx.update(self.extra())
        return ctx

    def extra(self):
        return {}


class FormularioMixin(PerfilRequeridoMixin, SuccessMessageMixin):
    template_name = "crud/form.html"
    titulo = ""
    success_message = "Salvo com sucesso."
    cancelar_url = None

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["titulo"] = self.titulo
        ctx["cancelar_url"] = self.cancelar_url or self.get_success_url()
        return ctx


class CriarView(FormularioMixin, CreateView):
    pass


class EditarView(FormularioMixin, UpdateView):
    pass


class ExcluirView(PerfilRequeridoMixin, DeleteView):
    template_name = "crud/confirmar.html"
    titulo = "Excluir"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Excluído.")
        return resp

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["titulo"] = self.titulo
        ctx["cancelar_url"] = self.get_success_url()
        return ctx
