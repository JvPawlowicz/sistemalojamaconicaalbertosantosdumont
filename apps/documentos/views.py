from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.core.arquivos import servir_arquivo

from .forms import DocumentoForm
from .models import Documento


def _visivel(user, doc):
    if not user.pode_ver_grau(doc.grau_minimo):
        raise PermissionDenied


@login_required
def lista(request):
    categoria = request.GET.get("categoria", "")
    q = request.GET.get("q", "").strip()
    docs = Documento.objects.all()
    if categoria in Documento.Categoria.values:
        docs = docs.filter(categoria=categoria)
    if q:
        from django.db.models import Q

        docs = docs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q) | Q(texto_extraido__icontains=q))
    docs = [d for d in docs if request.user.pode_ver_grau(d.grau_minimo)]
    for d in docs:
        d.achado = d.trecho(q) if q and q.lower() not in d.titulo.lower() else ""
    return render(request, "documentos/lista.html", {
        "docs": docs, "categoria": categoria, "q": q, "categorias": Documento.Categoria.choices,
        "pode_gerir": request.user.tem_perfil(P.SECRETARIO),
    })


@login_required
def enviar(request):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    form = DocumentoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.save(commit=False)
        d.enviado_por = request.user
        d.save()
        messages.success(request, "Documento enviado.")
        return redirect("documentos:ver", pk=d.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Enviar documento", "multipart": True,
                                              "cancelar_url": "/documentos/"})


@login_required
def ver(request, pk):
    """Visualizador embutido: PDF e imagens abrem na própria página."""
    doc = get_object_or_404(Documento, pk=pk)
    _visivel(request.user, doc)
    return render(request, "documentos/ver.html", {"doc": doc, "pode_gerir": request.user.tem_perfil(P.SECRETARIO)})


@login_required
def arquivo(request, pk):
    doc = get_object_or_404(Documento, pk=pk)
    _visivel(request.user, doc)
    return servir_arquivo(doc.arquivo, inline=not request.GET.get("baixar"))


@login_required
@require_POST
def excluir(request, pk):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    doc = get_object_or_404(Documento, pk=pk)
    doc.arquivo.delete(save=False)
    doc.delete()
    messages.success(request, "Documento excluído.")
    return redirect("documentos:lista")
