import base64

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.core.arquivos import servir_arquivo
from apps.core.assinatura import evidencias_da_requisicao, novo_codigo, preparar_assinatura
from apps.core.comunicacao import enviar_email, enviar_whatsapp_documento
from apps.core.crud import CriarView, EditarView, ListaView
from apps.core.models import Loja
from apps.core.pdf import pdf_bytes, qr_data_uri, resposta_pdf
from apps.irmaos.models import Irmao
from apps.sessoes.models import Sessao

from .forms import VisitaRealizadaForm, VisitanteForm
from .models import AssinaturaCertificado, CertificadoVisita, VisitaRealizada, VisitaRecebida, Visitante


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


# --- visitas realizadas (certificados de outras lojas) ---
@login_required
def realizadas(request):
    qs = VisitaRealizada.objects.select_related("irmao")
    if not _gerir(request.user):
        qs = qs.filter(irmao=request.user)
    irmao = request.GET.get("irmao")
    if irmao and irmao.isdigit():
        qs = qs.filter(irmao_id=int(irmao))
    return render(request, "visitas/realizadas.html", {
        "visitas": qs, "pode_gerir": _gerir(request.user),
        "irmaos": Irmao.objects.filter(is_active=True, grau__isnull=False), "irmao_sel": irmao,
    })


@login_required
def nova_realizada(request):
    if not _gerir(request.user):
        raise PermissionDenied
    form = VisitaRealizadaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        v = form.save(commit=False)
        v.registrada_por = request.user
        v.save()
        messages.success(request, "Visita registrada e certificado vinculado ao irmão.")
        return redirect("visitas:realizadas")
    return render(request, "crud/form.html", {"form": form, "titulo": "Registrar visita a outra loja",
                                              "cancelar_url": reverse("visitas:realizadas"), "multipart": True})


@login_required
def certificado_recebido(request, pk):
    v = get_object_or_404(VisitaRealizada, pk=pk)
    if v.irmao_id != request.user.pk and not _gerir(request.user):
        raise PermissionDenied
    if request.GET.get("ver"):
        return render(request, "visitas/visualizar.html", {"v": v, "url_arquivo": reverse("visitas:certificado_recebido", args=[v.pk])})
    return servir_arquivo(v.certificado)


# --- banco de visitantes ---
class VisitantesView(ListaView):
    perfis_permitidos = (P.SECRETARIO,)
    titulo = "Banco de visitantes"
    subtitulo = "Visitantes recebidos pela Loja; reaproveitados em visitas futuras."
    colunas = [("Nome", lambda o: o.nome), ("Grau", lambda o: o.get_grau_display()), ("Loja", lambda o: o.loja_nome),
               ("Oriente", lambda o: o.oriente), ("Visitas", lambda o: o.visitas.count())]
    url_novo = "/visitas/visitantes/novo/"
    rotulo_novo = "Novo visitante"

    def get_objetos(self):
        return Visitante.objects.all()

    def url_de(self, obj):
        return reverse("visitas:visitante_editar", args=[obj.pk])


class NovoVisitante(CriarView):
    perfis_permitidos = (P.SECRETARIO,)
    model = Visitante
    form_class = VisitanteForm
    titulo = "Novo visitante"
    success_url = "/visitas/visitantes/"


class EditarVisitante(EditarView):
    perfis_permitidos = (P.SECRETARIO,)
    model = Visitante
    form_class = VisitanteForm
    titulo = "Editar visitante"
    success_url = "/visitas/visitantes/"


# --- visitantes recebidos na sessão ---
@login_required
def sessao_visitantes(request, sessao_pk):
    """Cadastro dos visitantes da sessão (Secretário ou irmão designado)."""
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    novo = VisitanteForm(prefix="novo")
    if request.method == "POST":
        if request.POST.get("existente"):
            vis = get_object_or_404(Visitante, pk=request.POST["existente"])
            VisitaRecebida.objects.get_or_create(sessao=sessao, visitante=vis, defaults={"registrada_por": request.user})
            messages.success(request, f"{vis.nome} registrado na sessão.")
            return redirect("visitas:sessao", sessao_pk=sessao.pk)
        novo = VisitanteForm(request.POST, prefix="novo")
        if novo.is_valid():
            vis = novo.save()
            VisitaRecebida.objects.get_or_create(sessao=sessao, visitante=vis, defaults={"registrada_por": request.user})
            messages.success(request, f"{vis.nome} cadastrado e registrado na sessão.")
            return redirect("visitas:sessao", sessao_pk=sessao.pk)
    return render(request, "visitas/sessao.html", {
        "sessao": sessao, "visitas": sessao.visitantes.select_related("visitante", "certificado"),
        "existentes": Visitante.objects.exclude(visitas__sessao=sessao), "novo": novo,
        "cert_status": {c.visita_id: c for c in CertificadoVisita.objects.filter(visita__sessao=sessao)},
    })


@login_required
@require_POST
def remover_visita(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    v = get_object_or_404(VisitaRecebida, pk=pk)
    sessao_pk = v.sessao_id
    if hasattr(v, "certificado") and v.certificado.assinaturas.exists():
        messages.error(request, "Não é possível remover: o certificado já foi assinado.")
    else:
        v.delete()
    return redirect("visitas:sessao", sessao_pk=sessao_pk)


# --- certificados de visita (assinatura e envio em lote) ---
@login_required
@require_POST
def gerar_certificados(request, sessao_pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    n = 0
    for v in sessao.visitantes.all():
        _, criado = CertificadoVisita.objects.get_or_create(visita=v, defaults={"codigo": novo_codigo()})
        n += criado
    messages.success(request, f"{n} certificado(s) gerado(s).")
    return redirect("visitas:sessao", sessao_pk=sessao.pk)


def _funcoes_do_usuario(user):
    funcoes = []
    if user.tem_perfil(P.VENERAVEL):
        funcoes.append(("veneravel", "Venerável Mestre"))
    if user.tem_perfil(P.SECRETARIO):
        funcoes.append(("secretario", "Secretário"))
    return funcoes


@login_required
def assinar_lote(request, sessao_pk):
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    funcoes = _funcoes_do_usuario(request.user)
    if not funcoes:
        raise PermissionDenied
    certs = CertificadoVisita.objects.filter(visita__sessao=sessao).select_related("visita__visitante")
    if request.method == "POST":
        funcao = request.POST.get("funcao")
        if funcao not in dict(funcoes):
            raise PermissionDenied
        try:
            evidencias = evidencias_da_requisicao(request)
            n = 0
            with transaction.atomic():
                for cert in certs:
                    if cert.assinaturas.filter(funcao=funcao).exists():
                        continue
                    ass = preparar_assinatura(AssinaturaCertificado, cert.hash_documento, evidencias,
                                              certificado=cert, funcao=funcao)
                    ass.save()
                    n += 1
                    cert.status = CertificadoVisita.Status.ASSINADO if cert.assinaturas.count() >= 2 \
                        else CertificadoVisita.Status.PARCIAL
                    cert.save()
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"{n} certificado(s) assinado(s) como {dict(funcoes)[funcao]}.")
            return redirect("visitas:sessao", sessao_pk=sessao.pk)
    pendentes = {f: sum(1 for c in certs if not c.assinaturas.filter(funcao=f).exists()) for f, _ in funcoes}
    return render(request, "visitas/assinar_lote.html", {
        "sessao": sessao, "funcoes": funcoes, "certs": certs, "pendentes": pendentes,
        "texto_legal": Loja.atual().texto_legal,
    })


def _pdf_certificado(request, cert):
    assinaturas = {a.funcao: a for a in cert.assinaturas.select_related("irmao")}
    url = request.build_absolute_uri(reverse("verificar", args=[cert.codigo]))
    return pdf_bytes("visitas/certificado_pdf.html", {
        "cert": cert, "v": cert.visita, "visitante": cert.visita.visitante, "sessao": cert.visita.sessao,
        "ass_veneravel": assinaturas.get("veneravel"), "ass_secretario": assinaturas.get("secretario"),
        "texto_legal": Loja.atual().texto_legal, "qr": qr_data_uri(url), "hash": cert.hash_documento,
    }, request)


@login_required
def certificado_pdf(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    cert = get_object_or_404(CertificadoVisita, pk=pk)
    return resposta_pdf(f"certificado-{cert.codigo}.pdf", _pdf_certificado(request, cert))


@login_required
@require_POST
def enviar_lote(request, sessao_pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    loja = Loja.atual()
    por_whatsapp = bool(request.POST.get("whatsapp"))
    enviados = falhas = sem_assinatura = 0
    for cert in CertificadoVisita.objects.filter(visita__sessao=sessao).select_related("visita__visitante"):
        if cert.assinaturas.count() < 2:
            sem_assinatura += 1
            continue
        vis = cert.visita.visitante
        dados = _pdf_certificado(request, cert)
        obs = []
        sucesso = False
        if vis.email:
            corpo = (f"Prezado Irmão {vis.nome},\n\nÉ com satisfação que agradecemos a sua visita à {loja.nome} "
                     f"na sessão de {sessao.data_hora:%d/%m/%Y}. Segue o certificado de visita assinado.\n\n"
                     f"Fraterno abraço,\n{loja.nome}")
            sucesso = enviar_email(vis.email, f"Certificado de visita — {loja.nome}", corpo,
                                   anexos=[(f"certificado-{cert.codigo}.pdf", dados, "application/pdf")],
                                   contexto="certificado")
            obs.append("e-mail ok" if sucesso else "e-mail falhou")
        else:
            obs.append("sem e-mail")
        if por_whatsapp and vis.whatsapp:
            ok, erro = enviar_whatsapp_documento(vis.whatsapp, f"Certificado de visita — {loja.nome}",
                                                 f"certificado-{cert.codigo}.pdf", base64.b64encode(dados).decode())
            obs.append("whatsapp ok" if ok else f"whatsapp falhou ({erro})")
            sucesso = sucesso or ok
        cert.status = CertificadoVisita.Status.ENVIADO if sucesso else CertificadoVisita.Status.FALHA
        cert.enviado_em = timezone.now() if sucesso else cert.enviado_em
        cert.envio_obs = "; ".join(obs)[:300]
        cert.save()
        enviados += sucesso
        falhas += not sucesso
    msg = f"{enviados} certificado(s) enviado(s); {falhas} com falha."
    if sem_assinatura:
        msg += f" {sem_assinatura} ainda sem as duas assinaturas."
    messages.success(request, msg)
    return redirect("visitas:sessao", sessao_pk=sessao.pk)
