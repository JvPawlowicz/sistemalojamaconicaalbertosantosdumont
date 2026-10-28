import base64
import io

import qrcode
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import Loja


def emblema_data_uri():
    """Esquadro e compasso como data URI (cabeçalho de PDFs)."""
    from pathlib import Path

    arq = Path(__file__).resolve().parent.parent.parent / "static" / "img" / "emblema.svg"
    return "data:image/svg+xml;base64," + base64.b64encode(arq.read_bytes()).decode()


def _png_data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_data_uri(loja, maximo=360):
    """Brasão/logo da Loja reduzido, para o cabeçalho dos PDFs (vazio se não enviado)."""
    if not loja.brasao:
        return ""
    from PIL import Image

    try:
        with loja.brasao.open("rb") as f:
            img = Image.open(f).convert("RGBA")
        img.thumbnail((maximo, maximo))
        return _png_data_uri(img)
    except Exception:  # noqa: BLE001 - imagem ilegível não deve impedir o PDF
        return ""


def marca_dagua_data_uri(loja):
    """Marca d'água com a transparência já aplicada (o WeasyPrint não suporta opacidade em fundo de página)."""
    if not loja.marca_dagua:
        return ""
    from PIL import Image

    try:
        with loja.marca_dagua.open("rb") as f:
            img = Image.open(f).convert("RGBA")
        img.thumbnail((1000, 1000))
        fator = max(3, min(30, loja.marca_dagua_intensidade)) / 100
        alfa = img.getchannel("A").point(lambda v: int(v * fator))
        img.putalpha(alfa)
        return _png_data_uri(img)
    except Exception:  # noqa: BLE001
        return ""


def qr_data_uri(texto):
    img = qrcode.make(texto, box_size=4, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class PDFIndisponivel(Exception):
    """As bibliotecas do WeasyPrint (Pango/GTK) não estão instaladas neste computador."""


def pdf_bytes(template, contexto, request=None):
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # bibliotecas nativas ausentes (comum no Windows)
        raise PDFIndisponivel(str(exc)) from exc

    loja = Loja.atual()
    contexto = {"loja": loja, "emblema": emblema_data_uri(), "logo": logo_data_uri(loja), "marca": marca_dagua_data_uri(loja), **contexto}
    html = render_to_string(template, contexto, request=request)
    return HTML(string=html, base_url=str(request.build_absolute_uri("/")) if request else None).write_pdf()


def resposta_pdf(nome, dados, inline=True):
    resp = HttpResponse(dados, content_type="application/pdf")
    resp["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{nome}"'
    return resp
