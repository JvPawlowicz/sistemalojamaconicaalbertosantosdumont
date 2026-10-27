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
