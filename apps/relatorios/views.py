from django.contrib.auth.decorators import login_required
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
    return render(request, "relatorios/indice.html", {"grupos": grupos})


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
