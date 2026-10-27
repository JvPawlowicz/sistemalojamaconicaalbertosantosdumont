from datetime import date
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
from apps.core.comunicacao import enviar_email, link_whatsapp
from apps.core.models import AnoMaconico
from apps.core.pdf import pdf_bytes, resposta_pdf
from apps.irmaos.models import Irmao

from . import services
from .forms import BaixaForm, BoletoForm, CategoriaFinanceiraForm, LancamentoAvulsoForm, MovimentoForm
from .models import CategoriaFinanceira, Lancamento, MovimentoCaixa, Orcamento


def _tesoureiro(user):
    if not user.tem_perfil(P.TESOUREIRO):
        raise PermissionDenied


def _mes(request):
    try:
        ano, mes = request.GET.get("mes", "").split("-")
        return date(int(ano), int(mes), 1)
    except (ValueError, TypeError):
        hoje = timezone.localdate()
        return hoje.replace(day=1)


@login_required
def painel(request):
    _tesoureiro(request.user)
    services.atualizar_vencidos()
    hoje = timezone.localdate()
    ano = AnoMaconico.atual()
    mov = MovimentoCaixa.objects.filter(data__range=(ano.inicio, ano.fim))
    receitas = mov.filter(tipo="receita").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    despesas = mov.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    return render(request, "tesouraria/painel.html", {
        "saldo": services.saldo_caixa(), "receitas": receitas, "despesas": despesas, "ano": ano,
        "vencidas": Lancamento.objects.filter(status="vencido").count(),
        "pendentes": Lancamento.objects.filter(status="pendente").count(),
        "recentes": MovimentoCaixa.objects.select_related("categoria")[:8], "hoje": hoje,
    })


@login_required
def mensalidades(request):
    _tesoureiro(request.user)
    services.atualizar_vencidos()
    mes = _mes(request)
    status = request.GET.get("status", "")
    qs = Lancamento.objects.filter(competencia=mes).select_related("irmao")
    if status in Lancamento.Status.values:
        qs = qs.filter(status=status)
    linhas = []
    for l in qs:
        msg = services.mensagem_cobranca(l)
        linhas.append((l, link_whatsapp(l.irmao.whatsapp or l.irmao.telefone, msg) if l.em_aberto else ""))
    total = qs.aggregate(s=Sum("valor"))["s"] or 0
    return render(request, "tesouraria/mensalidades.html", {
        "linhas": linhas, "mes": mes, "status": status, "status_choices": Lancamento.Status.choices, "total": total,
        "baixa_form": BaixaForm(initial={"data_pagamento": timezone.localdate()}),
    })


@login_required
@require_POST
def gerar(request):
    _tesoureiro(request.user)
    mes = _mes(request) if "mes" in request.GET else None
    try:
        a, m = request.POST.get("mes", "").split("-")
        mes = date(int(a), int(m), 1)
    except (ValueError, TypeError):
        mes = mes or timezone.localdate().replace(day=1)
    n = services.gerar_mensalidades(mes)
    messages.success(request, f"{n} mensalidade(s) gerada(s) para {mes:%m/%Y}.")
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={mes:%Y-%m}")


@login_required
@require_POST
def baixa(request, pk):
    _tesoureiro(request.user)
    l = get_object_or_404(Lancamento, pk=pk)
    form = BaixaForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        services.dar_baixa(l, request.user, d["data_pagamento"], d["valor_pago"], d["forma"], d["observacao"])
        messages.success(request, f"Baixa registrada: {l.irmao.nome_completo}.")
    else:
        messages.error(request, "Dados da baixa inválidos.")
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")


@login_required
@require_POST
def estornar(request, pk):
    _tesoureiro(request.user)
    l = get_object_or_404(Lancamento, pk=pk)
    services.estornar_baixa(l)
    messages.warning(request, "Baixa estornada e receita removida do caixa.")
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")


@login_required
@require_POST
def dispensar(request, pk):
    _tesoureiro(request.user)
    l = get_object_or_404(Lancamento, pk=pk)
    l.status = Lancamento.Status.DISPENSADO
    l.observacao = request.POST.get("observacao", "")[:200]
    l.save()
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")


@login_required
@require_POST
def cobrar_email(request, pk):
    _tesoureiro(request.user)
    l = get_object_or_404(Lancamento, pk=pk)
    if not l.irmao.email:
        messages.error(request, "O irmão não tem e-mail.")
    elif enviar_email(l.irmao.email, f"Cobrança — {l.descricao} {l.competencia:%m/%Y}",
                      services.mensagem_cobranca(l), contexto="cobranca"):
        l.ultima_cobranca_em = timezone.now()
        l.save()
        messages.success(request, "Cobrança enviada por e-mail.")
    else:
        messages.error(request, "Falha ao enviar o e-mail (veja o registro de e-mails).")
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")


@login_required
@require_POST
def cobrar_todos(request):
    _tesoureiro(request.user)
    mes = _mes(request) if request.GET.get("mes") else None
    try:
        a, m = request.POST.get("mes", "").split("-")
        mes = date(int(a), int(m), 1)
    except (ValueError, TypeError):
        mes = timezone.localdate().replace(day=1)
    ok = 0
    for l in services.inadimplencia_do_mes(mes).select_related("irmao").exclude(irmao__email=""):
        if enviar_email(l.irmao.email, f"Cobrança — {l.descricao} {l.competencia:%m/%Y}",
                        services.mensagem_cobranca(l), contexto="cobranca"):
            l.ultima_cobranca_em = timezone.now()
            l.save()
            ok += 1
    messages.success(request, f"{ok} cobrança(s) enviada(s) por e-mail.")
    return redirect(f"{reverse('tesouraria:mensalidades')}?mes={mes:%Y-%m}")


@login_required
def boleto(request, pk):
    l = get_object_or_404(Lancamento, pk=pk)
    if l.irmao_id != request.user.pk:
        _tesoureiro(request.user)
    if request.method == "POST":
        _tesoureiro(request.user)
        form = BoletoForm(request.POST, request.FILES, instance=l)
        if form.is_valid():
            form.save()
            messages.success(request, "Boleto anexado.")
        else:
            messages.error(request, "; ".join(sum(form.errors.values(), [])))
        return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")
    return servir_arquivo(l.boleto)


@login_required
def comprovante(request, pk):
    mov = get_object_or_404(MovimentoCaixa, pk=pk)
    _tesoureiro(request.user)
    return servir_arquivo(mov.comprovante)


@login_required
def caixa(request):
    _tesoureiro(request.user)
    ano = AnoMaconico.atual()
    if request.GET.get("ano"):
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    movs = MovimentoCaixa.objects.filter(data__range=(ano.inicio, ano.fim)).select_related("categoria")
    form = MovimentoForm(request.POST or None, request.FILES or None, initial={"data": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        m = form.save(commit=False)
        m.criado_por = request.user
        m.save()
        messages.success(request, "Movimento lançado no caixa.")
        return redirect("tesouraria:caixa")
    return render(request, "tesouraria/caixa.html", {
        "movs": movs, "form": form, "ano": ano, "anos": AnoMaconico.objects.all(), "saldo": services.saldo_caixa(),
    })


@login_required
def categorias(request):
    _tesoureiro(request.user)
    form = CategoriaFinanceiraForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Categoria criada.")
        return redirect("tesouraria:categorias")
    return render(request, "tesouraria/categorias.html", {"categorias": CategoriaFinanceira.objects.all(), "form": form})


@login_required
def orcamento(request):
    _tesoureiro(request.user)
    ano = AnoMaconico.atual()
    if request.GET.get("ano"):
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    if request.method == "POST":
        for cat in CategoriaFinanceira.objects.filter(ativa=True):
            bruto = request.POST.get(f"cat_{cat.pk}", "").replace(".", "").replace(",", ".")
            if bruto == "":
                continue
            try:
                valor = Decimal(bruto)
            except Exception:  # noqa: BLE001
                continue
            if valor >= 0:
                Orcamento.objects.update_or_create(ano=ano, categoria=cat, defaults={"valor_previsto": valor})
        messages.success(request, "Orçamento salvo.")
        return redirect(f"{reverse('tesouraria:orcamento')}?ano={ano.pk}")
    return render(request, "tesouraria/orcamento.html", {
        "linhas": services.orcamento_vs_realizado(ano), "ano": ano, "anos": AnoMaconico.objects.all(),
    })


@login_required
def minhas(request):
    services.atualizar_vencidos()
    return render(request, "tesouraria/minhas.html", {
        "lancamentos": Lancamento.objects.filter(irmao=request.user), "irmao": request.user,
    })


@login_required
def extrato_pdf(request, pk):
    irmao = get_object_or_404(Irmao, pk=pk)
    if irmao.pk != request.user.pk:
        _tesoureiro(request.user)
    lancs = Lancamento.objects.filter(irmao=irmao).order_by("competencia")
    dados = pdf_bytes("tesouraria/extrato_pdf.html", {
        "irmao": irmao, "lancamentos": lancs, "emitido": timezone.now(),
        "pago": lancs.filter(status="pago").aggregate(s=Sum("valor_pago"))["s"] or 0,
        "aberto": lancs.filter(status__in=["pendente", "vencido"]).aggregate(s=Sum("valor"))["s"] or 0,
    }, request)
    return resposta_pdf(f"extrato-{irmao.pk}.pdf", dados)


@login_required
def lancamento_avulso(request):
    """Cobrança avulsa (joia, contribuição extra, evento etc.)."""
    _tesoureiro(request.user)
    form = LancamentoAvulsoForm(request.POST or None, initial={"competencia": timezone.localdate().replace(day=1)})
    form.fields["irmao"].queryset = Irmao.objects.filter(is_active=True, grau__isnull=False)
    if request.method == "POST" and form.is_valid():
        l = form.save(commit=False)
        l.competencia = l.competencia.replace(day=1)
        l.status = Lancamento.Status.PENDENTE
        l.save()
        messages.success(request, "Cobrança lançada.")
        return redirect(f"{reverse('tesouraria:mensalidades')}?mes={l.competencia:%Y-%m}")
    return render(request, "crud/form.html", {"form": form, "titulo": "Cobrança avulsa",
                                              "cancelar_url": reverse("tesouraria:mensalidades")})
