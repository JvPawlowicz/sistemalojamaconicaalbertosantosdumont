"""Presença por QR Code e sessão online."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
import hmac

from apps.core import perfis as P
from apps.core.pdf import qr_data_uri
from apps.core.utils import ip_do_cliente

from .models import Presenca, Sessao
from .views import url_aba


def _sessao_por_token(token):
    s = Sessao.objects.filter(token_presenca=token).first()
    if s is None or not hmac.compare_digest(s.token_presenca, token):
        raise Http404
    return s


def _situacao(sessao, user):
    """Devolve (pode, motivo)."""
    if sessao.status == Sessao.Status.CANCELADA:
        return False, "Esta sessão foi cancelada."
    if not user.pode_ver_grau(sessao.grau) or user.grau is None:
        return False, "Você não tem grau para esta sessão."
    inicio, fim = sessao.janela_presenca()
    agora = timezone.now()
    if agora < inicio:
        return False, f"O registro abre às {timezone.localtime(inicio):%H:%M} de {timezone.localtime(inicio):%d/%m}."
    if agora > fim:
        return False, "O período de registro de presença desta sessão já encerrou."
    return True, ""


@login_required
def registrar_qr(request, token):
    sessao = _sessao_por_token(token)
    pode, motivo = _situacao(sessao, request.user)
    ja = Presenca.objects.filter(sessao=sessao, irmao=request.user, situacao=Presenca.Situacao.PRESENTE).first()
    if request.method == "POST" and pode:
        p, _ = Presenca.objects.get_or_create(sessao=sessao, irmao=request.user)
        if p.situacao != Presenca.Situacao.PRESENTE:
            p.situacao = Presenca.Situacao.PRESENTE
            p.origem = "qr"
            p.registrada_em = timezone.now()
            p.ip = ip_do_cliente(request) or None
            p.justificativa = ""
            p.save()
        messages.success(request, "Presença registrada. Obrigado, Irmão!")
        return redirect(request.path)
    return render(request, "sessoes/presenca_qr.html", {"sessao": sessao, "pode": pode, "motivo": motivo, "ja": ja})


@login_required
@require_POST
def renovar_qr(request, pk):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    sessao.novo_token_presenca()
    messages.success(request, "Novo QR Code gerado. O anterior deixou de valer.")
    return redirect(url_aba(sessao, "presenca"))


@login_required
def qr_tela(request, pk):
    """Tela cheia com o QR Code (para projetar no templo ou na recepção)."""
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=pk)
    url = request.build_absolute_uri(reverse("sessoes:presenca_qr", args=[sessao.token_presenca]))
    return render(request, "sessoes/qr_tela.html", {"sessao": sessao, "qr": qr_data_uri(url), "url": url})


@login_required
def entrar_online(request, pk):
    """Entra na videoconferência da sessão e registra a presença remota."""
    sessao = get_object_or_404(Sessao, pk=pk)
    if not sessao.online or not sessao.link_online:
        raise Http404
    pode, motivo = _situacao(sessao, request.user)
    if request.method == "POST" and pode:
        p, _ = Presenca.objects.get_or_create(sessao=sessao, irmao=request.user)
        if p.situacao != Presenca.Situacao.PRESENTE:
            p.situacao = Presenca.Situacao.PRESENTE
            p.origem = "qr"
            p.remota = True
            p.registrada_em = timezone.now()
            p.ip = ip_do_cliente(request) or None
            p.save()
        return redirect(sessao.link_online)
    return render(request, "sessoes/entrar_online.html", {"sessao": sessao, "pode": pode, "motivo": motivo})
