from django import forms

from apps.core.arquivos import validar_arquivo
from apps.core.forms import FormBase, ModelFormBase

from .models import CategoriaFinanceira, Lancamento, MovimentoCaixa, Orcamento


class MovimentoForm(ModelFormBase):
    class Meta:
        model = MovimentoCaixa
        fields = ["tipo", "categoria", "valor", "data", "descricao", "comprovante"]
        widgets = {"data": forms.DateInput()}

    def clean_comprovante(self):
        return validar_arquivo(self.cleaned_data.get("comprovante"))

    def clean(self):
        dados = super().clean()
        cat, tipo = dados.get("categoria"), dados.get("tipo")
        if cat and tipo and cat.tipo != tipo:
            self.add_error("categoria", "A categoria não corresponde ao tipo (receita/despesa).")
        if dados.get("valor") is not None and dados["valor"] <= 0:
            self.add_error("valor", "Informe um valor maior que zero.")
        return dados


class BaixaForm(FormBase):
    data_pagamento = forms.DateField(label="Data do pagamento", widget=forms.DateInput())
    valor_pago = forms.DecimalField(label="Valor pago (R$)", max_digits=10, decimal_places=2, min_value=0.01)
    forma = forms.ChoiceField(label="Forma de pagamento", choices=Lancamento.Forma.choices)
    observacao = forms.CharField(label="Observação", required=False, max_length=200)


class CategoriaFinanceiraForm(ModelFormBase):
    class Meta:
        model = CategoriaFinanceira
        fields = ["nome", "tipo", "ativa"]


class LancamentoAvulsoForm(ModelFormBase):
    class Meta:
        model = Lancamento
        fields = ["irmao", "descricao", "competencia", "valor", "vencimento", "observacao"]
        widgets = {"competencia": forms.DateInput(), "vencimento": forms.DateInput()}


class BoletoForm(ModelFormBase):
    class Meta:
        model = Lancamento
        fields = ["boleto"]

    def clean_boleto(self):
        return validar_arquivo(self.cleaned_data.get("boleto"), {"pdf", "png", "jpg", "jpeg"})


class ExtratoForm(forms.Form):
    arquivo = forms.FileField(label="Extrato bancário (OFX)", help_text="Baixe o OFX no internet banking (extrato do mês).")
