from django import forms

from apps.core.arquivos import validar_arquivo
from apps.core.forms import FormBase, ModelFormBase
from apps.irmaos.models import Irmao

from .models import Acompanhamento, CasoHospitalaria, MovimentoTronco


class CasoForm(ModelFormBase):
    class Meta:
        model = CasoHospitalaria
        fields = ["irmao", "beneficiado", "parentesco", "tipo", "descricao", "data_inicio", "responsavel"]
        widgets = {"data_inicio": forms.DateInput(), "descricao": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        q = Irmao.objects.filter(is_active=True, grau__isnull=False)
        self.fields["irmao"].queryset = q
        self.fields["responsavel"].queryset = q
        self.fields["irmao"].required = False

    def clean(self):
        d = super().clean()
        if not d.get("irmao") and not d.get("beneficiado"):
            self.add_error("irmao", "Escolha o irmão ou informe o nome do beneficiado.")
        return d


class AcompanhamentoForm(ModelFormBase):
    class Meta:
        model = Acompanhamento
        fields = ["data", "tipo", "descricao"]
        widgets = {"data": forms.DateInput(), "descricao": forms.Textarea(attrs={"rows": 3})}


class TroncoForm(ModelFormBase):
    class Meta:
        model = MovimentoTronco
        fields = ["tipo", "valor", "data", "descricao", "sessao", "caso", "comprovante"]
        widgets = {"data": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["caso"].queryset = CasoHospitalaria.objects.filter(status="acompanhando")
        self.fields["caso"].required = False
        self.fields["sessao"].required = False
        self.fields["caso"].label_from_instance = lambda c: f"{c.nome} ({c.get_tipo_display()})"

    def clean_valor(self):
        v = self.cleaned_data["valor"]
        if v <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")
        return v

    def clean_comprovante(self):
        return validar_arquivo(self.cleaned_data.get("comprovante"))
