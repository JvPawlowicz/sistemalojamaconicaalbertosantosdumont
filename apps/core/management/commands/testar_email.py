from django.core.management.base import BaseCommand

from apps.core.comunicacao import enviar_email
from apps.core.models import EmailLog


class Command(BaseCommand):
    help = "Envia um e-mail de teste para validar a configuração SMTP."

    def add_arguments(self, parser):
        parser.add_argument("destino")

    def handle(self, *args, **opts):
        ok = enviar_email(opts["destino"], "Teste de e-mail — sistema da Loja",
                          "Se você recebeu esta mensagem, o envio por SMTP está funcionando.", contexto="teste")
        if ok:
            self.stdout.write(self.style.SUCCESS("E-mail enviado."))
        else:
            self.stderr.write(self.style.ERROR(f"Falha: {EmailLog.objects.first().erro}"))
            raise SystemExit(1)
