from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P

from .forms import VotacaoForm
from .models import Participacao, Votacao, Voto


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


@login_required
def lista(request):
    gerir = _gerir(request.user)
    todas = list(Votacao.objects.select_related("sessao", "candidato"))
    visiveis = [v for v in todas if gerir or (v.status != Votacao.Status.RASCUNHO and request.user.pode_ver_grau(v.grau_minimo))]
    return render(request, "votacoes/lista.html", {
        "votacoes": visiveis, "pode_gerir": gerir,
        "ja_votei": set(Participacao.objects.filter(irmao=request.user).values_list("votacao_id", flat=True)),
    })


@login_required
def criar(request):
    if not _gerir(request.user):
        raise PermissionDenied
    form = VotacaoForm(request.POST or None, initial={"grau_minimo": P.MESTRE})
    if request.method == "POST" and form.is_valid():
        v = form.save(commit=False)
        v.criada_por = request.user
        v.save()
        messages.success(request, "Votação criada. Revise e abra quando a sessão estiver pronta.")
        return redirect("votacoes:detalhe", pk=v.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Nova votação / escrutínio", "cancelar_url": "/votacoes/"})


@login_required
def detalhe(request, pk):
    v = get_object_or_404(Votacao, pk=pk)
    gerir = _gerir(request.user)
    if v.status == Votacao.Status.RASCUNHO and not gerir:
        raise PermissionDenied
    if not gerir and not request.user.pode_ver_grau(v.grau_minimo):
        raise PermissionDenied
    pode, motivo = v.pode_votar(request.user)
    ctx = {"v": v, "pode_gerir": gerir, "pode_votar": pode, "motivo": motivo,
           "participacoes": v.participacoes.select_related("irmao") if gerir else None,
           "n_participantes": v.participacoes.count(), "n_habilitados": v.eleitores().count(),
           "ja_votei": v.participacoes.filter(irmao=request.user).exists()}
    if v.status == Votacao.Status.ENCERRADA:
        ctx["res"] = v.apuracao()
    return render(request, "votacoes/detalhe.html", ctx)


@login_required
@require_POST
def votar(request, pk):
    opcao = request.POST.get("opcao")
    if opcao not in dict(Voto.OPCOES):
        messages.error(request, "Escolha uma opção.")
        return redirect("votacoes:detalhe", pk=pk)
    with transaction.atomic():
        v = Votacao.objects.select_for_update().get(pk=pk)
        pode, motivo = v.pode_votar(request.user)
        if not pode:
            messages.error(request, motivo)
            return redirect("votacoes:detalhe", pk=pk)
        # participação e voto são gravados juntos, mas sem nenhuma ligação entre si
        Participacao.objects.create(votacao=v, irmao=request.user)
        Voto.objects.create(votacao=v, opcao=opcao)
    messages.success(request, "Seu voto foi registrado em sigilo. Obrigado, Irmão.")
    return redirect("votacoes:detalhe", pk=pk)


@login_required
@require_POST
def abrir(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    v = get_object_or_404(Votacao, pk=pk)
    if v.status == Votacao.Status.RASCUNHO:
        v.status = Votacao.Status.ABERTA
        v.aberta_em = timezone.now()
        v.save()
        messages.success(request, "Votação aberta. Os irmãos habilitados já podem votar.")
    return redirect("votacoes:detalhe", pk=pk)


@login_required
@require_POST
def encerrar(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    v = get_object_or_404(Votacao, pk=pk)
    if v.status == Votacao.Status.ABERTA:
        v.status = Votacao.Status.ENCERRADA
        v.encerrada_em = timezone.now()
        v.save()
        messages.success(request, "Votação encerrada. O resultado já pode ser consultado.")
    return redirect("votacoes:detalhe", pk=pk)


@login_required
@require_POST
def aplicar_resultado(request, pk):
    """Aplica o resultado do escrutínio à etapa do candidato."""
    if not _gerir(request.user):
        raise PermissionDenied
    from apps.candidatos.models import Candidato

    v = get_object_or_404(Votacao, pk=pk)
    if v.status != Votacao.Status.ENCERRADA or v.tipo != Votacao.Tipo.ESCRUTINIO or not v.candidato or v.resultado_aplicado:
        messages.error(request, "Não é possível aplicar o resultado.")
        return redirect("votacoes:detalhe", pk=pk)
    res = v.apuracao()
    c = v.candidato
    c.etapa = Candidato.Etapa.APROVADO if res["aprovada"] else Candidato.Etapa.REPROVADO
    c.etapa_desde = timezone.localdate()
    c.save()
    v.resultado_aplicado = True
    v.save(update_fields=["resultado_aplicado"])
    messages.success(request, f"Candidato {c.nome}: {c.get_etapa_display().lower()}.")
    return redirect("votacoes:detalhe", pk=pk)
