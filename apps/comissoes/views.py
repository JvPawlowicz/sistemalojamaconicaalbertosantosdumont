from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core import perfis as P
from apps.core.models import AnoMaconico

from .forms import ComissaoForm, MembroFormSet
from .models import Comissao


def _ver(user):
    if not (user.pode_ver_grau(P.MESTRE) or user.tem_perfil(P.SECRETARIO)):
        raise PermissionDenied


@login_required
def lista(request):
    _ver(request.user)
    return render(request, "comissoes/lista.html", {
        "comissoes": Comissao.objects.select_related("ano").prefetch_related("membros__irmao"),
        "pode_gerir": request.user.tem_perfil(P.SECRETARIO),
    })


@login_required
def editar(request, pk=None):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    comissao = get_object_or_404(Comissao, pk=pk) if pk else None
    form = ComissaoForm(request.POST or None, instance=comissao, initial={"ano": AnoMaconico.atual()} if not pk else None)
    formset = MembroFormSet(request.POST or None, instance=comissao)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        formset = MembroFormSet(request.POST, instance=obj)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Comissão salva.")
            return redirect("comissoes:lista")
    return render(request, "comissoes/form.html", {"form": form, "formset": formset,
                                                   "titulo": "Editar comissão" if pk else "Nova comissão"})
