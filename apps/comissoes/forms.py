from django import forms
from django.forms import inlineformset_factory

from apps.core.forms import ModelFormBase

from .models import Comissao, MembroComissao


class ComissaoForm(ModelFormBase):
    class Meta:
        model = Comissao
        fields = ["nome", "tipo", "ano", "objetivo", "prazo", "candidato", "encerrada", "parecer", "parecer_em"]
        widgets = {"prazo": forms.DateInput(), "parecer_em": forms.DateInput()}


class MembroForm(ModelFormBase):
    class Meta:
        model = MembroComissao
        fields = ["irmao", "papel"]


MembroFormSet = inlineformset_factory(Comissao, MembroComissao, form=MembroForm, extra=3, can_delete=True)
