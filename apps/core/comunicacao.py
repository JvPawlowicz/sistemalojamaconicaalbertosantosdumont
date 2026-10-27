"""Envio de e-mail (SMTP, canal principal) e WhatsApp (Evolution API, opcional)."""
import json
import logging
import urllib.request
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMessage

from .models import EmailLog
from .utils import somente_digitos

log = logging.getLogger(__name__)


def enviar_email(destinatario, assunto, corpo, anexos=None, contexto=""):
    """Envia um e-mail e registra o resultado. Devolve True se enviado."""
    registro = EmailLog.objects.create(destinatario=destinatario, assunto=assunto[:200], contexto=contexto)
    try:
        msg = EmailMessage(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [destinatario])
        for nome, conteudo, mimetype in anexos or []:
            msg.attach(nome, conteudo, mimetype)
        msg.send(fail_silently=False)
        registro.enviado = True
    except Exception as exc:  # noqa: BLE001 - qualquer falha de SMTP deve ser registrada
        log.warning("Falha ao enviar e-mail para %s: %s", destinatario, exc)
        registro.erro = str(exc)[:1000]
    registro.save()
    return registro.enviado


def normalizar_telefone_br(telefone):
    digitos = somente_digitos(telefone)
    if not digitos:
        return ""
    if digitos.startswith("55") and len(digitos) >= 12:
        return digitos
    return "55" + digitos


def link_whatsapp(telefone, mensagem):
    """Link wa.me com a mensagem preenchida (o usuário só clica e envia)."""
    numero = normalizar_telefone_br(telefone)
    return f"https://wa.me/{numero}?text={quote(mensagem)}" if numero else ""


def whatsapp_configurado():
    return bool(settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY and settings.EVOLUTION_INSTANCE)


def enviar_whatsapp_documento(telefone, legenda, nome_arquivo, conteudo_base64):
    """Envia um documento via Evolution API. Devolve (ok, erro)."""
    if not whatsapp_configurado():
        return False, "Evolution API não configurada"
    numero = normalizar_telefone_br(telefone)
    if not numero:
        return False, "Telefone inválido"
    url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/message/sendMedia/{settings.EVOLUTION_INSTANCE}"
    carga = {
        "number": numero,
        "mediatype": "document",
        "mimetype": "application/pdf",
        "caption": legenda,
        "fileName": nome_arquivo,
        "media": conteudo_base64,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(carga).encode(),
        headers={"Content-Type": "application/json", "apikey": settings.EVOLUTION_API_KEY},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - URL vem da configuração
            return 200 <= resp.status < 300, ""
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha no WhatsApp: %s", exc)
        return False, str(exc)[:300]
