from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P

from .forms import EmprestimoForm, ItemForm
from .models import Emprestimo, ItemPatrimonio


def _gerir(user):
    if not user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied


@login_required
def lista(request):
    _gerir(request.user)
    q = request.GET.get("q", "").strip()
    itens = ItemPatrimonio.objects.select_related("responsavel")
    if q:
        itens = itens.filter(nome__icontains=q)
    return render(request, "patrimonio/lista.html", {"itens": itens, "q": q})


@login_required
def novo(request):
    _gerir(request.user)
    form = ItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Item cadastrado.")
        return redirect("patrimonio:lista")
    return render(request, "crud/form.html", {"form": form, "titulo": "Novo item de patrimônio",
                                              "cancelar_url": "/patrimonio/"})


@login_required
def editar(request, pk):
    _gerir(request.user)
    item = get_object_or_404(ItemPatrimonio, pk=pk)
    form = ItemForm(request.POST or None, instance=item)
    emp = EmprestimoForm(prefix="emp")
    if request.method == "POST" and "emp-irmao" not in request.POST:
        if form.is_valid():
            form.save()
            messages.success(request, "Item atualizado.")
            return redirect("patrimonio:lista")
    elif request.method == "POST":
        emp = EmprestimoForm(request.POST, prefix="emp")
        if emp.is_valid() and item.emprestavel and not item.emprestado_a:
            Emprestimo.objects.create(item=item, irmao=emp.cleaned_data["irmao"], emprestado_em=timezone.localdate(),
                                      devolver_ate=emp.cleaned_data["devolver_ate"])
            messages.success(request, "Empréstimo registrado.")
            return redirect("patrimonio:editar", pk=pk)
    return render(request, "patrimonio/item.html", {
        "form": form, "item": item, "emp": emp, "emprestimos": item.emprestimos.select_related("irmao")[:10],
    })


@login_required
@require_POST
def devolver(request, pk):
    _gerir(request.user)
    e = get_object_or_404(Emprestimo, pk=pk)
    e.devolvido_em = timezone.localdate()
    e.save()
    messages.success(request, "Devolução registrada.")
    return redirect("patrimonio:editar", pk=e.item_id)
