"""Definição dos relatórios. Cada função devolve (subtítulo, cabeçalho, linhas)."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.atas.models import Ata
from apps.candidatos.models import Candidato
from apps.cargos.models import Gestao
from apps.core import perfis as P
from apps.core.models import AceiteTermo, AnoMaconico, TermoAceite
from apps.irmaos.models import Irmao
from apps.patrimonio.models import ItemPatrimonio
from apps.sessoes import services as sessoes_services
from apps.tesouraria import services as tes
from apps.tesouraria.models import Lancamento, MovimentoCaixa
from apps.visitas.models import VisitaRealizada, VisitaRecebida


def _ano(request):
    pk = request.GET.get("ano")
    if pk and pk.isdigit():
        a = AnoMaconico.objects.filter(pk=pk).first()
        if a:
            return a
    return AnoMaconico.atual()


def frequencia(request):
    ano = _ano(request)
    linhas = []
    for i in Irmao.objects.filter(is_active=True, grau__isnull=False):
        f = sessoes_services.frequencia(i, ano)
        linhas.append([i.nome_completo, i.grau_nome, f["presentes"], f["justificadas"], f["ausentes"], f["total"],
                       f"{f['percentual']}%".replace(".", ",") if f["percentual"] is not None else "—"])
    return (f"Ano maçônico {ano}", ["Irmão", "Grau", "Presenças", "Justificadas", "Ausências", "Sessões", "Frequência"], linhas)


def quadro_obreiros(request):
    linhas = [[i.nome_completo, i.grau_nome, i.get_situacao_display(), i.categoria or "—", i.data_iniciacao,
               i.data_promocao, i.data_elevacao, i.profissao, i.telefone]
              for i in Irmao.objects.filter(grau__isnull=False).order_by("-grau", "nome_completo")]
    return ("Todos os irmãos do quadro", ["Irmão", "Grau", "Situação", "Categoria", "Iniciação", "Promoção",
                                          "Elevação", "Profissão", "Telefone"], linhas)


def oficiais(request):
    ano = _ano(request)
    linhas = [[g.cargo.nome, g.irmao.nome_completo] for g in Gestao.objects.filter(ano=ano).select_related("cargo", "irmao")]
    return (f"Gestão {ano}", ["Cargo", "Irmão"], linhas)


def atas(request):
    ano = _ano(request)
    linhas = []
    for a in Ata.objects.filter(sessao__ano=ano).select_related("sessao"):
        faltam = ", ".join(s.irmao.nome_completo for s in a.faltam_assinar()) if a.status == Ata.Status.APROVADA else ""
        linhas.append([a.numero or "—", a.sessao.data_hora.date(), a.sessao.get_grau_display(), a.get_status_display(),
                       a.versao, faltam])
    return (f"Ano maçônico {ano}", ["Nº", "Data", "Grau", "Situação", "Versão", "Falta assinar"], linhas)


def aniversariantes(request):
    hoje = timezone.localdate()
    mes = int(request.GET["mes"]) if request.GET.get("mes", "").isdigit() and 1 <= int(request.GET["mes"]) <= 12 else hoje.month
    linhas = [[i.nome_completo, i.data_nascimento, i.telefone]
              for i in Irmao.objects.filter(is_active=True, grau__isnull=False, data_nascimento__month=mes)
              .order_by("data_nascimento__day")]
    return (f"Mês {mes:02d}", ["Irmão", "Nascimento", "Telefone"], linhas)


def candidatos(request):
    hoje = timezone.localdate()
    linhas = [[c.nome, c.proposto_por.nome_completo, c.data_proposta, c.get_etapa_display(),
               (hoje - (c.etapa_desde or c.data_proposta)).days] for c in Candidato.objects.select_related("proposto_por")]
    return ("Propostas", ["Candidato", "Proposto por", "Data da proposta", "Etapa", "Dias na etapa"], linhas)


def cerimonias(request):
    ano = _ano(request)
    linhas = []
    for campo, nome in (("data_iniciacao", "Iniciação"), ("data_promocao", "Promoção"), ("data_elevacao", "Elevação")):
        for i in Irmao.objects.filter(**{f"{campo}__range": (ano.inicio, ano.fim)}):
            linhas.append([nome, getattr(i, campo), i.nome_completo])
    linhas.sort(key=lambda l: l[1])
    return (f"Ano maçônico {ano}", ["Cerimônia", "Data", "Irmão"], linhas)


def visitas(request):
    ano = _ano(request)
    linhas = [["Realizada", v.data, v.irmao.nome_completo, f"{v.loja_nome} {v.loja_numero}".strip(), v.oriente]
              for v in VisitaRealizada.objects.filter(data__range=(ano.inicio, ano.fim)).select_related("irmao")]
    linhas += [["Recebida", v.sessao.data_hora.date(), v.visitante.nome,
                f"{v.visitante.loja_nome} {v.visitante.loja_numero}".strip(), v.visitante.oriente]
               for v in VisitaRecebida.objects.filter(sessao__ano=ano).select_related("sessao", "visitante")]
    linhas.sort(key=lambda l: l[1])
    return (f"Ano maçônico {ano}", ["Tipo", "Data", "Irmão / visitante", "Loja", "Oriente"], linhas)


def mensalidades(request):
    tes.atualizar_vencidos()
    ano = _ano(request)
    dados = defaultdict(lambda: [0, Decimal(0)])
    for l in Lancamento.objects.filter(competencia__range=(ano.inicio, ano.fim), status__in=["pendente", "vencido"]) \
            .select_related("irmao"):
        d = dados[l.irmao.nome_completo]
        d[0] += 1
        d[1] += l.valor
    linhas = sorted(([n, q, t] for n, (q, t) in dados.items()), key=lambda l: -l[2])
    return (f"Inadimplência — ano maçônico {ano}", ["Irmão", "Parcelas em aberto", "Total em aberto (R$)"], linhas)


def caixa(request):
    ano = _ano(request)
    linhas = []
    saldo = Decimal(0)
    for mes in ano.meses:
        fim = date(mes.year + (mes.month // 12), mes.month % 12 + 1, 1)
        qs = MovimentoCaixa.objects.filter(data__gte=mes, data__lt=fim)
        rec = qs.filter(tipo="receita").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        des = qs.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        saldo += rec - des
        linhas.append([mes.strftime("%m/%Y"), rec, des, rec - des, saldo])
    return (f"Fluxo de caixa — ano maçônico {ano}", ["Mês", "Receitas", "Despesas", "Resultado", "Saldo acumulado"], linhas)


def orcamento(request):
    ano = _ano(request)
    linhas = [[l["categoria"].nome, l["categoria"].get_tipo_display(), l["previsto"], l["realizado"], l["diferenca"]]
              for l in tes.orcamento_vs_realizado(ano)]
    return (f"Ano maçônico {ano}", ["Categoria", "Tipo", "Previsto", "Realizado", "Diferença"], linhas)


def patrimonio(request):
    linhas = [[i.nome, i.categoria, i.quantidade, i.get_estado_display(), i.local, i.responsavel or "—", i.valor]
              for i in ItemPatrimonio.objects.select_related("responsavel")]
    return ("Inventário", ["Item", "Categoria", "Qtd.", "Estado", "Local", "Responsável", "Valor (R$)"], linhas)


def auditoria(request):
    linhas = []
    for modelo, rotulo in ((Ata, "Ata"), (Lancamento, "Mensalidade"), (MovimentoCaixa, "Caixa"), (Irmao, "Irmão"),
                           (Candidato, "Candidato")):
        for h in modelo.history.select_related("history_user").order_by("-history_date")[:100]:
            linhas.append([h.history_date, rotulo, str(h.instance)[:80],
                           {"+": "Criado", "~": "Alterado", "-": "Excluído"}.get(h.history_type, ""),
                           h.history_user.nome_completo if h.history_user else "—"])
    linhas.sort(key=lambda l: l[0], reverse=True)
    return ("Últimas alterações", ["Quando", "Tipo", "Registro", "Ação", "Usuário"], linhas[:300])


def aceites(request):
    termo = TermoAceite.vigente()
    feitos = {a.irmao_id: a for a in AceiteTermo.objects.filter(termo=termo)} if termo else {}
    linhas = [[i.nome_completo, "Sim" if i.pk in feitos else "Não", feitos[i.pk].aceito_em if i.pk in feitos else None,
               feitos[i.pk].ip if i.pk in feitos else ""] for i in Irmao.objects.filter(is_active=True, grau__isnull=False)]
    return (f"Termo versão {termo.versao if termo else '—'}", ["Irmão", "Aceitou", "Quando", "IP"], linhas)


# slug: (título, grupo, perfil exigido, função, usa ano?)
RELATORIOS = {
    "frequencia": ("Frequência por irmão", "Secretaria", P.SECRETARIO, frequencia, True),
    "quadro-obreiros": ("Quadro de obreiros", "Secretaria", P.SECRETARIO, quadro_obreiros, False),
    "oficiais": ("Quadro de oficiais", "Secretaria", P.SECRETARIO, oficiais, True),
    "atas": ("Situação das atas", "Secretaria", P.SECRETARIO, atas, True),
    "aniversariantes": ("Aniversariantes", "Secretaria", P.SECRETARIO, aniversariantes, False),
    "candidatos": ("Candidatos e propostas", "Secretaria", P.SECRETARIO, candidatos, False),
    "cerimonias": ("Cerimônias do ano", "Secretaria", P.SECRETARIO, cerimonias, True),
    "visitas": ("Visitas realizadas e recebidas", "Secretaria", P.SECRETARIO, visitas, True),
    "mensalidades": ("Inadimplência", "Tesouraria", P.TESOUREIRO, mensalidades, True),
    "caixa": ("Fluxo de caixa", "Tesouraria", P.TESOUREIRO, caixa, True),
    "orcamento": ("Orçamento previsto × realizado", "Tesouraria", P.TESOUREIRO, orcamento, True),
    "patrimonio": ("Inventário do patrimônio", "Patrimônio", P.SECRETARIO, patrimonio, False),
    "auditoria": ("Trilha de auditoria", "Administração", P.ADMINISTRADOR, auditoria, False),
    "aceites": ("Aceites do termo de assinatura", "Administração", P.ADMINISTRADOR, aceites, False),
}
