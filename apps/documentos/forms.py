from apps.core.arquivos import validar_arquivo
from apps.core.forms import ModelFormBase

from .models import Documento


class DocumentoForm(ModelFormBase):
    class Meta:
        model = Documento
        fields = ["titulo", "categoria", "descricao", "arquivo", "grau_minimo"]

    def clean_arquivo(self):
        return validar_arquivo(self.cleaned_data.get("arquivo"))
