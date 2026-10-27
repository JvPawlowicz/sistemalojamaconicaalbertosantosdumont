from django.db import transaction

from apps.cargos.models import Gestao

from .models import Escala, Presenca, Sessao


@transaction.atomic
def gerar_escala(sessao):
    """Pré-preenche a escala com os titulares da gestão do ano (mantém o que já foi definido)."""
    for g in Gestao.objects.filter(ano=sessao.ano).select_related("cargo", "irmao"):
        Escala.objects.get_or_create(sessao=sessao, cargo=g.cargo, defaults={"irmao": g.irmao, "titular": g.irmao})


@transaction.atomic
def gerar_presencas(sessao):
    """Cria linhas de presença (ausente por padrão) para os irmãos elegíveis."""
    existentes = set(sessao.presencas.values_list("irmao_id", flat=True))
    novos = [Presenca(sessao=sessao, irmao=i) for i in sessao.elegiveis() if i.pk not in existentes]
    Presenca.objects.bulk_create(novos)


def frequencia(irmao, ano):
    """Frequência do irmão no ano maçônico: (presentes, justificadas, ausentes, total, percentual)."""
    qs = Presenca.objects.filter(irmao=irmao, sessao__ano=ano, sessao__status=Sessao.Status.REALIZADA)
    presentes = qs.filter(situacao=Presenca.Situacao.PRESENTE).count()
    justificadas = qs.filter(situacao=Presenca.Situacao.JUSTIFICADA).count()
    ausentes = qs.filter(situacao=Presenca.Situacao.AUSENTE).count()
    total = presentes + justificadas + ausentes
    return {
        "presentes": presentes, "justificadas": justificadas, "ausentes": ausentes, "total": total,
        "percentual": round(100 * presentes / total, 1) if total else None,
    }
