from django import forms

from .models import Loja


def _mascara_do_campo(nome):
    for chave, mascara in (("telefone", "telefone"), ("whatsapp", "telefone"), ("cpf", "cpf"), ("cnpj", "cnpj"),
                           ("cep", "cep")):
        if chave in nome:
            return mascara
    return ""


class EstiloFormMixin:
    """Aplica as classes do tema e widgets HTML5 (data, hora) a todos os campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            if isinstance(campo, forms.DecimalField):
                campo.localize = True
                campo.widget = forms.TextInput(attrs={"inputmode": "decimal"})
            w = campo.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "check")
            elif isinstance(w, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                pass
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "input")
            else:
                w.attrs.setdefault("class", "input")
            if isinstance(w, forms.DateInput):
                w.input_type = "date"
                w.format = "%Y-%m-%d"
            elif isinstance(w, forms.DateTimeInput):
                w.input_type = "datetime-local"
                w.format = "%Y-%m-%dT%H:%M"
            mascara = _mascara_do_campo(nome)
            if mascara:
                w.attrs.setdefault("data-mask", mascara)
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 4)
            if campo.help_text:
                w.attrs.setdefault("aria-describedby", f"ajuda-{nome}")
            if campo.required and not isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("aria-required", "true")


class FormBase(EstiloFormMixin, forms.Form):
    pass


class ModelFormBase(EstiloFormMixin, forms.ModelForm):
    pass


class LojaForm(ModelFormBase):
    class Meta:
        model = Loja
        fields = [
            "nome", "numero", "oriente", "potencia", "rito", "cnpj", "endereco", "email_contato",
            "brasao", "cabecalho_documentos", "texto_legal", "mensalidade_dia_vencimento", "chave_pix", "intersticio_promocao_meses",
            "intersticio_elevacao_meses", "lembrete_sessao_horas", "cobranca_automatica",
            "limite_faltas_consecutivas", "frequencia_minima_percentual", "quorum_minimo", "multa_atraso_percentual",
            "juros_mensal_percentual", "dias_carencia_atraso",
        ]
        widgets = {"cabecalho_documentos": forms.Textarea(attrs={"rows": 4}),
                   "texto_legal": forms.Textarea(attrs={"rows": 5})}


    def clean_brasao(self):
        from .arquivos import IMAGENS, validar_arquivo

        return validar_arquivo(self.cleaned_data.get("brasao"), IMAGENS)


class TokenForm(FormBase):
    token = forms.CharField(
        label="Código de 6 dígitos",
        max_length=8,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True}),
    )
