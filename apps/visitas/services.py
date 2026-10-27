from django.db import transaction
from django.utils import timezone

from apps.core.assinatura import calcular_hash_assinatura, novo_codigo

from .models import AssinaturaCertificado, AutorizacaoAssinaturaLote, CertificadoVisita


@transaction.atomic
def aplicar_autorizacoes(sessao):
    """Aplica as assinaturas pré-autorizadas (dentro da validade) aos certificados da sessão. Devolve quantas."""
    agora = timezone.now()
    aplicadas = 0
    for aut in sessao.autorizacoes_certificado.select_related("irmao"):
        if not aut.valida_em(agora):
            continue
        for cert in CertificadoVisita.objects.filter(visita__sessao=sessao):
            if cert.assinaturas.filter(funcao=aut.funcao).exists():
                continue
            codigo = novo_codigo()
            ass = AssinaturaCertificado(
                certificado=cert, funcao=aut.funcao, autorizacao=aut, irmao=aut.irmao, imagem=aut.imagem, foto=aut.foto,
                hash_documento=cert.hash_documento, ip=aut.ip, user_agent=aut.user_agent, latitude=aut.latitude,
                longitude=aut.longitude, precisao_m=aut.precisao_m, autenticacao_2fa=aut.autenticacao_2fa,
                assinado_em=aut.assinado_em, codigo=codigo, aceite=aut.aceite,
                texto_legal=(aut.texto_legal + f" Assinatura aplicada por pré-autorização registrada em "
                             f"{timezone.localtime(aut.assinado_em):%d/%m/%Y %H:%M}.").strip(),
            )
            ass.hash_assinatura = calcular_hash_assinatura(ass.hash_documento, ass.irmao.pk, ass.assinado_em, ass.ip,
                                                           codigo, ass.imagem)
            ass.save()
            cert.status = (CertificadoVisita.Status.ASSINADO if cert.assinaturas.count() >= 2
                           else CertificadoVisita.Status.PARCIAL)
            cert.save()
            aplicadas += 1
    return aplicadas
