from django import forms

from apps.core.forms import FormBase, ModelFormBase
from apps.irmaos.models import Irmao

from .models import ItemPatrimonio


class ItemForm(ModelFormBase):
    class Meta:
        model = ItemPatrimonio
        fields = ["nome", "categoria", "quantidade", "estado", "local", "responsavel", "valor", "data_aquisicao",
                  "emprestavel", "observacao"]
        widgets = {"data_aquisicao": forms.DateInput()}


class EmprestimoForm(FormBase):
    irmao = forms.ModelChoiceField(Irmao.objects.filter(is_active=True, grau__isnull=False), label="Irmão")
    devolver_ate = forms.DateField(required=False, widget=forms.DateInput(), label="Devolver até")
