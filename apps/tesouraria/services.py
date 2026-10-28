from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.models import AnoMaconico, Loja
from apps.irmaos.models import Irmao

from .models import CategoriaFinanceira, Lancamento, MovimentoCaixa, Orcamento


def saldo_caixa():
    entradas = MovimentoCaixa.objects.filter(tipo="receita").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    saidas = MovimentoCaixa.objects.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal(0)
    return entradas - saidas


def categoria_mensalidades():
    cat, _ = CategoriaFinanceira.objects.get_or_create(nome="Mensalidades", tipo=CategoriaFinanceira.Tipo.RECEITA)
    return cat


def atualizar_vencidos(hoje=None):
    hoje = hoje or timezone.localdate()
    return Lancamento.objects.filter(status=Lancamento.Status.PENDENTE, vencimento__lt=hoje).update(
        status=Lancamento.Status.VENCIDO
    )


@transaction.atomic
def gerar_mensalidades(competencia: date):
    """Gera a mensalidade do mês para cada irmão ativo, conforme a categoria. Idempotente."""
    competencia = competencia.replace(day=1)
    loja = Loja.atual()
    dia = min(loja.mensalidade_dia_vencimento, 28)
    vencimento = competencia.replace(day=dia)
    criados = 0
    for irmao in Irmao.objects.filter(is_active=True, grau__isnull=False, situacao__in=["ativo", "remido"]):
        cat = irmao.categoria
        if cat is None:
            continue
        isento = cat.isento or irmao.situacao == "remido"
        _, criado = Lancamento.objects.get_or_create(
            irmao=irmao, competencia=competencia, descricao="Mensalidade",
            defaults={
                "valor": Decimal(0) if isento else cat.valor_mensal, "vencimento": vencimento,
                "status": Lancamento.Status.ISENTO if isento else Lancamento.Status.PENDENTE,
            },
        )
        criados += criado
    atualizar_vencidos()
    return criados


@transaction.atomic
def dar_baixa(lancamento, usuario, data_pagamento, valor_pago, forma, observacao=""):
    """Registra o pagamento e lança a receita no caixa."""
    lancamento.status = Lancamento.Status.PAGO
    lancamento.pago_em = data_pagamento
    lancamento.valor_pago = valor_pago
    lancamento.forma = forma
    lancamento.baixa_por = usuario
    if observacao:
        lancamento.observacao = observacao
    lancamento.save()
    MovimentoCaixa.objects.update_or_create(
        lancamento=lancamento,
        defaults={
            "tipo": CategoriaFinanceira.Tipo.RECEITA, "categoria": categoria_mensalidades(), "valor": valor_pago,
            "data": data_pagamento, "criado_por": usuario,
            "descricao": f"{lancamento.descricao} {lancamento.competencia:%m/%Y} — {lancamento.irmao.nome_completo}",
        },
    )


@transaction.atomic
def estornar_baixa(lancamento):
    MovimentoCaixa.objects.filter(lancamento=lancamento).delete()
    lancamento.status = Lancamento.Status.PENDENTE
    lancamento.pago_em = None
    lancamento.valor_pago = None
    lancamento.save()
    atualizar_vencidos()


def orcamento_vs_realizado(ano: AnoMaconico):
    """Linhas (categoria, previsto, realizado, diferença) do ano maçônico."""
    realizado = {
        r["categoria"]: r["total"]
        for r in MovimentoCaixa.objects.filter(data__range=(ano.inicio, ano.fim))
        .values("categoria").annotate(total=Sum("valor"))
    }
    previstos = {o.categoria_id: o.valor_previsto for o in Orcamento.objects.filter(ano=ano)}
    linhas = []
    for cat in CategoriaFinanceira.objects.filter(ativa=True):
        prev = previstos.get(cat.pk, Decimal(0))
        real = realizado.get(cat.pk, Decimal(0))
        linhas.append({"categoria": cat, "previsto": prev, "realizado": real, "diferenca": real - prev})
    return linhas


def mensagem_cobranca(lancamento):
    loja = Loja.atual()
    v = valor_atualizado(lancamento)
    fmt = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
    texto = (f"Prezado Irmão {lancamento.irmao.nome_completo}, informamos que a {lancamento.descricao.lower()} "
             f"de {lancamento.competencia:%m/%Y} (R$ {fmt(lancamento.valor)}), com vencimento em "
             f"{lancamento.vencimento:%d/%m/%Y}, encontra-se em aberto.")
    if v["total"] != v["base"]:
        texto += f" Com multa e juros ({v['dias']} dia(s) de atraso), o valor atualizado é R$ {fmt(v['total'])}."
    if loja.chave_pix:
        from .pix import br_code, txid_da_mensalidade

        texto += (f" PIX copia e cola: {br_code(loja.chave_pix, loja.nome, loja.oriente, v['total'], txid_da_mensalidade(lancamento.pk))}")
    return texto + f" Fraterno abraço, Tesouraria — {loja.nome}."


def inadimplencia_do_mes(competencia: date):
    return Lancamento.objects.filter(competencia=competencia.replace(day=1), status__in=["pendente", "vencido"])


def valor_atualizado(lancamento, hoje=None):
    """Valor com multa e juros do regimento (pro rata por dia). Devolve dict com os componentes."""
    from decimal import ROUND_HALF_UP

    hoje = hoje or timezone.localdate()
    base = lancamento.valor
    zero = {"base": base, "multa": Decimal(0), "juros": Decimal(0), "total": base, "dias": 0}
    if lancamento.status not in (Lancamento.Status.PENDENTE, Lancamento.Status.VENCIDO) or base <= 0:
        return zero
    loja = Loja.atual()
    dias = (hoje - lancamento.vencimento).days - loja.dias_carencia_atraso
    if dias <= 0 or not (loja.multa_atraso_percentual or loja.juros_mensal_percentual):
        return zero
    cent = Decimal("0.01")
    multa = (base * loja.multa_atraso_percentual / 100).quantize(cent, ROUND_HALF_UP)
    juros = (base * loja.juros_mensal_percentual / 100 * Decimal(dias) / 30).quantize(cent, ROUND_HALF_UP)
    return {"base": base, "multa": multa, "juros": juros, "total": base + multa + juros, "dias": dias}
