from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core import perfis as P
from apps.core.arquivos import servir_arquivo

from .forms import CorrespondenciaForm
from .models import Correspondencia


@login_required
def lista(request):
    itens = [c for c in Correspondencia.objects.all() if request.user.pode_ver_grau(c.grau_minimo)]
    return render(request, "expediente/lista.html", {"itens": itens, "pode_gerir": request.user.tem_perfil(P.SECRETARIO)})


@login_required
def novo(request):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    form = CorrespondenciaForm(request.POST or None, request.FILES or None, initial={"data": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        c = form.save(commit=False)
        c.registrada_por = request.user
        c.save()
        messages.success(request, "Correspondência registrada.")
        return redirect("expediente:lista")
    return render(request, "crud/form.html", {"form": form, "titulo": "Registrar correspondência", "multipart": True,
                                              "cancelar_url": "/expediente/"})


@login_required
def arquivo(request, pk):
    c = get_object_or_404(Correspondencia, pk=pk)
    if not request.user.pode_ver_grau(c.grau_minimo):
        raise PermissionDenied
    return servir_arquivo(c.arquivo)
