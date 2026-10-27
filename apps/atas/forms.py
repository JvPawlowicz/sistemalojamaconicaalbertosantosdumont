from django import forms

from apps.core.forms import ModelFormBase

from .models import Ata, ModeloTexto


class AtaForm(ModelFormBase):
    class Meta:
        model = Ata
        fields = ["numero", "livro", "folha", "conteudo"]
        widgets = {"conteudo": forms.Textarea(attrs={"rows": 24, "id": "ata-conteudo", "spellcheck": "true"})}


class ModeloTextoForm(ModelFormBase):
    class Meta:
        model = ModeloTexto
        fields = ["titulo", "atalho", "categoria", "texto", "ativo"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 8})}
