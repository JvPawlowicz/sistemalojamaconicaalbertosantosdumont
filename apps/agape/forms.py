from django import forms

from apps.core.forms import FormBase, ModelFormBase

from .models import Agape, AgapeLancamento, Item, Visitante


class AgapeForm(ModelFormBase):
    class Meta:
        model = Agape
        fields = ["sessao", "data", "descricao", "valor_por_pessoa", "observacao"]
        widgets = {"data": forms.DateInput(), "observacao": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sessao"].required = False
        self.fields["sessao"].label_from_instance = lambda s: f"{s.data_hora:%d/%m/%Y} · {s.get_tipo_display()}"


class VisitanteForm(ModelFormBase):
    class Meta:
        model = Visitante
        fields = ["nome", "loja"]


class LancamentoForm(ModelFormBase):
    class Meta:
        model = AgapeLancamento
        fields = ["tipo", "categoria", "valor", "data", "descricao", "agape"]
        widgets = {"data": forms.DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agape"].required = False

    def clean_valor(self):
        v = self.cleaned_data["valor"]
        if v <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")
        return v


class ItemForm(ModelFormBase):
    class Meta:
        model = Item
        fields = ["nome", "unidade", "minimo", "ativo"]


class MovimentoForm(FormBase):
    item = forms.ModelChoiceField(Item.objects.filter(ativo=True), label="Item")
    tipo = forms.ChoiceField(choices=[("entrada", "Entrada (compra/doação)"), ("consumo", "Consumo no Ágape"),
                                      ("perda", "Perda / quebra"), ("ajuste", "Ajuste de contagem (informe o estoque real)")])
    quantidade = forms.IntegerField(min_value=0, label="Quantidade")
    data = forms.DateField(label="Data", widget=forms.DateInput())
    agape = forms.ModelChoiceField(Agape.objects.all(), required=False, label="Ágape (consumo)")
    custo_total = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2,
                                     label="Custo da compra (lança saída no caixa do Ágape)")
    observacao = forms.CharField(required=False, max_length=200, label="Observação")
