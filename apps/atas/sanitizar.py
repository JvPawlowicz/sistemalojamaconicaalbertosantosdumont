"""Sanitização do HTML da ata (editor rico) e utilidades de texto.

O HTML guardado é SEMPRE o resultado desta função: o hash da assinatura cobre exatamente o que foi sanitizado e
nenhum script, atributo de evento ou estilo arbitrário chega ao banco, às telas ou aos PDFs.
"""
import re

import nh3
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe

TAGS = {"p", "br", "h2", "h3", "strong", "em", "u", "ul", "ol", "li", "blockquote", "hr"}
ATRIBUTOS = {"p": {"style"}, "h2": {"style"}, "h3": {"style"}}
_ALINHAMENTO = re.compile(r"(?:^|;)\s*text-align:\s*(left|right|center|justify)\s*(?=;|$)", re.I)


def _filtrar_atributo(tag, atributo, valor):
    if atributo == "style":
        m = _ALINHAMENTO.search(valor)
        return f"text-align: {m.group(1).lower()}" if m else None
    return valor


def sanitizar_html(html: str) -> str:
    limpo = nh3.clean(html or "", tags=TAGS, attributes=ATRIBUTOS, attribute_filter=_filtrar_atributo,
                      link_rel=None, strip_comments=True)
    return limpo.strip()


def texto_simples(html: str) -> str:
    """Texto puro com quebras entre blocos (para busca, comparação de versões e e-mails)."""
    t = re.sub(r"</(p|h2|h3|li|blockquote)>", "\n", html or "", flags=re.I)
    t = re.sub(r"<(br|hr)\s*/?>", "\n", t, flags=re.I)
    t = strip_tags(t)
    import html as _h

    t = _h.unescape(t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def texto_para_html(texto: str) -> str:
    """Converte o texto simples (atas antigas) em parágrafos HTML seguros."""
    blocos = re.split(r"\n{2,}", (texto or "").strip())
    return "".join("<p>" + escape(b).replace("\n", "<br>") + "</p>" for b in blocos if b.strip())


def renderizar(ata) -> str:
    """HTML pronto para exibir/imprimir (já seguro)."""
    if ata.formato == "html":
        return mark_safe(sanitizar_html(ata.conteudo))
    return mark_safe(texto_para_html(ata.conteudo))
