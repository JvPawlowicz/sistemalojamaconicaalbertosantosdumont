from django import forms

from apps.core.forms import ModelFormBase
from apps.irmaos.models import Irmao, telefone_validator

from .models import Candidato, Parecer


class CandidatoForm(ModelFormBase):
    telefone = forms.CharField(required=False, max_length=15, validators=[telefone_validator])

    class Meta:
        model = Candidato
        fields = ["nome", "data_nascimento", "profissao", "telefone", "email", "proposto_por", "data_proposta",
                  "observacoes"]
        widgets = {"data_nascimento": forms.DateInput(), "data_proposta": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proposto_por"].queryset = Irmao.objects.filter(is_active=True, grau=3)


class ParecerForm(ModelFormBase):
    class Meta:
        model = Parecer
        fields = ["irmao", "data", "favoravel", "texto"]
        widgets = {"data": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["irmao"].queryset = Irmao.objects.filter(is_active=True, grau=3)
        self.fields["irmao"].label = "Sindicante"
