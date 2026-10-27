from django import forms

from apps.core.arquivos import validar_arquivo
from apps.core.forms import ModelFormBase

from .models import Correspondencia


class CorrespondenciaForm(ModelFormBase):
    class Meta:
        model = Correspondencia
        fields = ["tipo", "data", "assunto", "origem_destino", "descricao", "arquivo", "grau_minimo", "leva_a_sessao"]
        widgets = {"data": forms.DateInput()}

    def clean_arquivo(self):
        return validar_arquivo(self.cleaned_data.get("arquivo"))
