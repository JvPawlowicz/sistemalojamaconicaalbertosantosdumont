"""Entrega protegida de arquivos enviados (nada em /media é público)."""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404

EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "gif", "webp"}


def validar_arquivo(arquivo, extensoes=EXTENSOES_PERMITIDAS):
    """Valida extensão e tamanho de um upload."""
    if not arquivo:
        return arquivo
    ext = Path(arquivo.name).suffix.lower().lstrip(".")
    if ext not in extensoes:
        raise ValidationError("Formato não permitido. Use: " + ", ".join(sorted(extensoes)).upper() + ".")
    if arquivo.size > settings.ARQUIVO_TAMANHO_MAXIMO:
        raise ValidationError("Arquivo maior que o limite de 15 MB.")
    return arquivo


def servir_arquivo(fieldfile, inline=True, cache=False):
    """Resposta com o arquivo, tipo conforme a extensão e sem permitir execução de conteúdo ativo."""
    if not fieldfile:
        raise Http404
    try:
        f = fieldfile.open("rb")
    except FileNotFoundError as exc:
        raise Http404 from exc
    tipo = mimetypes.guess_type(fieldfile.name)[0] or "application/octet-stream"
    if tipo not in ("application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"):
        tipo = "application/octet-stream"
        inline = False
    resp = FileResponse(f, content_type=tipo)
    nome = Path(fieldfile.name).name
    resp["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{nome}"'
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Content-Security-Policy"] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"
    resp["Cache-Control"] = "private, max-age=3600" if cache else "private, no-store"
    return resp


IMAGENS = {"png", "jpg", "jpeg", "webp", "gif"}
