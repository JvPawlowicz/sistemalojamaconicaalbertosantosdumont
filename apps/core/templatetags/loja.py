from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def icon(nome, classe=""):
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false"><use href="{}#i-{}"></use></svg>',
        classe, static("img/icons.svg"), nome,
    )


@register.filter
def tem_perfil(user, perfil):
    return user.is_authenticated and user.tem_perfil(perfil)


@register.filter
def pode_ver_grau(user, grau):
    return user.is_authenticated and user.pode_ver_grau(int(grau))


@register.filter
def get_item(dic, chave):
    try:
        return dic.get(chave)
    except AttributeError:
        return None


@register.filter
def moeda(valor):
    if valor in (None, ""):
        return "—"
    try:
        texto = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return valor
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter
def telefone(valor):
    d = "".join(c for c in str(valor or "") if c.isdigit())
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return valor or "—"


_STATUS = {
    "pago": "ok", "assinada": "ok", "assinado": "ok", "enviado": "ok", "realizada": "ok", "aprovado": "ok",
    "iniciado": "ok", "ativo": "ok", "isento": "info", "dispensado": "info", "previsto": "info",
    "pendente": "warn", "vencido": "danger", "rascunho": "muted", "circulacao": "info", "aprovada": "warn",
    "agendada": "info", "cancelada": "muted", "falha": "danger", "parcial": "warn", "gerado": "muted",
    "reprovado": "danger", "desistiu": "muted", "proposto": "info", "sindicancia": "warn", "escrutinio": "warn",
    "licenciado": "warn", "remido": "info", "afastado": "warn", "falecido": "muted", "desligado": "muted",
}


@register.simple_tag
def selo(valor, texto):
    return format_html('<span class="selo selo-{}">{}</span>', _STATUS.get(str(valor), "muted"), texto)


@register.simple_tag
def campo(bound):
    from django.template.loader import render_to_string

    return mark_safe(render_to_string("partials/campo.html", {"campo": bound}))


@register.simple_tag(takes_context=True)
def navegacao(context):
    """Menu lateral e abas da seção atual (definidos em apps/core/navegacao.py)."""
    from apps.core import navegacao as nav

    request = context["request"]
    user = request.user
    view_name = request.resolver_match.view_name if request.resolver_match else ""
    atual = nav.secao_da_view(view_name)
    grupos = {}
    for s in nav.secoes_visiveis(user):
        grupos.setdefault(s.grupo, []).append({"secao": s, "url": nav.entrada(s, user), "ativa": s is atual})
    abas = []
    if atual is not None:
        ativo = nav.item_ativo(atual, view_name)
        visiveis = nav.itens_visiveis(atual, user)
        if len(visiveis) > 1:
            from django.urls import reverse

            abas = [{"rotulo": i.rotulo, "url": reverse(i.url_name), "ativa": i is ativo} for i in visiveis]
    return {"grupos": grupos, "abas": abas, "secao": atual}


@register.filter
def campo_por_nome(form, nome):
    try:
        return form[nome]
    except KeyError:
        return None


@register.simple_tag
def querystring_sem_pagina(request):
    """Querystring atual sem o parâmetro de página, já pronta para anexar '&pagina=N'."""
    q = request.GET.copy()
    q.pop("pagina", None)
    texto = q.urlencode()
    return mark_safe(texto.replace("&", "&amp;") + "&amp;") if texto else ""
