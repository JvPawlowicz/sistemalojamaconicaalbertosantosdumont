"""Rotina diária (agendar no cron/systemd): lembrete de sessão, vencimentos e cobrança semanal.

Exemplo de cron:  0 8 * * *  cd /app && python manage.py enviar_lembretes
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.comunicacao import enviar_email
from apps.core.models import Loja
from apps.sessoes.models import Sessao
from apps.tesouraria import services as tes
from apps.tesouraria.models import Lancamento


class Command(BaseCommand):
    help = "Envia lembretes automáticos e atualiza mensalidades vencidas."

    def handle(self, *args, **opts):
        agora = timezone.now()
        loja = Loja.atual()
        vencidos = tes.atualizar_vencidos()
        self.stdout.write(f"{vencidos} mensalidade(s) marcada(s) como vencida(s).")

        enviados = 0
        if loja.lembrete_sessao_horas:
            limite = agora + timedelta(hours=loja.lembrete_sessao_horas)
            for s in Sessao.objects.filter(status=Sessao.Status.AGENDADA, data_hora__gt=agora, data_hora__lte=limite,
                                           lembrete_enviado_em__isnull=True):
                for irmao in s.elegiveis().exclude(email=""):
                    corpo = (f"Prezado Irmão {irmao.nome_completo},\n\nLembramos da Sessão {s.titulo}, em "
                             f"{timezone.localtime(s.data_hora):%d/%m/%Y às %H:%M}{', ' + s.local if s.local else ''}.\n\n"
                             f"Fraterno abraço,\n{loja.nome}")
                    enviados += enviar_email(irmao.email, f"Lembrete — {s.titulo}", corpo, contexto="lembrete")
                s.lembrete_enviado_em = agora
                s.save(update_fields=["lembrete_enviado_em"])
        self.stdout.write(f"{enviados} lembrete(s) de sessão enviado(s).")

        from django.conf import settings

        from apps.atas.models import Ata
        from apps.atas.services import avisar_signatarios

        avisos = 0
        for ata in Ata.objects.filter(status=Ata.Status.APROVADA, aprovada_em__lte=agora - timedelta(days=2)):
            recente = ata.signatarios.filter(ultimo_aviso_em__gt=agora - timedelta(days=3)).exists()
            if not recente:
                avisos += avisar_signatarios(ata, settings.SITE_URL, lembrete=True)
        self.stdout.write(f"{avisos} lembrete(s) de assinatura de ata enviado(s).")

        cobrancas = 0
        if loja.cobranca_automatica:
            for l in Lancamento.objects.filter(status=Lancamento.Status.VENCIDO).select_related("irmao").exclude(irmao__email=""):
                if l.ultima_cobranca_em and agora - l.ultima_cobranca_em < timedelta(days=7):
                    continue
                if enviar_email(l.irmao.email, f"Cobrança — {l.descricao} {l.competencia:%m/%Y}",
                                tes.mensagem_cobranca(l), contexto="cobranca"):
                    l.ultima_cobranca_em = agora
                    l.save(update_fields=["ultima_cobranca_em"])
                    cobrancas += 1
        self.stdout.write(f"{cobrancas} cobrança(s) automática(s) enviada(s).")
