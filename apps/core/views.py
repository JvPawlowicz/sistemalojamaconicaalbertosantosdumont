import base64
import io

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from . import perfis as P
from .forms import LojaForm, TokenForm
from .models import AceiteTermo, AnoMaconico, EmailLog, Loja, SolicitacaoLGPD, TermoAceite
from .utils import ip_do_cliente


def _qr_data_uri(texto):
    img = qrcode.make(texto)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@login_required
def painel(request):
    from apps.atas.models import Ata
    from apps.sessoes.models import Sessao
    from apps.tesouraria.models import Lancamento

    user = request.user
    hoje = timezone.localdate()
    ctx = {"ano": AnoMaconico.atual()}
    ctx["proximas"] = [
        s for s in Sessao.objects.filter(data_hora__date__gte=hoje, status=Sessao.Status.AGENDADA)
        .order_by("data_hora")[:8] if user.pode_ver_grau(s.grau)
    ]
    ctx["pendencias_assinatura"] = Ata.objects.pendentes_de(user)
    ctx["minhas_mensalidades"] = Lancamento.objects.filter(
        irmao=user, status__in=[Lancamento.Status.PENDENTE, Lancamento.Status.VENCIDO]
    )[:6]
    from apps.irmaos.models import Irmao

    ativos = Irmao.objects.filter(is_active=True, grau__isnull=False)
    ctx["aniversariantes"] = ativos.filter(data_nascimento__month=hoje.month).order_by("data_nascimento__day")
    if user.tem_algum_perfil(P.TESOUREIRO):
        from apps.tesouraria.services import saldo_caixa

        ctx["saldo"] = saldo_caixa()
        ctx["inadimplentes"] = Lancamento.objects.filter(status=Lancamento.Status.VENCIDO).count()
    from .pendencias import atalhos_do_usuario, tarefas_do_usuario

    ctx["tarefas"] = tarefas_do_usuario(user)
    ctx["atalhos"] = atalhos_do_usuario(user)
    if user.tem_algum_perfil(P.SECRETARIO, P.TESOUREIRO):
        ctx["indicadores"] = _indicadores(ctx["ano"])
    return render(request, "core/painel.html", ctx)


def _indicadores(ano):
    """Números do ano maçônico para o painel da gestão."""
    from apps.atas.models import Ata
    from apps.candidatos.models import Candidato
    from apps.irmaos.models import Irmao
    from apps.sessoes import services as ses
    from apps.sessoes.models import Sessao

    ativos = Irmao.objects.filter(is_active=True, grau__isnull=False)
    freqs = [f["percentual"] for f in (ses.frequencia(i, ano) for i in ativos) if f["percentual"] is not None]
    return {
        "irmaos": ativos.count(),
        "por_grau": [(n, ativos.filter(grau=g).count()) for g, n in P.GRAU_CHOICES],
        "frequencia_media": round(sum(freqs) / len(freqs), 1) if freqs else None,
        "sessoes_realizadas": Sessao.objects.filter(ano=ano, status=Sessao.Status.REALIZADA).count(),
        "atas_pendentes": Ata.objects.filter(status=Ata.Status.APROVADA).count(),
        "atas_sem_aprovacao": Ata.objects.filter(status__in=[Ata.Status.RASCUNHO, Ata.Status.CIRCULACAO]).count(),
        "candidatos": Candidato.objects.exclude(
            etapa__in=[Candidato.Etapa.INICIADO, Candidato.Etapa.REPROVADO, Candidato.Etapa.DESISTIU]).count(),
    }


@login_required
def aceite_termo(request):
    termo = TermoAceite.vigente()
    if not termo or request.user.aceites.filter(termo=termo).exists():
        return redirect("core:painel")
    if request.method == "POST":
        if request.POST.get("aceito") != "on":
            messages.error(request, "Marque a caixa para confirmar o aceite do termo.")
        else:
            AceiteTermo.objects.create(
                irmao=request.user, termo=termo, hash_termo=termo.hash,
                ip=ip_do_cliente(request) or None, user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            )
            messages.success(request, "Termo aceito. Obrigado!")
            return redirect("core:painel")
    return render(request, "core/aceite_termo.html", {"termo": termo, "loja": Loja.atual()})


def privacidade(request):
    return render(request, "core/privacidade.html")


# --- 2FA (TOTP) ---
@login_required
def configurar_2fa(request):
    user = request.user
    if user.totpdevice_set.filter(confirmed=True).exists() and not user.is_verified():
        return redirect("core:2fa_verificar")
    device = user.totpdevice_set.filter(confirmed=False).first() or TOTPDevice.objects.create(
        user=user, name="principal", confirmed=False
    )
    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["token"]):
            device.confirmed = True
            device.save()
            otp_login(request, device)
            sd, _ = StaticDevice.objects.get_or_create(user=user, name="recuperacao")
            sd.token_set.all().delete()
            codigos = []
            for _ in range(8):
                t = StaticToken.random_token()
                sd.token_set.create(token=t)
                codigos.append(t)
            return render(request, "core/2fa_codigos.html", {"codigos": codigos})
        form.add_error("token", "Código inválido. Verifique o horário do celular e tente de novo.")
    return render(request, "core/2fa_configurar.html", {"form": form, "qr": _qr_data_uri(device.config_url),
                                                         "chave": base64.b32encode(device.bin_key).decode()})


@login_required
def verificar_2fa(request):
    form = TokenForm(request.POST or None)
    destino = request.GET.get("next") or request.POST.get("next") or reverse("core:painel")
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = reverse("core:painel")
    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]
        for device in list(request.user.totpdevice_set.filter(confirmed=True)) + list(
            StaticDevice.objects.filter(user=request.user)
        ):
            if device.verify_token(token):
                otp_login(request, device)
                return redirect(destino)
        form.add_error("token", "Código inválido.")
    return render(request, "core/2fa_verificar.html", {"form": form, "next": destino})


# --- administração da Loja ---
@login_required
def configuracoes(request):
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    loja = Loja.atual()
    form = LojaForm(request.POST or None, request.FILES or None, instance=loja)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Configurações salvas.")
        return redirect("core:configuracoes")
    return render(request, "core/configuracoes.html", {"form": form, "termo": TermoAceite.vigente()})


@login_required
@require_POST
def novo_termo(request):
    """Publica uma nova versão do termo (exige novo aceite de todos)."""
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    texto = request.POST.get("texto", "").strip()
    if not texto:
        messages.error(request, "Informe o texto do termo.")
        return redirect("core:configuracoes")
    atual = TermoAceite.vigente()
    TermoAceite.objects.update(ativo=False)
    TermoAceite.objects.create(versao=(atual.versao + 1) if atual else 1, texto=texto, ativo=True)
    messages.success(request, "Nova versão do termo publicada. Todos deverão aceitar novamente.")
    return redirect("core:configuracoes")


@login_required
def relatorio_aceites(request):
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    from apps.irmaos.models import Irmao

    termo = TermoAceite.vigente()
    aceitos = set(AceiteTermo.objects.filter(termo=termo).values_list("irmao_id", flat=True)) if termo else set()
    irmaos = Irmao.objects.filter(is_active=True, grau__isnull=False)
    linhas = [(i, i.pk in aceitos) for i in irmaos]
    return render(request, "core/aceites.html", {"linhas": linhas, "termo": termo})


@login_required
def emails_enviados(request):
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    return render(request, "core/emails.html", {"emails": EmailLog.objects.all()[:200]})


# --- LGPD: direitos do titular ---
@login_required
def meus_dados(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo")
        mensagem = request.POST.get("mensagem", "").strip()
        if tipo in SolicitacaoLGPD.Tipo.values and mensagem:
            SolicitacaoLGPD.objects.create(irmao=request.user, tipo=tipo, mensagem=mensagem[:2000])
            messages.success(request, "Solicitação registrada. A Secretaria responderá em breve.")
        else:
            messages.error(request, "Informe o tipo e descreva a solicitação.")
        return redirect("core:meus_dados")
    return render(request, "core/meus_dados.html", {
        "solicitacoes": request.user.solicitacoes_lgpd.all(), "tipos": SolicitacaoLGPD.Tipo.choices,
    })


@login_required
def exportar_meus_dados(request):
    from django.http import HttpResponse

    from .lgpd import exportar_json

    resp = HttpResponse(exportar_json(request.user), content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="meus-dados.json"'
    return resp


@login_required
def solicitacoes_lgpd(request):
    if not request.user.tem_algum_perfil(P.SECRETARIO, P.ADMINISTRADOR):
        raise PermissionDenied
    if request.method == "POST":
        s = get_object_or_404(SolicitacaoLGPD, pk=request.POST.get("id"))
        status = request.POST.get("status")
        if status in (SolicitacaoLGPD.Status.ATENDIDA, SolicitacaoLGPD.Status.NEGADA):
            s.status = status
            s.resposta = request.POST.get("resposta", "")[:2000]
            s.resolvida_em = timezone.now()
            s.save()
            messages.success(request, "Solicitação atualizada.")
        return redirect("core:solicitacoes_lgpd")
    return render(request, "core/solicitacoes_lgpd.html", {"solicitacoes": SolicitacaoLGPD.objects.select_related("irmao")})


@login_required
def busca(request):
    """Busca rápida (Ctrl+K): páginas, irmãos, atas, sessões, documentos — respeitando perfil e grau."""
    from django.db.models import Q
    from django.http import JsonResponse

    from apps.atas.models import Ata
    from apps.documentos.models import Documento
    from apps.irmaos.models import Irmao
    from apps.sessoes.models import Sessao
    from . import navegacao as nav

    q = request.GET.get("q", "").strip()
    user = request.user
    resultados = []
    paginas = nav.paginas_para_busca(user)
    if not q:
        resultados += [{"grupo": "Ir para", **p} for p in paginas[:8]]
        return JsonResponse({"resultados": resultados})
    ql = q.lower()
    resultados += [{"grupo": "Ir para", **p} for p in paginas if ql in p["rotulo"].lower()][:6]
    for i in Irmao.objects.filter(grau__isnull=False).filter(
            Q(nome_completo__icontains=q) | Q(profissao__icontains=q) | Q(matricula__icontains=q))[:6]:
        resultados.append({"grupo": "Irmãos", "rotulo": f"{i.nome_completo} — {i.grau_nome}", "url": reverse("irmaos:detalhe", args=[i.pk])})
    if q.isdigit() or "ata" in ql:
        for a in Ata.objects.visiveis_para(user).filter(numero=int(q))[:4] if q.isdigit() else \
                Ata.objects.visiveis_para(user)[:4]:
            resultados.append({"grupo": "Atas", "rotulo": f"Ata {a.numero or 's/nº'} — {a.sessao.data_hora:%d/%m/%Y}",
                               "url": reverse("atas:detalhe", args=[a.pk])})
    for d in Documento.objects.filter(titulo__icontains=q)[:8]:
        if user.pode_ver_grau(d.grau_minimo):
            resultados.append({"grupo": "Biblioteca", "rotulo": d.titulo, "url": reverse("documentos:ver", args=[d.pk])})
    for s in Sessao.objects.filter(Q(local__icontains=q) | Q(pauta__icontains=q))[:6]:
        if user.pode_ver_grau(s.grau):
            resultados.append({"grupo": "Sessões", "rotulo": f"{s.data_hora:%d/%m/%Y} — {s.titulo}", "url": reverse("sessoes:detalhe", args=[s.pk])})
    if user.tem_perfil(P.SECRETARIO):
        from apps.visitas.models import Visitante

        for v in Visitante.objects.filter(Q(nome__icontains=q) | Q(loja_nome__icontains=q))[:4]:
            resultados.append({"grupo": "Visitantes", "rotulo": f"{v.nome} — {v.loja_nome}", "url": reverse("visitas:visitante_editar", args=[v.pk])})
    return JsonResponse({"resultados": resultados[:24]})
