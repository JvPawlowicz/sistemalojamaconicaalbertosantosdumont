from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core import perfis as P

from .forms import CategoriaForm, FamiliarFormSet, IrmaoForm, MeuPerfilForm
from .models import CategoriaIrmao, Irmao


def _pode_gerir(user):
    return user.tem_perfil(P.SECRETARIO)


@login_required
def lista(request):
    q = request.GET.get("q", "").strip()
    grau = request.GET.get("grau", "")
    situacao = request.GET.get("situacao", "ativo")
    qs = Irmao.objects.filter(grau__isnull=False)
    if q:
        qs = qs.filter(Q(nome_completo__icontains=q) | Q(profissao__icontains=q) | Q(matricula__icontains=q))
    if grau in ("1", "2", "3"):
        qs = qs.filter(grau=int(grau))
    if situacao:
        qs = qs.filter(situacao=situacao)
    return render(request, "irmaos/lista.html", {
        "irmaos": qs, "q": q, "grau": grau, "situacao": situacao,
        "situacoes": Irmao.Situacao.choices, "graus": P.GRAU_CHOICES, "pode_gerir": _pode_gerir(request.user),
    })


@login_required
def detalhe(request, pk):
    irmao = get_object_or_404(Irmao, pk=pk, grau__isnull=False)
    proprio = irmao.pk == request.user.pk
    completo = proprio or _pode_gerir(request.user)
    from apps.cargos.models import Gestao
    from apps.core.models import AnoMaconico

    return render(request, "irmaos/detalhe.html", {
        "irmao": irmao, "completo": completo, "proprio": proprio, "pode_gerir": _pode_gerir(request.user),
        "cargos": Gestao.objects.filter(irmao=irmao).select_related("cargo", "ano").order_by("-ano__inicio"),
        "ano": AnoMaconico.atual(), "cerimonias": irmao.cerimonias.all(),
    })


def _enviar_convite(request, irmao):
    form = PasswordResetForm({"email": irmao.email})
    if form.is_valid():
        form.save(
            request=request, use_https=request.is_secure(),
            subject_template_name="registration/convite_assunto.txt",
            email_template_name="registration/convite_email.txt",
        )


@login_required
def criar(request):
    if not _pode_gerir(request.user):
        raise PermissionDenied
    form = IrmaoForm(request.POST or None, request.FILES or None, editor=request.user)
    formset = FamiliarFormSet(request.POST or None, instance=Irmao())
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        irmao = form.save()
        formset.instance = irmao
        formset.save()
        if request.POST.get("enviar_convite") == "on":
            _enviar_convite(request, irmao)
            messages.info(request, "Convite para definir a senha enviado por e-mail.")
        messages.success(request, "Irmão cadastrado.")
        return redirect("irmaos:detalhe", pk=irmao.pk)
    return render(request, "irmaos/form.html", {"form": form, "formset": formset, "titulo": "Novo irmão", "novo": True})


@login_required
def editar(request, pk):
    if not _pode_gerir(request.user):
        raise PermissionDenied
    irmao = get_object_or_404(Irmao, pk=pk)
    form = IrmaoForm(request.POST or None, request.FILES or None, instance=irmao, editor=request.user)
    formset = FamiliarFormSet(request.POST or None, instance=irmao)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Cadastro atualizado.")
        return redirect("irmaos:detalhe", pk=irmao.pk)
    return render(request, "irmaos/form.html", {"form": form, "formset": formset, "titulo": irmao.nome_completo,
                                                "irmao": irmao})


@login_required
def meu_perfil(request):
    irmao = request.user
    form = MeuPerfilForm(request.POST or None, request.FILES or None, instance=irmao)
    formset = FamiliarFormSet(request.POST or None, instance=irmao)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Seus dados foram atualizados.")
        return redirect("irmaos:meu_perfil")
    return render(request, "irmaos/meu_perfil.html", {"form": form, "formset": formset, "irmao": irmao})


@login_required
def convidar(request, pk):
    if not _pode_gerir(request.user) or request.method != "POST":
        raise PermissionDenied
    irmao = get_object_or_404(Irmao, pk=pk)
    if not irmao.email:
        messages.error(request, "O irmão não tem e-mail cadastrado.")
    else:
        _enviar_convite(request, irmao)
        messages.success(request, "Convite para definir a senha enviado por e-mail.")
    return redirect("irmaos:detalhe", pk=pk)


@login_required
def categorias(request):
    if not request.user.tem_perfil(P.ADMINISTRADOR) and not request.user.tem_perfil(P.TESOUREIRO):
        raise PermissionDenied
    form = CategoriaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Categoria criada.")
        return redirect("irmaos:categorias")
    return render(request, "irmaos/categorias.html", {"categorias": CategoriaIrmao.objects.all(), "form": form})


@login_required
def categoria_editar(request, pk):
    if not request.user.tem_perfil(P.ADMINISTRADOR) and not request.user.tem_perfil(P.TESOUREIRO):
        raise PermissionDenied
    cat = get_object_or_404(CategoriaIrmao, pk=pk)
    form = CategoriaForm(request.POST or None, instance=cat)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Categoria atualizada.")
        return redirect("irmaos:categorias")
    return render(request, "irmaos/categorias.html", {"categorias": CategoriaIrmao.objects.all(), "form": form,
                                                       "editando": cat})
