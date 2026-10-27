from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P

from apps.sessoes.models import Sessao

from .forms import CandidatoForm, ParecerForm
from .models import Candidato


def _ver(user):
    """Dados de candidatos são sigilosos: Mestres, Secretário e Venerável."""
    if not (user.pode_ver_grau(P.MESTRE) or user.tem_perfil(P.SECRETARIO)):
        raise PermissionDenied


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


@login_required
def painel(request):
    _ver(request.user)
    colunas = []
    for valor, rotulo in Candidato.Etapa.choices:
        colunas.append((rotulo, Candidato.objects.filter(etapa=valor).select_related("proposto_por")))
    return render(request, "candidatos/painel.html", {"colunas": colunas, "pode_gerir": _gerir(request.user)})


@login_required
def criar(request):
    if not _gerir(request.user):
        raise PermissionDenied
    form = CandidatoForm(request.POST or None, initial={"data_proposta": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        c = form.save(commit=False)
        c.etapa_desde = timezone.localdate()
        c.save()
        messages.success(request, "Candidato registrado.")
        return redirect("candidatos:detalhe", pk=c.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Nova proposta",
                                              "cancelar_url": "/candidatos/"})


@login_required
def detalhe(request, pk):
    _ver(request.user)
    c = get_object_or_404(Candidato, pk=pk)
    form = ParecerForm(request.POST or None, initial={"data": timezone.localdate()})
    if request.method == "POST":
        if not _gerir(request.user):
            raise PermissionDenied
        if form.is_valid():
            p = form.save(commit=False)
            p.candidato = c
            p.save()
            messages.success(request, "Parecer registrado.")
            return redirect("candidatos:detalhe", pk=pk)
    return render(request, "candidatos/detalhe.html", {
        "c": c, "form": form, "etapas": Candidato.Etapa.choices, "pode_gerir": _gerir(request.user),
        "pareceres": c.pareceres.select_related("irmao"), "historico": c.history.all()[:15],
        "sessoes_recentes": Sessao.objects.order_by("-data_hora")[:15],
    })


@login_required
@require_POST
def mover(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    c = get_object_or_404(Candidato, pk=pk)
    etapa = request.POST.get("etapa")
    if etapa in Candidato.Etapa.values and etapa != c.etapa:
        c.etapa = etapa
        c.etapa_desde = timezone.localdate()
        c.save()
        messages.success(request, f"Etapa alterada para {c.get_etapa_display()}.")
    return redirect("candidatos:detalhe", pk=pk)


@login_required
@require_POST
def iniciar(request, pk):
    """Inicia o candidato aprovado: cria o irmão (Aprendiz) e registra a cerimônia na sessão escolhida."""
    if not _gerir(request.user):
        raise PermissionDenied
    from apps.sessoes import services
    from apps.sessoes.models import Sessao

    c = get_object_or_404(Candidato, pk=pk)
    sessao = get_object_or_404(Sessao, pk=request.POST.get("sessao"))
    try:
        irmao = services.iniciar_candidato(c, sessao, request.user)
    except services.CerimoniaInvalida as exc:
        messages.error(request, str(exc))
        return redirect("candidatos:detalhe", pk=pk)
    messages.success(request, f"{irmao.nome_completo} foi iniciado. Envie o convite de acesso pelo cadastro do irmão.")
    return redirect("irmaos:detalhe", pk=irmao.pk)


@login_required
def editar(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    c = get_object_or_404(Candidato, pk=pk)
    form = CandidatoForm(request.POST or None, instance=c)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados do candidato atualizados.")
        return redirect("candidatos:detalhe", pk=pk)
    return render(request, "crud/form.html", {"form": form, "titulo": f"Editar — {c.nome}",
                                              "cancelar_url": f"/candidatos/{pk}/"})


@login_required
@require_POST
def excluir(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    c = get_object_or_404(Candidato, pk=pk)
    if c.etapa == Candidato.Etapa.INICIADO:
        messages.error(request, "Candidato já iniciado não pode ser excluído (vira registro do irmão).")
        return redirect("candidatos:detalhe", pk=pk)
    c.delete()
    messages.success(request, "Proposta excluída.")
    return redirect("candidatos:painel")
