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
from .models import AceiteTermo, AnoMaconico, Aviso, EmailLog, Loja, SolicitacaoLGPD, TermoAceite
from .utils import ip_do_cliente


def _qr_data_uri(texto):
    img = qrcode.make(texto)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


RECURSOS = [
    ("users", "Quadro de irmãos", "Cadastro completo, graus, cargos por ano maçônico, família e dados profissionais, com importação por planilha."),
    ("calendar-days", "Sessões e presença", "Agenda, pauta, escala de cargos com substituições, presença por QR Code e frequência automática."),
    ("scroll-text", "Atas e assinaturas", "Redação com textos pré-cadastrados, circulação, aprovação e assinatura eletrônica verificável."),
    ("wallet", "Tesouraria", "Mensalidades por categoria, caixa em tempo real, orçamento, PIX copia e cola e conciliação do extrato."),
    ("handshake", "Visitação", "Banco de visitantes, certificados em PDF assinados em lote e certificados recebidos de outras lojas."),
    ("book-open", "Biblioteca", "Documentos por grau, visualizador embutido e busca dentro do texto dos PDFs."),
    ("user-plus", "Candidatos e escrutínio", "Painel da sindicância, pareceres e votação sigilosa com resultado só no encerramento."),
    ("id-card", "Carteirinha digital", "Identificação do irmão com QR Code de verificação, direto no celular."),
    ("megaphone", "Mural de avisos", "Comunicados por grau, fixados no Início e por e-mail."),
    ("heart-handshake", "Hospitalaria e Tronco", "Acompanhamento sigiloso de irmãos enfermos e controle do Tronco de Beneficência."),
    ("chart-column", "Relatórios", "Frequência, financeiro, orçamento e prestação de contas do Conselho Fiscal em PDF, XLSX e CSV."),
    ("smartphone", "No celular", "Aplicativo instalável (PWA) para presença, atas e avisos."),
]
SEGURANCA = [
    ("shield-check", "Verificação em duas etapas", "Obrigatória para perfis administrativos, com códigos de recuperação."),
    ("lock", "Acesso por grau e perfil", "Cada irmão vê apenas o que o seu grau e a sua função permitem."),
    ("history", "Trilha de auditoria", "Quem alterou o quê e quando, com histórico das versões das atas."),
    ("file-check", "LGPD", "Termo de aceite, exportação dos próprios dados e canal de solicitações."),
    ("archive", "Backup criptografado", "Cópia completa com senha e restauração testada."),
]
PASSOS = [
    ("Convocação", "O Secretário agenda a sessão, define a pauta e envia a convocação por e-mail."),
    ("Presença", "Os irmãos registram a presença pelo QR Code ou o Secretário marca na lista."),
    ("Ata", "A ata é redigida com os textos pré-cadastrados e circula para aprovação."),
    ("Assinatura", "Cada signatário assina no próprio dispositivo; a ata recebe hash e QR de verificação."),
    ("Arquivo", "A ata assinada entra no livro de atas, e a frequência e os relatórios se atualizam sozinhos."),
]


def painel(request):
    if not request.user.is_authenticated:
        from .models import Loja

        return render(request, "core/landing.html", {"loja": Loja.atual(), "recursos": RECURSOS, "seguranca": SEGURANCA, "passos": PASSOS})
    return _painel_logado(request)


@login_required
def _painel_logado(request):
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

    ctx["avisos"] = Aviso.vigentes_para(user)[:3]
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
    from .crud import paginar

    pagina = paginar(request, EmailLog.objects.all(), 50)
    return render(request, "core/emails.html", {"emails": pagina, "pagina": pagina})


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


def brasao(request):
    """Brasão da Loja (institucional; aparece também na tela de login)."""
    from .arquivos import servir_arquivo

    return servir_arquivo(Loja.atual().brasao, cache=True)


def imagem_identidade(request):
    """Imagem de identidade visual (busto) — pública, usada na entrada e na página inicial."""
    from .arquivos import servir_arquivo

    return servir_arquivo(Loja.atual().imagem_identidade, cache=True)


@login_required
def foto_irmao(request, pk):
    from apps.irmaos.models import Irmao

    from .arquivos import servir_arquivo

    irmao = get_object_or_404(Irmao, pk=pk, grau__isnull=False)
    return servir_arquivo(irmao.foto, cache=True)


@login_required
@require_POST
def testar_email(request):
    """Envia um e-mail de teste ao próprio administrador (valida a configuração SMTP)."""
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    from django.conf import settings

    from .comunicacao import enviar_email

    if not request.user.email:
        messages.error(request, "Seu cadastro não tem e-mail.")
    elif enviar_email(request.user.email, "Teste de e-mail — sistema da Loja",
                      "Se você recebeu esta mensagem, o envio por SMTP está funcionando.", contexto="teste"):
        modo = "SMTP" if settings.EMAIL_BACKEND.endswith("smtp.EmailBackend") else f"modo de desenvolvimento ({settings.EMAIL_BACKEND.rsplit('.', 2)[-2]})"
        messages.success(request, f"E-mail de teste enviado para {request.user.email} via {modo}.")
    else:
        ultimo = EmailLog.objects.first()
        messages.error(request, f"Falha no envio: {ultimo.erro if ultimo else 'erro desconhecido'}")
    return redirect("core:configuracoes")


@login_required
@require_POST
def testar_whatsapp(request):
    if not request.user.tem_perfil(P.ADMINISTRADOR):
        raise PermissionDenied
    from .comunicacao import whatsapp_status

    ok, texto = whatsapp_status()
    (messages.success if ok else messages.warning)(request, texto)
    return redirect("core:configuracoes")


def manifest(request):
    """Manifesto do aplicativo instalável (PWA)."""
    from django.http import JsonResponse
    from django.templatetags.static import static

    loja = Loja.atual()
    dados = {
        "name": f"{loja.nome} — Sistema", "short_name": "Loja", "lang": "pt-BR", "start_url": reverse("core:painel"),
        "scope": "/", "display": "standalone", "background_color": "#f1f8fd", "theme_color": "#4fb3e8",
        "description": "Gestão da Loja: sessões, atas, tesouraria e muito mais.",
        "icons": [
            {"src": static("icons/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Agenda", "url": reverse("sessoes:agenda")},
            {"name": "Atas", "url": reverse("atas:lista")},
            {"name": "Carteirinha", "url": "/carteirinha/"},
        ],
    }
    return JsonResponse(dados, content_type="application/manifest+json")


def service_worker(request):
    """Service worker na raiz (escopo total). Só guarda arquivos estáticos; páginas autenticadas nunca são armazenadas."""
    from django.http import HttpResponse

    js = """
const VERSAO = 'loja-v1';
const ESTATICOS = ['/offline/'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(ESTATICOS))); self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSAO).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url); if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(caches.open(VERSAO).then((c) => c.match(req).then((hit) => hit || fetch(req).then((r) => { if (r.ok) c.put(req, r.clone()); return r; }))));
    return;
  }
  if (req.mode === 'navigate') { e.respondWith(fetch(req).catch(() => caches.match('/offline/'))); }
});
"""
    resp = HttpResponse(js, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def offline(request):
    return render(request, "core/offline.html")
