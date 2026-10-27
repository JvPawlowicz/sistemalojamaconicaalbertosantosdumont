from datetime import date

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render

from apps.core.models import AnoMaconico

from . import exportar
from .relatorios import RELATORIOS


@login_required
def indice(request):
    grupos = {}
    for slug, (titulo, grupo, perfil, _, _) in RELATORIOS.items():
        if request.user.tem_perfil(perfil):
            grupos.setdefault(grupo, []).append((slug, titulo))
    return render(request, "relatorios/indice.html", {"grupos": grupos, "ano_atual": AnoMaconico.atual().nome})


@login_required
def ver(request, slug):
    if slug not in RELATORIOS:
        raise Http404
    titulo, grupo, perfil, funcao, usa_ano = RELATORIOS[slug]
    if not request.user.tem_perfil(perfil):
        raise PermissionDenied
    subtitulo, cabecalho, linhas = funcao(request)
    formato = request.GET.get("formato", "")
    nome = slug
    if formato == "csv":
        return exportar.para_csv(nome, cabecalho, linhas)
    if formato == "xlsx":
        return exportar.para_xlsx(nome, cabecalho, linhas)
    if formato == "pdf":
        return exportar.para_pdf(request, titulo, subtitulo, cabecalho, linhas)
    return render(request, "relatorios/ver.html", {
        "titulo": titulo, "subtitulo": subtitulo, "cabecalho": cabecalho, "slug": slug, "usa_ano": usa_ano,
        "linhas": [[exportar.formatar(c) for c in l] for l in linhas], "anos": AnoMaconico.objects.all(),
        "ano_sel": request.GET.get("ano", ""), "querystring": request.GET.urlencode(),
    })


@login_required
def pacote_fiscal(request):
    """Prestação de contas do ano maçônico para o Conselho Fiscal / comissão de auditoria (PDF único)."""
    from decimal import Decimal

    from django.db.models import Sum

    from apps.core import perfis as P
    from apps.core.models import Loja
    from apps.core.pdf import pdf_bytes, resposta_pdf
    from apps.tesouraria import services as tes
    from apps.tesouraria.models import Lancamento, MovimentoCaixa

    if not request.user.tem_algum_perfil(P.TESOUREIRO, P.ADMINISTRADOR):
        raise PermissionDenied
    ano = AnoMaconico.atual()
    if request.GET.get("ano", "").isdigit():
        ano = AnoMaconico.objects.filter(pk=int(request.GET["ano"])).first() or ano
    tes.atualizar_vencidos()
    movs = MovimentoCaixa.objects.filter(data__range=(ano.inicio, ano.fim)).select_related("categoria").order_by("data", "id")
    antes = MovimentoCaixa.objects.filter(data__lt=ano.inicio)
    saldo_inicial = (antes.filter(tipo="receita").aggregate(s=Sum("valor"))["s"] or Decimal(0)) - \
        (antes.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal(0))
    mensal, saldo = [], saldo_inicial
    for mes in ano.meses:
        fim = date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)
        qs = movs.filter(data__gte=mes, data__lt=fim)
        rec = qs.filter(tipo="receita").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        des = qs.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        saldo += rec - des
        mensal.append({"mes": mes, "receitas": rec, "despesas": des, "saldo": saldo})
    lanc = Lancamento.objects.filter(competencia__range=(ano.inicio, ano.fim))
    abertas = lanc.filter(status__in=["pendente", "vencido"]).select_related("irmao")
    dados = pdf_bytes("relatorios/pacote_fiscal_pdf.html", {
        "ano": ano, "saldo_inicial": saldo_inicial, "saldo_final": saldo, "mensal": mensal, "movs": movs,
        "orcamento": tes.orcamento_vs_realizado(ano),
        "mensalidades": {s: lanc.filter(status=s).count() for s in ("pago", "pendente", "vencido", "isento", "dispensado")},
        "abertas": abertas, "total_aberto": abertas.aggregate(s=Sum("valor"))["s"] or Decimal(0),
        "sem_comprovante": movs.filter(comprovante="", lancamento__isnull=True).count(), "emitido": timezone.now(),
        "usuario": request.user, "loja": Loja.atual(),
    }, request)
    return resposta_pdf(f"prestacao-de-contas-{ano.nome.replace('/', '-')}.pdf", dados, inline=False)
