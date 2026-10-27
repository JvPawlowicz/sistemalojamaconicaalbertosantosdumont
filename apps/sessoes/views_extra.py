"""Cerimônias, agenda social (eventos) e agenda unificada."""
import calendar
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.core.forms import ModelFormBase
from apps.irmaos.models import Irmao

from . import services
from .models import Cerimonia, ConfirmacaoEvento, Evento, Sessao


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


# --- Cerimônias ---
@login_required
def cerimonias_sessao(request, sessao_pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    if request.method == "POST":
        irmao = get_object_or_404(Irmao, pk=request.POST.get("irmao"), is_active=True)
        try:
            c = services.registrar_cerimonia(sessao, irmao, request.POST.get("tipo"), request.user,
                                             forcar=bool(request.POST.get("forcar")) and request.user.tem_perfil(P.VENERAVEL),
                                             observacao=request.POST.get("observacao", "")[:200])
        except services.CerimoniaInvalida as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{c.get_tipo_display()} registrada: {irmao.nome_completo} agora é {irmao.grau_nome}.")
        return redirect("sessoes:cerimonias", sessao_pk=sessao.pk)
    from apps.candidatos.models import Candidato

    return render(request, "sessoes/cerimonias.html", {
        "sessao": sessao, "registradas": sessao.cerimonias.select_related("irmao"),
        "aprendizes": Irmao.objects.filter(is_active=True, grau=P.APRENDIZ),
        "companheiros": Irmao.objects.filter(is_active=True, grau=P.COMPANHEIRO),
        "aprovados": Candidato.objects.filter(etapa=Candidato.Etapa.APROVADO),
        "pode_forcar": request.user.tem_perfil(P.VENERAVEL),
    })


@login_required
@require_POST
def iniciar(request, sessao_pk):
    if not _gerir(request.user):
        raise PermissionDenied
    from apps.candidatos.models import Candidato

    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    cand = get_object_or_404(Candidato, pk=request.POST.get("candidato"))
    try:
        irmao = services.iniciar_candidato(cand, sessao, request.user)
    except services.CerimoniaInvalida as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"{irmao.nome_completo} iniciado como Aprendiz. Envie o convite de senha pelo cadastro do irmão.")
    return redirect("sessoes:cerimonias", sessao_pk=sessao.pk)


# --- Eventos (agenda social) ---
class EventoForm(ModelFormBase):
    class Meta:
        model = Evento
        fields = ["titulo", "tipo", "data_hora", "local", "descricao", "valor_por_pessoa", "grau_minimo"]
        widgets = {"data_hora": forms.DateTimeInput()}


@login_required
def eventos(request):
    lista = [e for e in Evento.objects.filter(data_hora__gte=timezone.now() - timedelta(days=1))
             if request.user.pode_ver_grau(e.grau_minimo)]
    minhas = {c.evento_id: c for c in ConfirmacaoEvento.objects.filter(irmao=request.user)}
    return render(request, "sessoes/eventos.html", {"eventos": lista, "minhas": minhas, "pode_gerir": _gerir(request.user)})


@login_required
def evento_form(request, pk=None):
    if not _gerir(request.user):
        raise PermissionDenied
    evento = get_object_or_404(Evento, pk=pk) if pk else None
    form = EventoForm(request.POST or None, instance=evento)
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        if not e.pk:
            e.criado_por = request.user
        e.save()
        messages.success(request, "Evento salvo.")
        return redirect("sessoes:evento", pk=e.pk)
    return render(request, "crud/form.html", {"form": form, "titulo": "Editar evento" if pk else "Novo evento",
                                              "cancelar_url": "/sessoes/eventos/"})


@login_required
def evento(request, pk):
    e = get_object_or_404(Evento, pk=pk)
    if not request.user.pode_ver_grau(e.grau_minimo):
        raise PermissionDenied
    if request.method == "POST":
        resposta = request.POST.get("resposta")
        if resposta in ConfirmacaoEvento.Resposta.values:
            try:
                acomp = max(0, min(10, int(request.POST.get("acompanhantes") or 0)))
            except ValueError:
                acomp = 0
            ConfirmacaoEvento.objects.update_or_create(evento=e, irmao=request.user,
                                                       defaults={"resposta": resposta, "acompanhantes": acomp})
            messages.success(request, "Resposta registrada.")
        return redirect("sessoes:evento", pk=pk)
    return render(request, "sessoes/evento.html", {
        "e": e, "minha": e.confirmacoes.filter(irmao=request.user).first(), "pode_gerir": _gerir(request.user),
        "confirmacoes": e.confirmacoes.select_related("irmao") if _gerir(request.user) else [],
    })


# --- Agenda unificada ---
def _itens_do_mes(user, ano, mes):
    inicio = date(ano, mes, 1)
    fim = date(ano + (mes // 12), mes % 12 + 1, 1)
    itens = []
    for s in Sessao.objects.filter(data_hora__date__gte=inicio, data_hora__date__lt=fim):
        if user.pode_ver_grau(s.grau):
            itens.append((timezone.localtime(s.data_hora), "sessao", s.titulo, f"/sessoes/{s.pk}/"))
    for e in Evento.objects.filter(data_hora__date__gte=inicio, data_hora__date__lt=fim):
        if user.pode_ver_grau(e.grau_minimo):
            itens.append((timezone.localtime(e.data_hora), "evento", e.titulo, f"/sessoes/eventos/{e.pk}/"))
    for i in Irmao.objects.filter(is_active=True, grau__isnull=False, data_nascimento__month=mes):
        d = datetime(ano, mes, min(i.data_nascimento.day, calendar.monthrange(ano, mes)[1]), 0, 0,
                     tzinfo=timezone.get_current_timezone())
        itens.append((d, "aniversario", f"Aniversário de {i.nome_completo}", f"/irmaos/{i.pk}/"))
    return sorted(itens, key=lambda x: x[0])


@login_required
def agenda(request):
    hoje = timezone.localdate()
    try:
        a, m = request.GET.get("mes", "").split("-")
        ano, mes = int(a), int(m)
        date(ano, mes, 1)
    except (ValueError, TypeError):
        ano, mes = hoje.year, hoje.month
    anterior = date(ano - (1 if mes == 1 else 0), 12 if mes == 1 else mes - 1, 1)
    proximo = date(ano + (1 if mes == 12 else 0), 1 if mes == 12 else mes + 1, 1)
    por_dia = {}
    for dt, tipo, titulo, url in _itens_do_mes(request.user, ano, mes):
        por_dia.setdefault(dt.date(), []).append((dt, tipo, titulo, url))
    return render(request, "sessoes/agenda.html", {
        "ano": ano, "mes": mes, "dias": sorted(por_dia.items()), "anterior": anterior, "proximo": proximo,
        "mes_ref": date(ano, mes, 1),
    })


@login_required
def agenda_ics(request):
    """Exporta sessões e eventos futuros visíveis ao usuário (iCalendar)."""
    def esc(t):
        return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Sistema da Loja//PT-BR//", "CALSCALE:GREGORIAN"]
    agora = timezone.now()
    entradas = [(f"sessao-{s.pk}", s.data_hora, s.titulo, s.local) for s in Sessao.objects.filter(data_hora__gte=agora)
                if request.user.pode_ver_grau(s.grau)]
    entradas += [(f"evento-{e.pk}", e.data_hora, e.titulo, e.local) for e in Evento.objects.filter(data_hora__gte=agora)
                 if request.user.pode_ver_grau(e.grau_minimo)]
    for uid, inicio, titulo, local in entradas:
        fim = inicio + timedelta(hours=2)
        linhas += ["BEGIN:VEVENT", f"UID:{uid}@loja", f"DTSTAMP:{agora:%Y%m%dT%H%M%SZ}",
                   f"DTSTART:{inicio.astimezone(dt_timezone.utc):%Y%m%dT%H%M%SZ}", f"DTEND:{fim.astimezone(dt_timezone.utc):%Y%m%dT%H%M%SZ}",
                   f"SUMMARY:{esc(titulo)}", f"LOCATION:{esc(local or '')}", "END:VEVENT"]
    linhas.append("END:VCALENDAR")
    resp = HttpResponse("\r\n".join(linhas) + "\r\n", content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="agenda-loja.ics"'
    return resp
