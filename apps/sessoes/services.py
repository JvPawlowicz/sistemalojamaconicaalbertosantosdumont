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


# --- Cerimônias (iniciação, promoção, elevação) ---
class CerimoniaInvalida(Exception):
    pass


def _meses_entre(inicio, fim):
    return (fim.year - inicio.year) * 12 + fim.month - inicio.month - (1 if fim.day < inicio.day else 0)


@transaction.atomic
def registrar_cerimonia(sessao, irmao, tipo, usuario, forcar=False, observacao=""):
    """Registra a cerimônia e atualiza grau e data do irmão. Valida a sequência de graus e o interstício."""
    from apps.core import perfis as P
    from apps.core.models import Loja

    from .models import Cerimonia

    data = sessao.data_hora.date()
    loja = Loja.atual()
    regras = {
        Cerimonia.Tipo.PROMOCAO: (P.APRENDIZ, P.COMPANHEIRO, "data_promocao", "data_iniciacao",
                                  loja.intersticio_promocao_meses, "Aprendiz"),
        Cerimonia.Tipo.ELEVACAO: (P.COMPANHEIRO, P.MESTRE, "data_elevacao", "data_promocao",
                                  loja.intersticio_elevacao_meses, "Companheiro"),
    }
    if tipo not in regras:
        raise CerimoniaInvalida("Iniciações são registradas a partir do painel de candidatos.")
    grau_atual, grau_novo, campo_data, campo_anterior, intersticio, nome_grau = regras[tipo]
    if irmao.grau != grau_atual:
        raise CerimoniaInvalida(f"Só um {nome_grau} pode passar por essa cerimônia.")
    if Cerimonia.objects.filter(irmao=irmao, tipo=tipo).exists():
        raise CerimoniaInvalida("Esta cerimônia já foi registrada para o irmão.")
    anterior = getattr(irmao, campo_anterior)
    forcada = False
    if intersticio and anterior and _meses_entre(anterior, data) < intersticio:
        if not forcar:
            raise CerimoniaInvalida(
                f"Interstício mínimo de {intersticio} mês(es) não cumprido (desde {anterior:%d/%m/%Y}). "
                "Marque 'registrar mesmo assim' para prosseguir sob responsabilidade do Venerável.")
        forcada = True
    setattr(irmao, campo_data, data)
    irmao.grau = grau_novo
    irmao.save()
    return Cerimonia.objects.create(sessao=sessao, irmao=irmao, tipo=tipo, data=data, grau_resultante=grau_novo,
                                    registrada_por=usuario, forcada=forcada, observacao=observacao)


@transaction.atomic
def iniciar_candidato(candidato, sessao, usuario):
    """Cria o irmão (Aprendiz) a partir do candidato aprovado e registra a iniciação."""
    from django.utils.text import slugify

    from apps.candidatos.models import Candidato
    from apps.core import perfis as P
    from apps.irmaos.models import CategoriaIrmao, Irmao

    from .models import Cerimonia

    if candidato.etapa != Candidato.Etapa.APROVADO:
        raise CerimoniaInvalida("Só candidatos aprovados no escrutínio podem ser iniciados.")
    if not candidato.email:
        raise CerimoniaInvalida("Cadastre o e-mail do candidato para criar o acesso ao sistema.")
    base = slugify(candidato.nome).replace("-", ".") or "irmao"
    username, n = base, 1
    while Irmao.objects.filter(username=username).exists():
        n += 1
        username = f"{base}{n}"
    irmao = Irmao(
        username=username, nome_completo=candidato.nome, email=candidato.email, grau=P.APRENDIZ,
        data_iniciacao=sessao.data_hora.date(), data_nascimento=candidato.data_nascimento,
        telefone=candidato.telefone, profissao=candidato.profissao,
        categoria=CategoriaIrmao.objects.filter(ativo=True, isento=False).first(),
    )
    irmao.set_unusable_password()
    irmao.save()
    candidato.etapa = Candidato.Etapa.INICIADO
    candidato.etapa_desde = sessao.data_hora.date()
    candidato.save()
    Cerimonia.objects.create(sessao=sessao, irmao=irmao, tipo=Cerimonia.Tipo.INICIACAO, data=sessao.data_hora.date(),
                             grau_resultante=P.APRENDIZ, registrada_por=usuario)
    return irmao
