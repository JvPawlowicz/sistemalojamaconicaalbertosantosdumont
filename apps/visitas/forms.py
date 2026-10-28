from django import forms

from apps.core.arquivos import validar_arquivo
from apps.core.forms import ModelFormBase
from apps.irmaos.models import telefone_validator

from .models import LojaCoirma, VisitaRealizada, Visitante


class VisitaRealizadaForm(ModelFormBase):
    class Meta:
        model = VisitaRealizada
        fields = ["irmao", "loja", "loja_nome", "loja_numero", "oriente", "potencia", "data", "grau_sessao", "certificado",
                  "observacao"]
        widgets = {"data": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.irmaos.models import Irmao

        self.fields["irmao"].queryset = Irmao.objects.filter(is_active=True, grau__isnull=False)

    def clean_certificado(self):
        return validar_arquivo(self.cleaned_data.get("certificado"))

    def clean(self):
        dados = super().clean()
        loja = dados.get("loja")
        if loja:  # preenche a partir do diretório quando o campo manual ficou em branco
            dados["loja_nome"] = dados.get("loja_nome") or loja.nome
            dados["loja_numero"] = dados.get("loja_numero") or loja.numero
            dados["oriente"] = dados.get("oriente") or loja.oriente
            dados["potencia"] = dados.get("potencia") or loja.potencia
        elif not dados.get("loja_nome"):
            self.add_error("loja_nome", "Escolha uma loja do diretório ou informe o nome.")
        return dados


class LojaCoirmaForm(ModelFormBase):
    class Meta:
        model = LojaCoirma
        fields = ["nome", "numero", "oriente", "potencia", "rito", "endereco", "dia_sessoes", "contato_nome",
                  "contato_telefone", "contato_email", "observacao"]


class VisitanteForm(ModelFormBase):
    whatsapp = forms.CharField(required=False, max_length=15, validators=[telefone_validator], label="WhatsApp")

    class Meta:
        model = Visitante
        fields = ["nome", "grau", "loja_nome", "loja_numero", "oriente", "potencia", "registro", "email", "whatsapp"]
