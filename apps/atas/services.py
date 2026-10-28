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


def proximo_numero(sessao=None):
    """Próximo nº de ata: segue o último cadastrado; sem atas, parte do número inicial configurado na Loja.

    Com numeração por gestão, reinicia (a partir de 1) a cada ano maçônico.
    """
    from .models import Ata

    loja = Loja.atual()
    qs = Ata.objects.exclude(numero__isnull=True)
    if loja.ata_numeracao == "gestao" and sessao is not None:
        qs = qs.filter(sessao__ano=sessao.ano)
        ultimo = qs.order_by("-numero").first()
        return (ultimo.numero + 1) if ultimo else 1
    ultimo = qs.order_by("-numero").first()
    return (ultimo.numero + 1) if ultimo else max(loja.ata_numero_inicial, 1)


def avisar_signatarios(ata, base_url, lembrete=False, apenas_pendentes=True):
    """E-mail (SMTP) aos signatários que ainda não assinaram a versão atual, com link direto para assinar."""
    from django.urls import reverse
    from django.utils import timezone

    from apps.core.comunicacao import enviar_email

    loja = Loja.atual()
    link = base_url.rstrip("/") + reverse("atas:assinar", args=[ata.pk])
    enviados = 0
    for s in ata.faltam_assinar():
        assunto = ("Lembrete: " if lembrete else "") + f"Ata {ata.numero or 's/nº'} aguardando a sua assinatura"
        corpo = (f"Prezado Irmão {s.irmao.nome_completo},\n\nA ata da sessão {ata.sessao.titulo} de "
                 f"{ata.sessao.data_hora:%d/%m/%Y} foi aprovada e aguarda a sua assinatura eletrônica.\n\n"
                 f"Assine em: {link}\n(Acesso com o seu login; o conteúdo da ata não é enviado por e-mail.)\n\n"
                 f"Fraterno abraço,\n{loja.nome}")
        if s.irmao.email and enviar_email(s.irmao.email, assunto, corpo, contexto="ata-assinatura"):
            s.ultimo_aviso_em = timezone.now()
            s.save(update_fields=["ultimo_aviso_em"])
            enviados += 1
    return enviados
