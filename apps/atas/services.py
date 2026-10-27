import re

from apps.core.models import Loja

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
_VAR = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def _cargo_na_escala(sessao, trecho):
    e = sessao.escala.select_related("irmao", "cargo").filter(cargo__nome__icontains=trecho).first()
    return e.irmao.nome_completo if e else "____________"


def variaveis_da_sessao(sessao):
    """Valores disponíveis para as variáveis dos modelos de texto."""
    from django.utils import timezone

    loja = Loja.atual()
    dt = timezone.localtime(sessao.data_hora)
    presentes = sessao.presencas.filter(situacao="presente").count()
    return {
        "data": f"{dt:%d/%m/%Y}",
        "data_extenso": f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}",
        "hora": f"{dt:%H:%M}",
        "grau": sessao.get_grau_display(),
        "tipo": sessao.get_tipo_display(),
        "local": sessao.local or "____________",
        "ano_maconico": sessao.ano.nome,
        "loja": loja.nome,
        "numero_loja": loja.numero or "____",
        "oriente": loja.oriente or "____________",
        "veneravel": _cargo_na_escala(sessao, "Venerável"),
        "secretario": _cargo_na_escala(sessao, "Secretário"),
        "presentes": str(presentes),
        "visitantes": str(sessao.visitantes.count()),
    }


def renderizar_modelo(texto, sessao):
    valores = variaveis_da_sessao(sessao)
    return _VAR.sub(lambda m: valores.get(m.group(1), m.group(0)), texto)


def proximo_numero():
    from .models import Ata

    ultimo = Ata.objects.exclude(numero__isnull=True).order_by("-numero").first()
    return (ultimo.numero + 1) if ultimo else 1
