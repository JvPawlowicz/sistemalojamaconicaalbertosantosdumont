from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.core.arquivos import servir_arquivo

from .forms import AcompanhamentoForm, CasoForm, TroncoForm
from .models import CasoHospitalaria, MovimentoTronco


def _hosp(user):
    if not user.tem_perfil(P.HOSPITALEIRO):
        raise PermissionDenied


def _tronco(user):
    if not user.tem_algum_perfil(P.HOSPITALEIRO, P.TESOUREIRO):
        raise PermissionDenied


@login_required
def painel(request):
    _hosp(request.user)
    abertos = list(CasoHospitalaria.objects.filter(status="acompanhando").select_related("irmao", "responsavel"))
    limite = timezone.localdate() - timedelta(days=15)
    return render(request, "hospitalaria/painel.html", {
        "casos": abertos, "sem_contato": [c for c in abertos if c.ultimo_contato < limite],
        "encerrados": CasoHospitalaria.objects.filter(status="encerrado").select_related("irmao")[:10],
        "saldo": MovimentoTronco.saldo(),
    })


@login_required
def caso_novo(request):
    _hosp(request.user)
    form = CasoForm(request.POST or None, initial={"data_inicio": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        c = form.save()
        messages.success(request, "Caso registrado (sigiloso).")
        return redirect("hospitalaria:caso", pk=c.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Novo caso de hospitalaria",
                                              "cancelar_url": reverse("hospitalaria:painel")})


@login_required
def caso(request, pk):
    _hosp(request.user)
    c = get_object_or_404(CasoHospitalaria, pk=pk)
    form = AcompanhamentoForm(request.POST or None, initial={"data": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        a.caso = c
        a.registrado_por = request.user
        a.save()
        messages.success(request, "Acompanhamento registrado.")
        return redirect("hospitalaria:caso", pk=pk)
    return render(request, "hospitalaria/caso.html", {
        "c": c, "form": form, "acompanhamentos": c.acompanhamentos.select_related("registrado_por"),
        "movimentos": c.movimentos.all(),
    })


@login_required
@require_POST
def caso_status(request, pk):
    _hosp(request.user)
    c = get_object_or_404(CasoHospitalaria, pk=pk)
    if c.status == "acompanhando":
        c.status, c.encerrado_em = "encerrado", timezone.localdate()
    else:
        c.status, c.encerrado_em = "acompanhando", None
    c.save()
    return redirect("hospitalaria:caso", pk=pk)


@login_required
def tronco(request):
    _tronco(request.user)
    pode_lancar = request.user.tem_perfil(P.HOSPITALEIRO)
    form = TroncoForm(request.POST or None, request.FILES or None, initial={"data": timezone.localdate()}) if pode_lancar else None
    if request.method == "POST":
        if not pode_lancar:
            raise PermissionDenied
        if form.is_valid():
            m = form.save(commit=False)
            m.registrado_por = request.user
            m.save()
            messages.success(request, "Movimento do Tronco registrado.")
            return redirect("hospitalaria:tronco")
    from apps.core.models import AnoMaconico

    ano = AnoMaconico.atual()
    movs = MovimentoTronco.objects.filter(data__range=(ano.inicio, ano.fim)).select_related("sessao", "caso")
    arrec = movs.filter(tipo="arrecadacao").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    dest = movs.filter(tipo="destinacao").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    return render(request, "hospitalaria/tronco.html", {
        "movs": movs, "form": form, "saldo": MovimentoTronco.saldo(), "arrecadado": arrec, "destinado": dest, "ano": ano,
    })


@login_required
@require_POST
def tronco_rapido(request, sessao_pk):
    """Arrecadação da sessão, direto da área de trabalho da sessão."""
    _hosp(request.user)
    from apps.sessoes.models import Sessao

    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    try:
        valor = Decimal(request.POST.get("valor", "").replace(".", "").replace(",", "."))
    except Exception:  # noqa: BLE001
        valor = Decimal(0)
    if valor <= 0:
        messages.error(request, "Informe o valor arrecadado.")
    else:
        MovimentoTronco.objects.create(tipo="arrecadacao", valor=valor, data=sessao.data_hora.date(), sessao=sessao,
                                       descricao=f"Arrecadação da sessão de {sessao.data_hora:%d/%m/%Y}", registrado_por=request.user)
        messages.success(request, "Arrecadação do Tronco registrada.")
    return redirect(reverse("sessoes:detalhe", args=[sessao.pk]))


@login_required
def comprovante(request, pk):
    _tronco(request.user)
    return servir_arquivo(get_object_or_404(MovimentoTronco, pk=pk).comprovante)
