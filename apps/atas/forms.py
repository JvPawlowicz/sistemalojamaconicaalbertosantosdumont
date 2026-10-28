from django import forms

from apps.core.forms import ModelFormBase

from .models import Ata, ModeloTexto


class AtaForm(ModelFormBase):
    """Cadastro da ata. O texto vem do editor rico (HTML) e é sempre sanitizado antes de ser gravado."""

    class Meta:
        model = Ata
        fields = ["numero", "livro", "folha", "conteudo"]
        widgets = {"conteudo": forms.Textarea(attrs={"rows": 12, "id": "ata-conteudo"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = self.instance
        if inst and inst.pk and inst.formato == "texto" and not self.is_bound:
            from .sanitizar import texto_para_html

            self.initial["conteudo"] = texto_para_html(inst.conteudo)  # ata antiga: abre no editor rico

    def clean_conteudo(self):
        from .sanitizar import sanitizar_html, texto_simples

        html = sanitizar_html(self.cleaned_data.get("conteudo", ""))
        if not texto_simples(html):
            raise forms.ValidationError("A ata não pode ficar em branco.")
        return html

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.formato = "html"
        if commit:
            obj.save()
        return obj


class ModeloTextoForm(ModelFormBase):
    class Meta:
        model = ModeloTexto
        fields = ["titulo", "atalho", "categoria", "texto", "ativo"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 8})}
