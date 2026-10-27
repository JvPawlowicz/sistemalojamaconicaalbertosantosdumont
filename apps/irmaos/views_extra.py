import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core import perfis as P

from . import importacao
from .models import Irmao


@login_required
def importar(request):
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    resultado = None
    if request.method == "POST" and request.FILES.get("planilha"):
        arq = request.FILES["planilha"]
        aplicar = request.POST.get("acao") == "importar"
        try:
            criados, atualizados, erros = importacao.importar_irmaos(arq, aplicar=aplicar)
        except (ValidationError, Exception) as exc:  # noqa: BLE001 - planilha malformada
            messages.error(request, "Não foi possível ler a planilha: " + (" ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)))
        else:
            resultado = {"criados": criados, "atualizados": atualizados, "erros": erros, "aplicado": aplicar and not erros}
            if aplicar and not erros:
                messages.success(request, f"Importação concluída: {criados} novo(s), {atualizados} atualizado(s).")
            elif erros:
                messages.error(request, "A planilha tem erros. Nada foi gravado; corrija e envie novamente.")
    return render(request, "irmaos/importar.html", {"resultado": resultado, "colunas": importacao.COLUNAS})


@login_required
def modelo_importacao(request):
    resp = HttpResponse("﻿" + importacao.MODELO_CSV, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="modelo-importacao-irmaos.csv"'
    return resp


@login_required
@require_POST
def resetar_2fa(request, pk):
    """Remove os dispositivos 2FA do irmão (ele cadastra um novo no próximo acesso)."""
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    irmao = get_object_or_404(Irmao, pk=pk)
    if irmao.eh_desenvolvedor and not request.user.eh_desenvolvedor:
        raise PermissionDenied
    TOTPDevice.objects.filter(user=irmao).delete()
    StaticDevice.objects.filter(user=irmao).delete()
    messages.success(request, f"2FA de {irmao.nome_completo} redefinido.")
    return redirect("irmaos:detalhe", pk=pk)


@login_required
@require_POST
def alternar_acesso(request, pk):
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    irmao = get_object_or_404(Irmao, pk=pk)
    if irmao.pk == request.user.pk:
        messages.error(request, "Você não pode desativar o próprio acesso.")
    else:
        irmao.is_active = not irmao.is_active
        irmao.save()
        messages.success(request, f"Acesso de {irmao.nome_completo} {'reativado' if irmao.is_active else 'desativado'}.")
    return redirect("irmaos:detalhe", pk=pk)
