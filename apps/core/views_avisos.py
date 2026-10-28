"""Mural de avisos da Loja."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import perfis as P
from .comunicacao import enviar_email
from .forms import ModelFormBase
from .models import Aviso, Loja


class AvisoForm(ModelFormBase):
    enviar_email = forms.BooleanField(required=False, label="Avisar também por e-mail (irmãos do grau)")

    class Meta:
        model = Aviso
        fields = ["titulo", "texto", "grau_minimo", "fixado", "publicar_em", "expira_em"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 6}), "publicar_em": forms.DateTimeInput(),
                   "expira_em": forms.DateTimeInput()}


def _gerir(user):
    if not user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied


@login_required
def avisos(request):
    gerir = request.user.tem_perfil(P.SECRETARIO)
    return render(request, "core/avisos.html", {
        "avisos": Aviso.vigentes_para(request.user), "pode_gerir": gerir,
        "todos": Aviso.objects.all()[:50] if gerir else [],
    })


@login_required
def aviso_form(request, pk=None):
    _gerir(request.user)
    aviso = get_object_or_404(Aviso, pk=pk) if pk else None
    form = AvisoForm(request.POST or None, instance=aviso, initial={"publicar_em": timezone.now()} if not pk else None)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not a.pk:
            a.criado_por = request.user
        a.save()
        if form.cleaned_data.get("enviar_email") and not a.enviado_por_email_em:
            from apps.irmaos.models import Irmao

            loja = Loja.atual()
            for i in Irmao.objects.filter(is_active=True, grau__gte=a.grau_minimo).exclude(email=""):
                enviar_email(i.email, f"Aviso: {a.titulo}", f"{a.texto}\n\nVeja no sistema: {request.build_absolute_uri(reverse('core:avisos'))}\n\n{loja.nome}", contexto="aviso")
            a.enviado_por_email_em = timezone.now()
            a.save(update_fields=["enviado_por_email_em"])
        messages.success(request, "Aviso publicado.")
        return redirect("core:avisos")
    return render(request, "crud/form.html", {"form": form, "titulo": "Editar aviso" if pk else "Novo aviso",
                                              "cancelar_url": reverse("core:avisos")})


@login_required
@require_POST
def aviso_excluir(request, pk):
    _gerir(request.user)
    get_object_or_404(Aviso, pk=pk).delete()
    messages.success(request, "Aviso excluído.")
    return redirect("core:avisos")
