from django import forms

from apps.core.arquivos import validar_arquivo
from apps.core.forms import ModelFormBase
from apps.irmaos.models import telefone_validator

from .models import VisitaRealizada, Visitante


class VisitaRealizadaForm(ModelFormBase):
    class Meta:
        model = VisitaRealizada
        fields = ["irmao", "loja_nome", "loja_numero", "oriente", "potencia", "data", "grau_sessao", "certificado",
                  "observacao"]
        widgets = {"data": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.irmaos.models import Irmao

        self.fields["irmao"].queryset = Irmao.objects.filter(is_active=True, grau__isnull=False)

    def clean_certificado(self):
        return validar_arquivo(self.cleaned_data.get("certificado"))


class VisitanteForm(ModelFormBase):
    whatsapp = forms.CharField(required=False, max_length=15, validators=[telefone_validator], label="WhatsApp")

    class Meta:
        model = Visitante
        fields = ["nome", "grau", "loja_nome", "loja_numero", "oriente", "potencia", "registro", "email", "whatsapp"]
