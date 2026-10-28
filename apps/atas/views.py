from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core import perfis as P
from apps.core.assinatura import assinatura_integra, evidencias_da_requisicao, preparar_assinatura
from apps.core.comunicacao import enviar_email
from apps.core.crud import CriarView, EditarView, ListaView
from apps.core.models import Loja
from apps.core.pdf import pdf_bytes, qr_data_uri, resposta_pdf
from apps.irmaos.models import Irmao
from apps.sessoes.models import Sessao

from . import services
from .forms import AtaForm, ModeloTextoForm
from .models import Ata, AssinaturaAta, AtaSignatario, ModeloTexto


def _gerir(user):
    return user.tem_perfil(P.SECRETARIO)


def _ata_visivel(request, pk):
    ata = get_object_or_404(Ata.objects.visiveis_para(request.user), pk=pk)
    return ata


@login_required
def lista(request):
    atas = Ata.objects.visiveis_para(request.user).select_related("sessao")
    status = request.GET.get("status", "")
    if status in Ata.Status.values:
        atas = atas.filter(status=status)
    sem_ata = []
    if _gerir(request.user):
        sem_ata = Sessao.objects.filter(status=Sessao.Status.REALIZADA, ata__isnull=True).order_by("-data_hora")[:10]
    from apps.core.crud import paginar

    pagina = paginar(request, atas, 20)
    return render(request, "atas/lista.html", {
        "atas": pagina, "pagina": pagina, "status": status, "status_choices": Ata.Status.choices,
        "pode_gerir": _gerir(request.user), "sem_ata": sem_ata,
        "pendentes": Ata.objects.pendentes_de(request.user),
    })


@login_required
def criar(request, sessao_pk):
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=sessao_pk)
    if hasattr(sessao, "ata"):
        return redirect("atas:editar", pk=sessao.ata.pk)
    inicial = {"numero": services.proximo_numero(sessao)}
    cab = (ModeloTexto.objects.filter(atalho=f"ata-{sessao.tipo}", ativo=True).first()
           or ModeloTexto.objects.filter(categoria=ModeloTexto.Categoria.CABECALHO, ativo=True).first())
    if cab:
        from .sanitizar import texto_para_html

        inicial["conteudo"] = texto_para_html(services.renderizar_modelo(cab.texto, sessao)) + "<p></p>"
    form = AtaForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        ata = form.save(commit=False)
        ata.sessao = sessao
        ata.autor = request.user
        ata.save()
        messages.success(request, "Rascunho da ata criado.")
        return redirect("atas:editar", pk=ata.pk)
    return render(request, "atas/editor.html", {"form": form, "sessao": sessao, "ata": None})


@login_required
def editar(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    ata = get_object_or_404(Ata, pk=pk)
    if not ata.editavel:
        messages.error(request, "Esta ata já foi aprovada. Para alterar, crie uma nova versão.")
        return redirect("atas:detalhe", pk=pk)
    form = AtaForm(request.POST or None, instance=ata)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ata salva.")
        return redirect("atas:editar" if request.POST.get("continuar") else "atas:detalhe", pk=pk)
    return render(request, "atas/editor.html", {"form": form, "sessao": ata.sessao, "ata": ata})


@login_required
def detalhe(request, pk):
    ata = _ata_visivel(request, pk)
    user = request.user
    assinadas = {a.irmao_id: a for a in ata.assinaturas_validas.select_related("irmao")}
    signatarios = [(s, assinadas.get(s.irmao_id)) for s in ata.signatarios.select_related("irmao")]
    minha_pendente = any(s.irmao_id == user.pk and s.irmao_id not in assinadas for s, _ in signatarios) and \
        ata.status == Ata.Status.APROVADA
    candidatos = []
    if _gerir(user) and ata.status == Ata.Status.CIRCULACAO:
        escalados = set(ata.sessao.escala.filter(cargo__nome__icontains="Venerável").values_list("irmao_id", flat=True)) | \
            set(ata.sessao.escala.filter(cargo__nome__icontains="Secretário").values_list("irmao_id", flat=True))
        candidatos = [(i, i.pk in escalados) for i in ata.sessao.elegiveis().filter(grau__isnull=False)]
    return render(request, "atas/detalhe.html", {
        "ata": ata, "signatarios": signatarios, "minha_pendente": minha_pendente, "pode_gerir": _gerir(user),
        "candidatos": candidatos, "versoes_anteriores": ata.assinaturas.exclude(versao=ata.versao).count(),
    })


@login_required
@require_POST
def circular(request, pk):
    """Envia a ata (por link no sistema e e-mail SMTP) para leitura e aprovação na sessão."""
    if not _gerir(request.user):
        raise PermissionDenied
    ata = get_object_or_404(Ata, pk=pk)
    if not ata.editavel:
        raise PermissionDenied
    ata.status = Ata.Status.CIRCULACAO
    ata.circulacao_enviada_em = timezone.now()
    ata.save()
    ok = 0
    if request.POST.get("por_email"):
        link = request.build_absolute_uri(reverse("atas:detalhe", args=[ata.pk]))
        loja = Loja.atual()
        for irmao in ata.sessao.elegiveis().exclude(email=""):
            corpo = (f"Prezado Irmão {irmao.nome_completo},\n\nA minuta da ata da sessão {ata.sessao.titulo} de "
                     f"{ata.sessao.data_hora:%d/%m/%Y} está disponível para leitura e aprovação em sessão:\n{link}\n\n"
                     f"(Acesso com seu login; o conteúdo da ata não é enviado por e-mail.)\n\n{loja.nome}")
            ok += enviar_email(irmao.email, f"Minuta de ata — {ata.sessao.data_hora:%d/%m/%Y}", corpo, contexto="ata")
    messages.success(request, f"Ata em circulação no sistema.{f' E-mail enviado a {ok} irmão(s).' if ok else ''}")
    return redirect("atas:detalhe", pk=pk)


@login_required
@require_POST
def aprovar(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    ata = get_object_or_404(Ata, pk=pk)
    if ata.status not in (Ata.Status.CIRCULACAO, Ata.Status.RASCUNHO):
        raise PermissionDenied
    ids = [int(i) for i in request.POST.getlist("signatarios") if i.isdigit()]
    irmaos = list(ata.sessao.elegiveis().filter(pk__in=ids))
    if not irmaos:
        messages.error(request, "Escolha ao menos um signatário.")
        return redirect("atas:detalhe", pk=pk)
    with transaction.atomic():
        ata.signatarios.all().delete()
        for ordem, irmao in enumerate(irmaos):
            esc = ata.sessao.escala.filter(irmao=irmao).select_related("cargo").first()
            AtaSignatario.objects.create(ata=ata, irmao=irmao, ordem=ordem, funcao=esc.cargo.nome if esc else "")
        ata.status = Ata.Status.APROVADA
        ata.aprovada_em = timezone.now()
        ata.save()
        ata.arquivar_versao(request.user)
    avisados = services.avisar_signatarios(ata, request.build_absolute_uri("/"))
    messages.success(request, f"Ata aprovada. Os signatários já podem assinar ({avisados} aviso(s) enviado(s) por e-mail).")
    return redirect("atas:detalhe", pk=pk)


@login_required
def assinar(request, pk):
    ata = _ata_visivel(request, pk)
    if ata.status != Ata.Status.APROVADA or not ata.signatarios.filter(irmao=request.user).exists():
        raise PermissionDenied
    if ata.assinaturas_validas.filter(irmao=request.user).exists():
        messages.info(request, "Você já assinou esta ata.")
        return redirect("atas:detalhe", pk=pk)
    if request.method == "POST":
        try:
            evidencias = evidencias_da_requisicao(request)
            with transaction.atomic():
                ata = Ata.objects.select_for_update().get(pk=pk)
                if ata.status != Ata.Status.APROVADA:
                    raise ValidationError("A ata não está mais aberta para assinatura.")
                assinatura = preparar_assinatura(AssinaturaAta, ata.hash_conteudo, evidencias, ata=ata, versao=ata.versao)
                assinatura.save()
                if not ata.faltam_assinar():
                    ata.status = Ata.Status.ASSINADA
                    ata.save()
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, "Ata assinada. Código da assinatura: " + assinatura.codigo)
            return redirect("atas:detalhe", pk=pk)
    return render(request, "atas/assinar.html", {"ata": ata, "texto_legal": Loja.atual().texto_legal})


@login_required
@require_POST
def nova_versao(request, pk):
    if not _gerir(request.user):
        raise PermissionDenied
    ata = get_object_or_404(Ata, pk=pk)
    if ata.editavel:
        raise PermissionDenied
    with transaction.atomic():
        ata.arquivar_versao(request.user)
        ata.versao += 1
        ata.status = Ata.Status.RASCUNHO
        ata.aprovada_em = None
        ata.save()
        ata.signatarios.all().delete()
    messages.warning(request, f"Criada a versão {ata.versao}. As assinaturas anteriores deixam de valer para esta versão.")
    return redirect("atas:editar", pk=pk)


def _contexto_pdf(request, ata):
    assinaturas = list(ata.assinaturas_validas.select_related("irmao").order_by("assinado_em"))
    url = request.build_absolute_uri(reverse("verificar", args=[assinaturas[0].codigo])) if assinaturas else ""
    return {
        "ata": ata, "assinaturas": assinaturas, "texto_legal": Loja.atual().texto_legal,
        "hash": ata.hash_conteudo, "qr": qr_data_uri(url) if url else "",
        "minuta": ata.status != Ata.Status.ASSINADA,
        "faltam": ata.faltam_assinar() if ata.status == Ata.Status.APROVADA else [],
    }


@login_required
def pdf(request, pk):
    ata = _ata_visivel(request, pk)
    dados = pdf_bytes("atas/ata_pdf.html", _contexto_pdf(request, ata), request)
    return resposta_pdf(f"ata-{ata.numero or ata.pk}-v{ata.versao}.pdf", dados)


# --- Modelos de texto ---
class ModelosView(ListaView):
    perfis_permitidos = (P.SECRETARIO,)
    titulo = "Modelos de texto da ata"
    subtitulo = "Na digitação da ata, escreva @ para inserir um destes textos."
    colunas = [("Título", lambda o: o.titulo), ("Atalho", lambda o: "@" + o.atalho),
               ("Categoria", lambda o: o.get_categoria_display()), ("Ativo", lambda o: "Sim" if o.ativo else "Não")]
    url_novo = "/atas/modelos/novo/"
    rotulo_novo = "Novo modelo"
    acoes_extra = [("Carregar textos padrão", "/atas/modelos/padroes/")]

    def get_objetos(self):
        return ModeloTexto.objects.all()

    def url_de(self, obj):
        return reverse("atas:modelo_editar", args=[obj.pk])


class NovoModelo(CriarView):
    perfis_permitidos = (P.SECRETARIO,)
    model = ModeloTexto
    form_class = ModeloTextoForm
    titulo = "Novo modelo de texto"
    success_url = "/atas/modelos/"


class EditarModelo(EditarView):
    perfis_permitidos = (P.SECRETARIO,)
    model = ModeloTexto
    form_class = ModeloTextoForm
    titulo = "Editar modelo de texto"
    success_url = "/atas/modelos/"


@login_required
def buscar_modelos(request):
    """API do @ no editor: textos prontos (com as variáveis da sessão preenchidas) e nomes de irmãos."""
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=request.GET.get("sessao"))
    q = request.GET.get("q", "").strip().lower()
    itens = []
    for m in ModeloTexto.objects.filter(ativo=True):
        if q in m.titulo.lower() or q in m.atalho.lower() or q in m.get_categoria_display().lower():
            itens.append({"tipo": "modelo", "grupo": "Textos prontos", "titulo": m.titulo, "atalho": m.atalho,
                          "detalhe": f"@{m.atalho} · {m.get_categoria_display()}", "categoria": m.get_categoria_display(),
                          "texto": services.renderizar_modelo(m.texto, sessao)})
    itens = itens[:10]
    if q:
        for i in sessao.elegiveis().filter(nome_completo__icontains=q, grau__isnull=False)[:6]:
            titulo = "Ir∴ " + i.nome_completo
            itens.append({"tipo": "irmao", "grupo": "Irmãos", "titulo": i.nome_completo, "detalhe": i.grau_nome,
                          "texto": f"Ir∴ {i.nome_completo}"})
    return JsonResponse({"itens": itens})


@login_required
def renderizar_texto(request):
    """Preenche as variáveis de um trecho ({{data}}, {{veneravel}}…) para uma sessão."""
    if not _gerir(request.user):
        raise PermissionDenied
    sessao = get_object_or_404(Sessao, pk=request.GET.get("sessao"))
    return JsonResponse({"texto": services.renderizar_modelo(request.GET.get("texto", "")[:2000], sessao)})


def verificar(request, codigo):
    """Página pública de verificação de autenticidade (não expõe o conteúdo)."""
    from apps.visitas.models import AssinaturaCertificado, CertificadoVisita

    codigo = codigo.upper()
    ass = AssinaturaAta.objects.select_related("ata__sessao", "irmao").filter(codigo=codigo).first()
    if ass:
        outras = list(ass.ata.assinaturas.filter(versao=ass.versao).select_related("irmao"))
        return render(request, "atas/verificar.html", {
            "tipo": "ata", "ass": ass, "outras": outras, "integra": assinatura_integra(ass),
            "vigente": ass.versao == ass.ata.versao, "hash_atual": ass.ata.hash_conteudo,
            "documento_confere": (ass.hash_documento == ass.ata.hash_conteudo) if ass.versao == ass.ata.versao else
            bool(ass.ata.versoes.filter(versao=ass.versao, hash=ass.hash_documento).exists()),
            "loja": Loja.atual(),
        })
    cert = CertificadoVisita.objects.select_related("visita__visitante", "visita__sessao").filter(codigo=codigo).first()
    if cert:
        assinaturas = list(cert.assinaturas.select_related("irmao"))
        return render(request, "atas/verificar.html", {
            "tipo": "certificado", "cert": cert, "assinaturas": assinaturas,
            "integras": all(assinatura_integra(a) and a.hash_documento == cert.hash_documento for a in assinaturas),
            "loja": Loja.atual(),
        })
    raise Http404


@login_required
def livro_pdf(request):
    """Livro de atas do ano maçônico (atas assinadas, em ordem), para impressão/arquivo."""
    if not _gerir(request.user):
        raise PermissionDenied
    from apps.core.models import AnoMaconico

    ano = AnoMaconico.atual()
    if request.GET.get("ano", "").isdigit():
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    atas = Ata.objects.filter(sessao__ano=ano, status=Ata.Status.ASSINADA).select_related("sessao") \
        .order_by("sessao__data_hora")
    blocos = [{"ata": a, "assinaturas": list(a.assinaturas_validas.select_related("irmao")), "hash": a.hash_conteudo}
              for a in atas]
    dados = pdf_bytes("atas/livro_pdf.html", {"ano": ano, "blocos": blocos, "texto_legal": Loja.atual().texto_legal}, request)
    return resposta_pdf(f"livro-de-atas-{ano.nome.replace('/', '-')}.pdf", dados)


def _diff_html(antigo, novo):
    """Diferença linha a linha entre dois textos, já escapada para HTML."""
    import difflib

    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    a, b = antigo.splitlines(), novo.splitlines()
    saida = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            saida += [f"<div>{escape(l) or '&nbsp;'}</div>" for l in a[i1:i2]]
        else:
            saida += [f'<div class="dif-del">{escape(l) or "&nbsp;"}</div>' for l in a[i1:i2]]
            saida += [f'<div class="dif-ins">{escape(l) or "&nbsp;"}</div>' for l in b[j1:j2]]
    return mark_safe("".join(saida))


@login_required
def versoes(request, pk):
    """Histórico de versões da ata e comparação entre elas."""
    ata = _ata_visivel(request, pk)
    snaps = {v.versao: v for v in ata.versoes.all()}
    snaps.setdefault(ata.versao, None)
    from .sanitizar import texto_simples

    textos = {v.versao: (texto_simples(v.conteudo) if v.formato == "html" else v.conteudo) for v in ata.versoes.all()}
    textos[ata.versao] = ata.texto if ata.editavel or ata.versao not in textos else textos[ata.versao]
    numeros = sorted(textos)
    try:
        a = int(request.GET.get("a", numeros[-2] if len(numeros) > 1 else numeros[-1]))
        b = int(request.GET.get("b", numeros[-1]))
    except ValueError:
        a = b = numeros[-1]
    if a not in textos or b not in textos:
        a = b = numeros[-1]
    ass = {n: list(ata.assinaturas.filter(versao=n).select_related("irmao")) for n in numeros}
    return render(request, "atas/versoes.html", {
        "ata": ata, "numeros": numeros, "a": a, "b": b, "diff": _diff_html(textos[a], textos[b]),
        "assinaturas": ass, "snaps": snaps, "atual": ata.versao,
    })


@login_required
def carregar_padroes(request):
    """Cria os textos padrão que ainda não existem (não altera nem apaga os que a Secretaria já editou)."""
    if not request.user.tem_perfil(P.SECRETARIO):
        raise PermissionDenied
    from .modelos_padrao import MODELOS

    if request.method == "POST":
        novos = sum(ModeloTexto.objects.get_or_create(atalho=a, defaults={"titulo": t, "categoria": c, "texto": x})[1]
                    for t, a, c, x in MODELOS)
        messages.success(request, f"{novos} texto(s) padrão adicionado(s)." if novos else "Todos os textos padrão já estão cadastrados.")
        return redirect("atas:modelos")
    return render(request, "atas/padroes.html", {"total": len(MODELOS), "existentes": ModeloTexto.objects.count()})
