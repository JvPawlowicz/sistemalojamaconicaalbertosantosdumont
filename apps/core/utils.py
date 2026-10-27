import hashlib
from datetime import date


def ano_maconico_de(data: date):
    """Ano maçônico vai de 1º de julho a 30 de junho. Devolve (inicio, fim, nome)."""
    ano_inicio = data.year if data.month >= 7 else data.year - 1
    return date(ano_inicio, 7, 1), date(ano_inicio + 1, 6, 30), f"{ano_inicio}/{ano_inicio + 1}"


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def ip_do_cliente(request) -> str:
    """IP do cliente, resistente a falsificação do cabeçalho X-Forwarded-For.

    Com PROXY_COUNT = N proxies confiáveis à frente do app, o IP do cliente é o N-ésimo a partir
    da direita da cadeia (o que o primeiro proxy confiável registrou). Sem proxy (N = 0), usa
    REMOTE_ADDR e ignora o cabeçalho enviado pelo cliente.
    """
    from django.conf import settings

    n = getattr(settings, "PROXY_COUNT", 0)
    if n:
        cadeia = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(cadeia) >= n:
            return cadeia[-n]
    return request.META.get("REMOTE_ADDR", "")


def somente_digitos(valor: str) -> str:
    return "".join(c for c in (valor or "") if c.isdigit())


def carimbo(dt) -> str:
    """Data/hora canônica para hashes: UTC, precisão de segundos (estável em backups e entre bancos)."""
    from datetime import timezone as _tz

    return dt.astimezone(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
