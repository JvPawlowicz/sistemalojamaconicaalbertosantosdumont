from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.irmaos.models import Irmao

from .forms import AgapeForm, ItemForm, LancamentoForm, MovimentoForm, VisitanteForm
from .models import Agape, AgapeLancamento, Item, Movimento, Participante, Visitante


def _tes(user):
    if not user.tem_perfil(P.TESOUREIRO):
        raise PermissionDenied


def _irmaos_ativos():
    return Irmao.objects.filter(is_active=True, grau__isnull=False)


@login_required
def lista(request):
    pode = request.user.tem_perfil(P.TESOUREIRO)
    agapes = Agape.objects.select_related("sessao")[:40]
    minhas = dict(Participante.objects.filter(irmao=request.user, agape__in=agapes).values_list("agape_id", "vai"))
    return render(request, "agape/lista.html", {
        "agapes": agapes, "pode": pode, "minhas": minhas, "saldo": AgapeLancamento.saldo() if pode else None,
        "baixos": [i for i in Item.objects.filter(ativo=True) if i.baixo] if pode else [],
    })


@login_required
def criar(request):
    _tes(request.user)
    ini = {"data": timezone.localdate(), "descricao": "Ágape"}
    sid = request.GET.get("sessao")
    if sid and sid.isdigit():
        from apps.sessoes.models import Sessao

        s = Sessao.objects.filter(pk=sid).first()
        if s:
            ini.update(sessao=s, data=s.data_hora.date())
    form = AgapeForm(request.POST or None, initial=ini)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            a = form.save()
            Participante.objects.bulk_create([Participante(agape=a, irmao=i) for i in _irmaos_ativos()])
        messages.success(request, "Ágape criado. Todos os irmãos entram como ‘vai’; desmarque quem não participa.")
        return redirect("agape:detalhe", pk=a.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Novo Ágape", "cancelar_url": reverse("agape:lista")})


@login_required
def editar(request, pk):
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    form = AgapeForm(request.POST or None, instance=a)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("agape:detalhe", pk=pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Editar Ágape", "cancelar_url": reverse("agape:detalhe", args=[pk])})


@login_required
def detalhe(request, pk):
    a = get_object_or_404(Agape.objects.select_related("sessao"), pk=pk)
    pode = request.user.tem_perfil(P.TESOUREIRO)
    novos = _irmaos_ativos().exclude(pk__in=a.participantes.values("irmao"))
    if pode and novos:
        Participante.objects.bulk_create([Participante(agape=a, irmao=i) for i in novos])
    minha = a.participantes.filter(irmao=request.user).first()
    form_v = VisitanteForm(prefix="v")
    return render(request, "agape/detalhe.html", {
        "a": a, "pode": pode, "participantes": a.participantes.select_related("irmao"), "visitantes": a.visitantes.all(),
        "minha": minha, "form_v": form_v, "lancamentos": a.lancamentos.all() if pode else [],
    })


@login_required
@require_POST
def confirmar(request, pk):
    """O próprio irmão informa se vai ou não ao Ágape (enquanto aberto)."""
    a = get_object_or_404(Agape, pk=pk)
    if not a.aberto:
        messages.error(request, "Este Ágape já foi encerrado.")
        return redirect("agape:detalhe", pk=pk)
    p, _ = Participante.objects.get_or_create(agape=a, irmao=request.user)
    if p.pago and p.vai:
        messages.error(request, "Seu rateio já foi pago; fale com o tesoureiro para alterar.")
    else:
        p.vai = request.POST.get("vai") == "1"
        p.save(update_fields=["vai"])
        messages.success(request, "Presença no Ágape confirmada." if p.vai else "Registrado: você não vai ao Ágape.")
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def participante(request, pk, irmao_pk):
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    p = get_object_or_404(Participante, agape=a, irmao_id=irmao_pk)
    acao = request.POST.get("acao")
    if acao == "vai":
        if p.pago and p.vai:
            messages.error(request, "Estorne o pagamento antes de tirar o irmão do Ágape.")
        else:
            p.vai = not p.vai
            p.save(update_fields=["vai"])
    elif acao == "pago" and p.vai:
        with transaction.atomic():
            if p.pago:
                AgapeLancamento.objects.filter(participante=p).delete()
                p.pago, p.pago_em = False, None
            else:
                p.pago, p.pago_em = True, timezone.localdate()
                AgapeLancamento.objects.create(
                    agape=a, tipo="entrada", categoria="rateio", valor=a.valor_por_pessoa, data=p.pago_em,
                    descricao=f"Rateio — {p.irmao.nome_completo}", participante=p, criado_por=request.user)
            p.save(update_fields=["pago", "pago_em"])
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def sincronizar(request, pk):
    """Subpresença baseada na lista de presença da sessão: quem faltou à sessão fica como ‘não vai’."""
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    if not a.sessao_id:
        messages.error(request, "Este Ágape não está ligado a uma sessão.")
        return redirect("agape:detalhe", pk=pk)
    pres = set(a.sessao.presencas.filter(situacao="presente").values_list("irmao_id", flat=True))
    if not pres:
        messages.error(request, "A presença da sessão ainda não foi registrada.")
        return redirect("agape:detalhe", pk=pk)
    n = a.participantes.filter(pago=False).exclude(irmao_id__in=pres).update(vai=False)
    a.participantes.filter(irmao_id__in=pres, vai=False).update(vai=True)
    messages.success(request, f"Sincronizado com a presença da sessão: {n} irmão(s) ausente(s) marcados como ‘não vai’.")
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def visitante_novo(request, pk):
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    f = VisitanteForm(request.POST, prefix="v")
    if f.is_valid():
        v = f.save(commit=False)
        v.agape = a
        v.save()
    else:
        messages.error(request, "Informe o nome do visitante.")
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def visitante_excluir(request, pk, visitante_pk):
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    if a.repasse_id:
        messages.error(request, "O repasse já foi feito; não é possível remover visitantes.")
    else:
        Visitante.objects.filter(agape=a, pk=visitante_pk).delete()
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def repasse(request, pk):
    """A loja arca com os visitantes: sai do caixa da loja e entra no caixa do Ágape."""
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    valor = a.custo_visitantes
    if a.repasse_id or valor <= 0:
        messages.error(request, "Nada a repassar (ou repasse já feito).")
        return redirect("agape:detalhe", pk=pk)
    from apps.tesouraria.models import CategoriaFinanceira, MovimentoCaixa

    with transaction.atomic():
        cat, _ = CategoriaFinanceira.objects.get_or_create(nome="Ágape — visitantes", tipo=CategoriaFinanceira.Tipo.DESPESA)
        MovimentoCaixa.objects.create(tipo=cat.tipo, categoria=cat, valor=valor, data=timezone.localdate(),
                                      descricao=f"Custo dos visitantes — {a}", criado_por=request.user)
        a.repasse = AgapeLancamento.objects.create(
            agape=a, tipo="entrada", categoria="repasse", valor=valor, data=timezone.localdate(),
            descricao=f"Repasse da loja — {a.n_visitantes} visitante(s)", criado_por=request.user)
        a.save(update_fields=["repasse"])
    messages.success(request, "Repasse feito: despesa lançada no caixa da loja e entrada no caixa do Ágape.")
    return redirect("agape:detalhe", pk=pk)


@login_required
@require_POST
def encerrar(request, pk):
    _tes(request.user)
    a = get_object_or_404(Agape, pk=pk)
    a.status = Agape.Status.ABERTO if a.status == Agape.Status.ENCERRADO else Agape.Status.ENCERRADO
    a.save(update_fields=["status"])
    return redirect("agape:detalhe", pk=pk)


@login_required
def caixa(request):
    _tes(request.user)
    form = LancamentoForm(request.POST or None, initial={"data": timezone.localdate(), "tipo": "saida"})
    if request.method == "POST" and form.is_valid():
        l = form.save(commit=False)
        l.criado_por = request.user
        l.save()
        messages.success(request, "Lançamento registrado no caixa do Ágape.")
        return redirect("agape:caixa")
    movs = AgapeLancamento.objects.select_related("agape")[:200]
    ent = sum((m.valor for m in movs if m.tipo == "entrada"), Decimal(0))
    sai = sum((m.valor for m in movs if m.tipo == "saida"), Decimal(0))
    return render(request, "agape/caixa.html", {"movs": movs, "form": form, "saldo": AgapeLancamento.saldo(), "entradas": ent, "saidas": sai})


@login_required
def inventario(request):
    _tes(request.user)
    form = MovimentoForm(request.POST or None, initial={"data": timezone.localdate(), "tipo": "entrada"})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        item, q = d["item"], d["quantidade"]
        with transaction.atomic():
            if d["tipo"] == "entrada":
                qtd = q
            elif d["tipo"] in ("consumo", "perda"):
                qtd = -q
            else:  # ajuste: informa o estoque real
                qtd = q - item.estoque
            Movimento.objects.create(item=item, tipo=d["tipo"], quantidade=qtd, data=d["data"], agape=d.get("agape"),
                                     observacao=d.get("observacao", ""), registrado_por=request.user)
            if d["tipo"] == "entrada" and d.get("custo_total"):
                AgapeLancamento.objects.create(tipo="saida", categoria="bebida", valor=d["custo_total"], data=d["data"],
                                               descricao=f"Compra: {q} {item.unidade} de {item.nome}", criado_por=request.user)
        messages.success(request, "Movimento de estoque registrado.")
        return redirect("agape:inventario")
    return render(request, "agape/inventario.html", {
        "itens": Item.objects.all(), "form": form, "historico": Movimento.objects.select_related("item", "agape")[:30],
    })


@login_required
def item_form(request, pk=None):
    _tes(request.user)
    obj = get_object_or_404(Item, pk=pk) if pk else None
    form = ItemForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("agape:inventario")
    return render(request, "crud/form.html", {"form": form, "titulo": "Item do inventário", "cancelar_url": reverse("agape:inventario")})
