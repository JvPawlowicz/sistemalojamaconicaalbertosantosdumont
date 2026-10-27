"""Assinatura eletrônica avançada: coleta de evidências, hash e verificação."""
import base64
import re
import secrets
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import AceiteTermo, Loja, TermoAceite
from .utils import carimbo, ip_do_cliente, sha256_texto

_PNG_B64 = re.compile(r"^data:image/png;base64,([A-Za-z0-9+/=]+)$")
LIMITE_IMAGEM = 400_000  # bytes de texto base64


def _decimal(valor, casas=6, limite=180):
    try:
        d = Decimal(str(valor)).quantize(Decimal(1).scaleb(-casas))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if abs(d) <= limite else None


def validar_imagem_assinatura(data_url):
    if not data_url:
        return ""
    if len(data_url) > LIMITE_IMAGEM or not _PNG_B64.match(data_url):
        raise ValidationError("Desenho de assinatura inválido.")
    try:
        base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Desenho de assinatura inválido.") from exc
    return data_url


def novo_codigo():
    return secrets.token_hex(8).upper()


def calcular_hash_assinatura(hash_documento, irmao_id, assinado_em, ip, codigo, imagem):
    base = "|".join([hash_documento, str(irmao_id), carimbo(assinado_em), ip or "", codigo, sha256_texto(imagem or "")])
    return sha256_texto(base)


def evidencias_da_requisicao(request):
    """Monta os campos de evidência (sem hash_documento) a partir do POST e da sessão."""
    imagem = validar_imagem_assinatura(request.POST.get("assinatura_png", ""))
    foto = request.FILES.get("foto_assinatura")
    if not imagem and not foto:
        raise ValidationError("Desenhe a assinatura ou envie uma foto dela.")
    if foto and (foto.size > 3 * 1024 * 1024 or not (foto.content_type or "").startswith("image/")):
        raise ValidationError("A foto da assinatura deve ser uma imagem de até 3 MB.")
    termo = TermoAceite.vigente()
    aceite = None
    if termo:
        aceite = AceiteTermo.objects.filter(irmao=request.user, termo=termo).first()
        if aceite is None:
            raise ValidationError("É preciso aceitar o termo de assinatura eletrônica antes de assinar.")
    lat = _decimal(request.POST.get("latitude"), limite=90)
    lon = _decimal(request.POST.get("longitude"))
    prec = request.POST.get("precisao", "")
    return {
        "irmao": request.user,
        "imagem": imagem,
        "foto": foto,
        "ip": ip_do_cliente(request) or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
        "latitude": lat if lat is not None and lon is not None else None,
        "longitude": lon if lat is not None and lon is not None else None,
        "precisao_m": int(float(prec)) if prec.replace(".", "", 1).isdigit() else None,
        "autenticacao_2fa": bool(request.user.is_verified()),
        "aceite": aceite,
        "texto_legal": Loja.atual().texto_legal,
        "assinado_em": timezone.now().replace(microsecond=0),
    }


def preparar_assinatura(modelo, hash_documento, evidencias, **extra):
    """Cria (sem salvar) a assinatura com código e hash de integridade calculados."""
    codigo = novo_codigo()
    obj = modelo(hash_documento=hash_documento, codigo=codigo, **evidencias, **extra)
    obj.hash_assinatura = calcular_hash_assinatura(
        hash_documento, obj.irmao.pk, obj.assinado_em, obj.ip, codigo, obj.imagem
    )
    return obj


def assinatura_integra(obj):
    """Recalcula o hash da assinatura e compara com o registrado."""
    return obj.hash_assinatura == calcular_hash_assinatura(
        obj.hash_documento, obj.irmao_id, obj.assinado_em, obj.ip, obj.codigo, obj.imagem
    )
