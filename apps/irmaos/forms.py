from django import forms
from django.forms import inlineformset_factory
from django.utils.text import slugify

from apps.core import perfis as P
from apps.core.forms import ModelFormBase

from .models import CategoriaIrmao, Familiar, Irmao

CAMPOS_PESSOAIS = [
    "cpf", "rg", "data_nascimento", "telefone", "whatsapp", "foto", "cep", "logradouro", "numero",
    "complemento", "bairro", "cidade", "uf", "contato_emergencia_nome", "contato_emergencia_telefone",
    "formacao_academica", "profissao", "empresa", "plano_saude", "plano_funeral",
]
DATAS = ("data_nascimento", "data_iniciacao", "data_promocao", "data_elevacao")


class IrmaoForm(ModelFormBase):
    """Cadastro completo (Secretário/Venerável)."""

    perfis = forms.MultipleChoiceField(
        choices=P.PERFIL_CHOICES, required=False, widget=forms.CheckboxSelectMultiple, label="Perfis de acesso"
    )

    class Meta:
        model = Irmao
        fields = [
            "nome_completo", "email", "username", "matricula", "grau", "situacao", "categoria",
            "data_iniciacao", "data_promocao", "data_elevacao", "is_active",
        ] + CAMPOS_PESSOAIS
        widgets = {d: forms.DateInput() for d in DATAS}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        self.fields["email"].required = True
        self.fields["username"].required = False
        self.fields["username"].help_text = "Em branco: gerado a partir do nome."
        self.fields["categoria"].queryset = CategoriaIrmao.objects.filter(ativo=True)
        self.fields["is_active"].label = "Acesso ao sistema habilitado"
        escolhas = P.PERFIL_CHOICES
        if editor is not None and not editor.eh_desenvolvedor:
            escolhas = [c for c in escolhas if c[0] != P.DESENVOLVEDOR]
        self.fields["perfis"].choices = escolhas
        if self.instance.pk:
            self.fields["perfis"].initial = self.instance.perfis

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if username:
            return username
        base = slugify(self.cleaned_data.get("nome_completo", "")).replace("-", ".") or "irmao"
        candidato, n = base, 1
        while Irmao.objects.filter(username=candidato).exclude(pk=self.instance.pk).exists():
            n += 1
            candidato = f"{base}{n}"
        return candidato

    def clean(self):
        dados = super().clean()
        # preserva perfil Desenvolvedor se quem edita não é desenvolvedor
        if self.instance.pk and self.editor is not None and not self.editor.eh_desenvolvedor:
            if P.DESENVOLVEDOR in (self.instance.perfis or []):
                dados["perfis"] = list(dados.get("perfis", [])) + [P.DESENVOLVEDOR]
        return dados

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.perfis = list(self.cleaned_data.get("perfis", []))
        if self.editor is not None and self.editor.eh_desenvolvedor:
            # painel técnico (Django Admin) só para o Desenvolvedor; só outro Desenvolvedor altera isso
            obj.is_superuser = obj.is_staff = P.DESENVOLVEDOR in obj.perfis
        if not obj.pk:
            obj.set_unusable_password()
        if commit:
            obj.save()
        return obj


class MeuPerfilForm(ModelFormBase):
    """O próprio irmão atualiza seus dados de contato e pessoais."""

    class Meta:
        model = Irmao
        fields = ["email", "telefone", "whatsapp", "foto", "cep", "logradouro", "numero", "complemento", "bairro",
                  "cidade", "uf", "contato_emergencia_nome", "contato_emergencia_telefone", "formacao_academica",
                  "profissao", "empresa", "plano_saude", "plano_funeral"]


class FamiliarForm(ModelFormBase):
    class Meta:
        model = Familiar
        fields = ["parentesco", "nome", "data_nascimento", "telefone"]
        widgets = {"data_nascimento": forms.DateInput()}


FamiliarFormSet = inlineformset_factory(Irmao, Familiar, form=FamiliarForm, extra=2, can_delete=True)


class CategoriaForm(ModelFormBase):
    class Meta:
        model = CategoriaIrmao
        fields = ["nome", "valor_mensal", "isento", "ativo"]
