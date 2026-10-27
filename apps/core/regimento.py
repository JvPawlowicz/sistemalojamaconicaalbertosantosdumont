"""Regras do regimento interno, configuráveis em Configurações (0 = desligada)."""
from apps.core.models import AnoMaconico, Loja


def faltas_consecutivas(irmao, ano):
    """Maior sequência atual de ausências NÃO justificadas (presença ou justificativa zera a contagem)."""
    from apps.sessoes.models import Presenca, Sessao

    qs = Presenca.objects.filter(irmao=irmao, sessao__ano=ano, sessao__status=Sessao.Status.REALIZADA) \
        .order_by("sessao__data_hora").values_list("situacao", flat=True)
    seq = 0
    for situacao in qs:
        seq = seq + 1 if situacao == Presenca.Situacao.AUSENTE else 0
    return seq


def alertas_de_frequencia(ano=None):
    """Lista de (irmão, motivo) conforme as regras configuradas."""
    from apps.irmaos.models import Irmao
    from apps.sessoes import services

    ano = ano or AnoMaconico.atual()
    loja = Loja.atual()
    saida = []
    if not (loja.limite_faltas_consecutivas or loja.frequencia_minima_percentual):
        return saida
    for i in Irmao.objects.filter(is_active=True, grau__isnull=False, situacao="ativo"):
        motivos = []
        if loja.limite_faltas_consecutivas:
            f = faltas_consecutivas(i, ano)
            if f >= loja.limite_faltas_consecutivas:
                motivos.append(f"{f} faltas consecutivas não justificadas (limite {loja.limite_faltas_consecutivas})")
        if loja.frequencia_minima_percentual:
            freq = services.frequencia(i, ano)
            if freq["percentual"] is not None and freq["total"] >= 3 and freq["percentual"] < loja.frequencia_minima_percentual:
                motivos.append(f"frequência de {freq['percentual']}% (mínimo {loja.frequencia_minima_percentual}%)".replace(".", ","))
        if motivos:
            saida.append((i, "; ".join(motivos)))
    return saida


def quorum(sessao):
    """(presentes, mínimo, atingido). Mínimo 0 = sem exigência."""
    from apps.sessoes.models import Presenca

    minimo = Loja.atual().quorum_minimo
    presentes = sessao.presencas.filter(situacao=Presenca.Situacao.PRESENTE).count()
    return presentes, minimo, (not minimo) or presentes >= minimo
