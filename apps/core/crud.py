"""Blocos reutilizáveis para listas, formulários e confirmações."""
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from .mixins import PerfilRequeridoMixin


class ListaView(PerfilRequeridoMixin, TemplateView):
    """Lista genérica: subclasses definem titulo, colunas e get_objetos()."""

    template_name = "crud/lista.html"
    titulo = ""
    subtitulo = ""
    colunas: list = []
    url_novo = None
    rotulo_novo = "Novo"
    vazio = "Nada cadastrado ainda."

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
        ctx["linhas"] = [self.linha(o) for o in self.get_objetos()]
        ctx["url_novo"] = self.url_novo
        ctx["rotulo_novo"] = self.rotulo_novo
        ctx["vazio"] = self.vazio
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
