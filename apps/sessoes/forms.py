from django import forms

from apps.core.forms import FormBase, ModelFormBase

from .models import Sessao


class SessaoForm(ModelFormBase):
    class Meta:
        model = Sessao
        fields = ["data_hora", "tipo", "grau", "local", "pauta", "expediente", "status", "observacoes"]
        widgets = {
            "data_hora": forms.DateTimeInput(),
            "pauta": forms.Textarea(attrs={"rows": 6}),
            "expediente": forms.Textarea(attrs={"rows": 4}),
        }
