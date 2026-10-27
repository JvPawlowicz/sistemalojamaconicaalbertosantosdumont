from apps.core.forms import ModelFormBase

from .models import Cargo


class CargoForm(ModelFormBase):
    class Meta:
        model = Cargo
        fields = ["nome", "sigla", "ordem", "descricao", "ativo"]
