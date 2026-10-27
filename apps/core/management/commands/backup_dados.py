"""Backup portátil (independe do banco): dados em JSON + arquivos enviados, opcionalmente criptografado.

Uso:  BACKUP_PASSPHRASE='...' python manage.py backup_dados /caminho/destino
Restaurar com:  python manage.py restaurar_dados ARQUIVO --confirmar
"""
import base64
import io
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

EXCLUIR = ["contenttypes", "auth.permission", "sessions", "admin.logentry", "axes"]


def chave_da_senha(senha: str, sal: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=600_000)
    return base64.urlsafe_b64encode(kdf.derive(senha.encode()))


def criptografar(dados: bytes, senha: str) -> bytes:
    from cryptography.fernet import Fernet

    sal = os.urandom(16)
    return b"LOJABK1" + sal + Fernet(chave_da_senha(senha, sal)).encrypt(dados)


def descriptografar(dados: bytes, senha: str) -> bytes:
    from cryptography.fernet import Fernet, InvalidToken

    if not dados.startswith(b"LOJABK1"):
        return dados
    if not senha:
        raise CommandError("Backup criptografado: informe a senha em BACKUP_PASSPHRASE.")
    sal, corpo = dados[7:23], dados[23:]
    try:
        return Fernet(chave_da_senha(senha, sal)).decrypt(corpo)
    except InvalidToken as exc:
        raise CommandError("Senha incorreta ou arquivo de backup corrompido.") from exc


class Command(BaseCommand):
    help = "Gera um backup (dados + arquivos enviados), criptografado se BACKUP_PASSPHRASE estiver definida."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="Diretório onde gravar o backup")

    def handle(self, *args, **opts):
        destino = Path(opts["destino"])
        destino.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        call_command("dumpdata", exclude=EXCLUIR, indent=1, stdout=buf, verbosity=0)
        json.loads(buf.getvalue())  # valida
        pacote = io.BytesIO()
        with tarfile.open(fileobj=pacote, mode="w:gz") as tar:
            dados = buf.getvalue().encode()
            info = tarfile.TarInfo("dados.json")
            info.size = len(dados)
            tar.addfile(info, io.BytesIO(dados))
            media = Path(settings.MEDIA_ROOT)
            if media.exists():
                tar.add(media, arcname="media")
        conteudo = pacote.getvalue()
        senha = os.environ.get("BACKUP_PASSPHRASE", "")
        sufixo = ".tar.gz"
        if senha:
            conteudo, sufixo = criptografar(conteudo, senha), ".tar.gz.enc"
        else:
            self.stdout.write(self.style.WARNING("BACKUP_PASSPHRASE não definida: backup SEM criptografia."))
        arquivo = destino / f"loja-backup-{datetime.now():%Y%m%d-%H%M%S}{sufixo}"
        arquivo.write_bytes(conteudo)
        os.chmod(arquivo, 0o600)
        self.stdout.write(self.style.SUCCESS(f"Backup gravado em {arquivo} ({len(conteudo) // 1024} KB)"))
