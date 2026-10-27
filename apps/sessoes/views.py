from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.cargos.models import Cargo
from apps.core import perfis as P
from apps.core.comunicacao import enviar_email
from apps.core.models import AnoMaconico, Loja
from apps.core.pdf import pdf_bytes, resposta_pdf
from apps.irmaos.models import Irmao

from . import services
from .forms import SessaoForm
from .models import Escala, Presenca, Sessao


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


def _sessao_visivel(request, pk):
    sessao = get_object_or_404(Sessao, pk=pk)
    if not request.user.pode_ver_grau(sessao.grau):
        raise PermissionDenied
    return sessao


def _expedientes_da_sessao(sessao):
    """Correspondências lidas nesta sessão ou, se ainda não realizada, as pendentes de leitura."""
    from apps.expediente.models import Correspondencia

    if sessao.status == Sessao.Status.REALIZADA:
        return sessao.expedientes.all()
    return Correspondencia.objects.filter(leva_a_sessao=True, lida_em_sessao__isnull=True,
                                          data__lte=sessao.data_hora.date())


@login_required
def lista(request):
    anos = AnoMaconico.objects.all()
    ano = AnoMaconico.atual()
    if request.GET.get("ano"):
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    sessoes = [s for s in Sessao.objects.filter(ano=ano).order_by("data_hora") if request.user.pode_ver_grau(s.grau)]
    return render(request, "sessoes/lista.html", {
        "sessoes": sessoes, "ano": ano, "anos": anos, "pode_gerir": _gerir(request.user), "agora": timezone.now(),
    })


ABAS = [("resumo", "Resumo"), ("escala", "Escala"), ("presenca", "Presença"), ("visitantes", "Visitantes"),
        ("cerimonias", "Cerimônias"), ("ata", "Ata")]
ABAS_DE_GESTAO = {"escala", "presenca", "visitantes", "cerimonias"}


def url_aba(sessao, aba="resumo"):
    return reverse("sessoes:detalhe", args=[sessao.pk]) + (f"?aba={aba}" if aba != "resumo" else "")


def render_detalhe(request, sessao, aba, **extra):
    """Área de trabalho da sessão: tudo em uma página, com abas (menos cliques e navegação)."""
    from apps.atas.models import Ata
    from apps.cargos.models import Cargo
    from apps.candidatos.models import Candidato
    from apps.irmaos.models import Irmao as IrmaoModel
    from apps.visitas.forms import VisitanteForm
    from apps.visitas.models import CertificadoVisita, Visitante

    gerir = _gerir(request.user)
    abas_ok = [(k, n) for k, n in ABAS if gerir or k not in ABAS_DE_GESTAO]
    if aba not in dict(abas_ok):
        aba = "resumo"
    ata = Ata.objects.filter(sessao=sessao).first()
    ctx = {
        "sessao": sessao, "aba": aba, "pode_gerir": gerir, "ata": ata,
        "escala": sessao.escala.select_related("cargo", "irmao"),
        "expedientes": _expedientes_da_sessao(sessao),
        "abas": [{"chave": k, "rotulo": n, "url": url_aba(sessao, k), "ativa": k == aba,
                  "badge": {"visitantes": sessao.visitantes.count() or "", "cerimonias": sessao.cerimonias.count() or ""}.get(k, "")}
                 for k, n in abas_ok],
    }
    if aba == "escala":
        atual = {e.cargo_id: e for e in sessao.escala.all()}
        ctx["linhas"] = [(c, atual.get(c.pk)) for c in Cargo.objects.filter(ativo=True)]
        ctx["irmaos"] = sessao.elegiveis().filter(grau__isnull=False)
    elif aba == "presenca":
        services.gerar_presencas(sessao)
        ctx["presencas"] = sessao.presencas.select_related("irmao")
        from apps.core.regimento import quorum

        ctx["quorum"] = quorum(sessao)
    elif aba == "visitantes":
        ctx["visitas"] = sessao.visitantes.select_related("visitante", "certificado")
        ctx["existentes"] = Visitante.objects.exclude(visitas__sessao=sessao)
        ctx["novo"] = extra.pop("novo", None) or VisitanteForm(prefix="novo")
        ctx["cert_status"] = {c.visita_id: c for c in CertificadoVisita.objects.filter(visita__sessao=sessao)}
    elif aba == "cerimonias":
        ctx["registradas"] = sessao.cerimonias.select_related("irmao")
        ctx["aprendizes"] = IrmaoModel.objects.filter(is_active=True, grau=P.APRENDIZ)
        ctx["companheiros"] = IrmaoModel.objects.filter(is_active=True, grau=P.COMPANHEIRO)
        ctx["aprovados"] = Candidato.objects.filter(etapa=Candidato.Etapa.APROVADO)
        ctx["pode_forcar"] = request.user.tem_perfil(P.VENERAVEL)
    ctx.update(extra)
    return render(request, "sessoes/detalhe.html", ctx)


@login_required
def detalhe(request, pk):
    sessao = _sessao_visivel(request, pk)
    return render_detalhe(request, sessao, request.GET.get("aba", "resumo"))


@login_required
def criar(request):
    if not _gerir(request.user):
        raise PermissionDenied
    form = SessaoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sessao = form.save()
        services.gerar_escala(sessao)
        messages.success(request, "Sessão agendada. A escala foi preenchida com os titulares da gestão.")
        return redirect("sessoes:detalhe", pk=sessao.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Nova sessão",
                                              "cancelar_url": "/sessoes/"})


@login_required
def editar(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    form = SessaoForm(request.POST or None, instance=sessao)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sessão atualizada.")
        return redirect("sessoes:detalhe", pk=pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Editar sessão",
                                              "cancelar_url": f"/sessoes/{pk}/"})


@login_required
def escala(request, pk):
    """O Venerável (ou o Secretário) define quem ocupa cada cargo na sessão."""
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    if request.method == "POST":
        for cargo in Cargo.objects.filter(ativo=True):
            valor = request.POST.get(f"cargo_{cargo.pk}", "")
            existente = Escala.objects.filter(sessao=sessao, cargo=cargo).first()
            if not valor:
                if existente:
                    existente.delete()
                continue
            irmao = get_object_or_404(Irmao, pk=valor, is_active=True, grau__isnull=False)
            from apps.cargos.models import Gestao

            titular = Gestao.objects.filter(ano=sessao.ano, cargo=cargo).first()
            titular_irmao = titular.irmao if titular else None
            Escala.objects.update_or_create(
                sessao=sessao, cargo=cargo,
                defaults={"irmao": irmao, "titular": titular_irmao,
                          "substituicao": bool(titular_irmao and titular_irmao.pk != irmao.pk)},
            )
        messages.success(request, "Escala da sessão salva.")
    return redirect(url_aba(sessao, "escala"))


@login_required
def presenca(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    services.gerar_presencas(sessao)
    if request.method == "POST":
        for p in sessao.presencas.all():
            situacao = request.POST.get(f"p_{p.irmao_id}")
            if situacao in Presenca.Situacao.values:
                p.situacao = situacao
                p.justificativa = request.POST.get(f"j_{p.irmao_id}", "")[:200]
                p.save()
        messages.success(request, "Presença registrada.")
    return redirect(url_aba(sessao, "presenca"))


@login_required
@require_POST
def concluir(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    sessao.status = Sessao.Status.REALIZADA
    sessao.save()
    services.gerar_presencas(sessao)
    from apps.expediente.models import Correspondencia

    Correspondencia.objects.filter(leva_a_sessao=True, lida_em_sessao__isnull=True,
                                   data__lte=sessao.data_hora.date()).update(lida_em_sessao=sessao)
    from apps.core.regimento import quorum

    presentes, minimo, ok = quorum(sessao)
    if not ok:
        messages.warning(request, f"Atenção: quórum não atingido ({presentes} presente(s); mínimo {minimo}). "
                                  "Registre a justificativa na ata.")
    messages.success(request, "Sessão marcada como realizada. A frequência foi atualizada.")
    return redirect("sessoes:detalhe", pk=pk)


def _contexto_convocacao(sessao):
    return {"sessao": sessao, "escala": sessao.escala.select_related("cargo", "irmao")}


@login_required
def convocacao_pdf(request, pk):
    sessao = _sessao_visivel(request, pk)
    dados = pdf_bytes("sessoes/convocacao_pdf.html", _contexto_convocacao(sessao), request)
    return resposta_pdf(f"convocacao-{sessao.data_hora:%Y%m%d}.pdf", dados)


@login_required
@require_POST
def enviar_convocacao(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    dados = pdf_bytes("sessoes/convocacao_pdf.html", _contexto_convocacao(sessao), request)
    loja = Loja.atual()
    ok = falha = 0
    for irmao in sessao.elegiveis().exclude(email=""):
        corpo = (
            f"Prezado Irmão {irmao.nome_completo},\n\n"
            f"Convocamos para a Sessão {sessao.titulo}, em {sessao.data_hora:%d/%m/%Y às %H:%M}"
            f"{', ' + sessao.local if sessao.local else ''}.\n\nA convocação com a pauta segue em anexo.\n\n"
            f"Fraterno abraço,\n{loja.nome}"
        )
        enviado = enviar_email(irmao.email, f"Convocação — {sessao.titulo} — {sessao.data_hora:%d/%m/%Y}", corpo,
                               anexos=[("convocacao.pdf", dados, "application/pdf")], contexto="convocacao")
        ok += enviado
        falha += not enviado
    sessao.convocacao_enviada_em = timezone.now()
    sessao.save()
    messages.success(request, f"Convocação enviada: {ok} e-mail(s); {falha} falha(s).")
    return redirect("sessoes:detalhe", pk=pk)


@login_required
def frequencia(request):
    """Frequência dos irmãos no ano maçônico."""
    if not _gerir(request.user):
        irmaos = [request.user]
    else:
        irmaos = Irmao.objects.filter(is_active=True, grau__isnull=False)
    ano = AnoMaconico.atual()
    if request.GET.get("ano"):
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    linhas = [(i, services.frequencia(i, ano)) for i in irmaos]
    return render(request, "sessoes/frequencia.html", {
        "linhas": linhas, "ano": ano, "anos": AnoMaconico.objects.all(),
    })


@login_required
@require_POST
def cancelar(request, pk):
    """Cancela a sessão (não realizada e sem ata) e avisa os irmãos elegíveis por e-mail."""
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    if sessao.status == Sessao.Status.REALIZADA or hasattr(sessao, "ata"):
        messages.error(request, "Sessão realizada ou com ata não pode ser cancelada.")
        return redirect(url_aba(sessao))
    sessao.status = Sessao.Status.CANCELADA
    sessao.save()
    enviados = 0
    if request.POST.get("avisar"):
        loja = Loja.atual()
        motivo = request.POST.get("motivo", "").strip()
        for irmao in sessao.elegiveis().exclude(email=""):
            corpo = (f"Prezado Irmão {irmao.nome_completo},\n\nInformamos que a Sessão {sessao.titulo} marcada para "
                     f"{sessao.data_hora:%d/%m/%Y às %H:%M} foi CANCELADA." + (f"\nMotivo: {motivo}" if motivo else "")
                     + f"\n\nFraterno abraço,\n{loja.nome}")
            enviados += enviar_email(irmao.email, f"Sessão cancelada — {sessao.data_hora:%d/%m/%Y}", corpo, contexto="cancelamento")
    messages.success(request, "Sessão cancelada." + (f" {enviados} irmão(s) avisado(s) por e-mail." if enviados else ""))
    return redirect(url_aba(sessao))
