from django import forms

from apps.core.forms import ModelFormBase

from .models import Votacao


class VotacaoForm(ModelFormBase):
    class Meta:
        model = Votacao
        fields = ["titulo", "descricao", "tipo", "sessao", "candidato", "grau_minimo", "exigir_presenca", "negativos_maximos"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.candidatos.models import Candidato

        self.fields["candidato"].queryset = Candidato.objects.exclude(etapa__in=["iniciado", "reprovado", "desistiu"])
        self.fields["candidato"].required = False
        self.fields["sessao"].required = False

    def clean(self):
        d = super().clean()
        if d.get("tipo") == Votacao.Tipo.ESCRUTINIO and not d.get("candidato"):
            self.add_error("candidato", "Escolha o candidato do escrutínio.")
        return d
