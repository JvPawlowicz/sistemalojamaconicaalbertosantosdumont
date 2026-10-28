"""Central de pendências: o que o usuário precisa fazer agora, com link direto para a ação."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from . import perfis as P


def _t(texto, url, icone, nivel="atencao", acao="Abrir"):
    return {"texto": texto, "url": url, "icone": icone, "nivel": nivel, "acao": acao}


def tarefas_do_usuario(user):
    from apps.atas.models import Ata
    from apps.candidatos.models import Candidato
    from apps.core.models import SolicitacaoLGPD
    from apps.irmaos.models import Irmao
    from apps.sessoes.models import ConfirmacaoEvento, Evento, Sessao
    from apps.tesouraria.models import Lancamento
    from apps.visitas.models import CertificadoVisita

    agora = timezone.now()
    hoje = timezone.localdate()
    tarefas = []

    # --- para qualquer irmão ---
    for a in Ata.objects.pendentes_de(user):
        tarefas.append(_t(f"Assinar a ata {a.numero or 's/nº'} de {a.sessao.data_hora:%d/%m/%Y}",
                          reverse("atas:assinar", args=[a.pk]), "pen-line", "urgente", "Assinar"))
    em_aberto = Lancamento.objects.filter(irmao=user, status__in=["pendente", "vencido"])
    if em_aberto.exists():
        venc = em_aberto.filter(status="vencido").count()
        tarefas.append(_t(f"{em_aberto.count()} mensalidade(s) em aberto" + (f" ({venc} vencida(s))" if venc else ""),
                          reverse("tesouraria:minhas"), "banknote", "urgente" if venc else "atencao", "Ver"))
    respondidos = set(ConfirmacaoEvento.objects.filter(irmao=user).values_list("evento_id", flat=True))
    for e in Evento.objects.filter(data_hora__gt=agora, data_hora__lte=agora + timedelta(days=30)):
        if e.pk not in respondidos and user.pode_ver_grau(e.grau_minimo):
            tarefas.append(_t(f"Confirmar presença: {e.titulo} ({e.data_hora:%d/%m})",
                              reverse("sessoes:evento", args=[e.pk]), "calendar", "info", "Responder"))

    from apps.votacoes.models import Votacao

    for v in Votacao.objects.filter(status=Votacao.Status.ABERTA):
        if v.pode_votar(user)[0]:
            tarefas.append(_t(f"Votação aberta: {v.titulo}", reverse("votacoes:detalhe", args=[v.pk]), "vote", "urgente", "Votar"))

    # --- secretaria ---
    if user.tem_perfil(P.SECRETARIO):
        for s in Sessao.objects.filter(status=Sessao.Status.REALIZADA, ata__isnull=True).order_by("-data_hora")[:3]:
            tarefas.append(_t(f"Redigir a ata da sessão de {s.data_hora:%d/%m/%Y}", reverse("atas:criar", args=[s.pk]),
                              "scroll-text", "urgente", "Redigir"))
        for a in Ata.objects.filter(status=Ata.Status.CIRCULACAO)[:3]:
            tarefas.append(_t(f"Aprovar a ata {a.numero or 's/nº'} (em circulação)", reverse("atas:detalhe", args=[a.pk]),
                              "stamp", "atencao", "Aprovar"))
        faltam = Ata.objects.filter(status=Ata.Status.APROVADA).count()
        if faltam:
            tarefas.append(_t(f"{faltam} ata(s) aprovada(s) aguardando assinaturas", reverse("atas:lista") + "?status=aprovada",
                              "pen-line", "info", "Acompanhar"))
        prox = Sessao.objects.filter(status=Sessao.Status.AGENDADA, data_hora__gt=agora,
                                     data_hora__lte=agora + timedelta(days=7), convocacao_enviada_em__isnull=True).first()
        if prox:
            tarefas.append(_t(f"Enviar a convocação da sessão de {prox.data_hora:%d/%m}", reverse("sessoes:detalhe", args=[prox.pk]),
                              "send", "atencao", "Enviar"))
        aprovados = Candidato.objects.filter(etapa=Candidato.Etapa.APROVADO).count()
        if aprovados:
            tarefas.append(_t(f"{aprovados} candidato(s) aprovado(s) aguardando iniciação", reverse("candidatos:painel"),
                              "user-plus", "atencao", "Ver"))

        from .regimento import alertas_de_frequencia

        alertas = alertas_de_frequencia()
        if alertas:
            tarefas.append(_t(f"{len(alertas)} irmão(s) fora das regras de frequência do regimento",
                              reverse("relatorios:ver", args=["alertas-regimento"]), "triangle-alert", "atencao", "Ver"))

    # --- certificados de visita (Venerável/Secretário) ---
    for funcao, perfil in (("veneravel", P.VENERAVEL), ("secretario", P.SECRETARIO)):
        if user.tem_perfil(perfil):
            pend = [c for c in CertificadoVisita.objects.select_related("visita__sessao")
                    .exclude(status__in=["enviado"]) if not c.assinaturas.filter(funcao=funcao).exists()]
            if pend:
                sessao = pend[0].visita.sessao
                tarefas.append(_t(f"{len(pend)} certificado(s) de visita para assinar como "
                                  f"{'Venerável' if funcao == 'veneravel' else 'Secretário'}",
                                  reverse("visitas:assinar_lote", args=[sessao.pk]), "pen-line", "atencao", "Assinar em lote"))
                break
    if user.tem_perfil(P.SECRETARIO):
        prontos = CertificadoVisita.objects.filter(status__in=["assinado", "falha"]).select_related("visita__sessao").first()
        if prontos:
            tarefas.append(_t("Certificados assinados prontos para envio", reverse("visitas:sessao", args=[prontos.visita.sessao_id]),
                              "send", "atencao", "Enviar"))

    # --- tesouraria ---
    if user.tem_perfil(P.TESOUREIRO):
        venc = Lancamento.objects.filter(status="vencido").count()
        if venc:
            tarefas.append(_t(f"{venc} mensalidade(s) vencida(s) a cobrar", reverse("tesouraria:mensalidades") + "?status=vencido",
                              "banknote", "urgente", "Cobrar"))
        if not Lancamento.objects.filter(competencia=hoje.replace(day=1)).exists():
            tarefas.append(_t(f"Gerar as mensalidades de {hoje:%m/%Y}", reverse("tesouraria:mensalidades"), "refresh-cw",
                              "atencao", "Gerar"))
        sem_cat = Irmao.objects.filter(is_active=True, grau__isnull=False, categoria__isnull=True).count()
        if sem_cat:
            tarefas.append(_t(f"{sem_cat} irmão(s) sem categoria de cobrança", reverse("irmaos:lista"), "users", "info", "Ajustar"))

    if user.tem_perfil(P.HOSPITALEIRO):
        from datetime import timedelta as _td

        from apps.hospitalaria.models import CasoHospitalaria

        limite = hoje - _td(days=15)
        atrasados = [c for c in CasoHospitalaria.objects.filter(status="acompanhando") if c.ultimo_contato < limite]
        if atrasados:
            tarefas.append(_t(f"{len(atrasados)} caso(s) de hospitalaria sem contato há mais de 15 dias",
                              reverse("hospitalaria:painel"), "heart-handshake", "atencao", "Ver"))

    # --- administração ---
    if user.tem_perfil(P.ADMINISTRADOR):
        abertas = SolicitacaoLGPD.objects.filter(status="aberta").count()
        if abertas:
            tarefas.append(_t(f"{abertas} solicitação(ões) LGPD aberta(s)", reverse("core:solicitacoes_lgpd"), "shield-check",
                              "atencao", "Responder"))
    ordem = {"urgente": 0, "atencao": 1, "info": 2}
    return sorted(tarefas, key=lambda t: ordem[t["nivel"]])


def atalhos_do_usuario(user):
    """Ações frequentes a um clique, conforme o perfil."""
    a = []
    if user.tem_perfil(P.SECRETARIO):
        a += [("Nova sessão", reverse("sessoes:criar"), "calendar-days"), ("Novo irmão", reverse("irmaos:criar"), "user-plus"),
              ("Registrar visita", reverse("visitas:nova_realizada"), "handshake"), ("Enviar documento", reverse("documentos:enviar"), "upload")]
    if user.tem_perfil(P.TESOUREIRO):
        a += [("Lançar no caixa", reverse("tesouraria:caixa"), "wallet"), ("Mensalidades", reverse("tesouraria:mensalidades"), "banknote")]
    a.append(("Agenda", reverse("sessoes:agenda"), "calendar"))
    return a
