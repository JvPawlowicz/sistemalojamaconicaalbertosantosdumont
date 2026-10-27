"""Restaura um backup gerado por backup_dados. DESTRUTIVO: apaga os dados atuais do banco."""
import io
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from .backup_dados import descriptografar


class Command(BaseCommand):
    help = "Restaura dados e arquivos de um backup (apaga os dados atuais)."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")
        parser.add_argument("--confirmar", action="store_true", help="Confirma que os dados atuais serão substituídos")

    def handle(self, *args, **opts):
        if not opts["confirmar"]:
            raise CommandError("Operação destrutiva: repita com --confirmar para substituir os dados atuais.")
        bruto = Path(opts["arquivo"]).read_bytes()
        conteudo = descriptografar(bruto, os.environ.get("BACKUP_PASSPHRASE", ""))
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(fileobj=io.BytesIO(conteudo), mode="r:gz") as tar:
                for m in tar.getmembers():  # evita caminhos fora do diretório temporário
                    if m.name.startswith(("/", "..")) or ".." in Path(m.name).parts or m.issym() or m.islnk():
                        raise CommandError(f"Backup inválido (membro suspeito: {m.name})")
                tar.extractall(tmp, filter="data")
            dados = Path(tmp) / "dados.json"
            if not dados.exists():
                raise CommandError("Backup inválido: dados.json ausente.")
            call_command("flush", interactive=False, verbosity=0)
            call_command("loaddata", str(dados), verbosity=0)
            origem = Path(tmp) / "media"
            if origem.exists():
                destino = Path(settings.MEDIA_ROOT)
                destino.mkdir(parents=True, exist_ok=True)
                shutil.copytree(origem, destino, dirs_exist_ok=True)
        self.stdout.write(self.style.SUCCESS("Backup restaurado."))
