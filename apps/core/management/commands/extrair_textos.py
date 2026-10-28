"""Extrai o texto dos PDFs da Biblioteca já enviados (para a busca dentro dos documentos)."""
from django.core.management.base import BaseCommand

from apps.documentos.models import Documento


class Command(BaseCommand):
    help = "Extrai o texto dos PDFs que ainda não foram indexados."

    def handle(self, *args, **opts):
        n = 0
        for d in Documento.objects.filter(texto_extraido=""):
            if d.eh_pdf:
                texto = d.extrair_texto()
                if texto:
                    Documento.objects.filter(pk=d.pk).update(texto_extraido=texto)
                    n += 1
        self.stdout.write(f"{n} documento(s) indexado(s).")
