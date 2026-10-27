"""Integrações externas exercitadas contra servidores locais reais (SMTP e Evolution API simulados)."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from apps.core import comunicacao


class _Evolution(BaseHTTPRequestHandler):
    chamadas = []
    estado = "open"

    def log_message(self, *a):
        pass

    def _responder(self, corpo, status=200):
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        type(self).chamadas.append(("GET", self.path, self.headers.get("apikey"), None))
        if self.headers.get("apikey") != "chave-secreta":
            return self._responder({"error": "unauthorized"}, 401)
        self._responder({"instance": {"instanceName": "loja", "state": type(self).estado}})

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).chamadas.append(("POST", self.path, self.headers.get("apikey"), corpo))
        if self.headers.get("apikey") != "chave-secreta":
            return self._responder({"error": "unauthorized"}, 401)
        self._responder({"key": {"id": "ABC"}}, 201)


@pytest.fixture
def evolution(settings):
    _Evolution.chamadas = []
    _Evolution.estado = "open"
    srv = HTTPServer(("127.0.0.1", 0), _Evolution)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    settings.EVOLUTION_API_URL = f"http://127.0.0.1:{srv.server_port}"
    settings.EVOLUTION_API_KEY = "chave-secreta"
    settings.EVOLUTION_INSTANCE = "loja"
    yield _Evolution
    srv.shutdown()


def test_whatsapp_envia_documento_no_formato_da_evolution(evolution):
    pdf = base64.b64encode(b"%PDF-1.4 x").decode()
    ok, erro = comunicacao.enviar_whatsapp_documento("(11) 91234-5678", "Certificado de visita", "c.pdf", pdf)
    assert ok and not erro
    metodo, caminho, chave, corpo = evolution.chamadas[-1]
    assert metodo == "POST" and caminho == "/message/sendMedia/loja" and chave == "chave-secreta"
    assert corpo["number"] == "5511912345678" and corpo["mediatype"] == "document" and corpo["fileName"] == "c.pdf"
    assert corpo["mimetype"] == "application/pdf" and corpo["media"] == pdf


def test_whatsapp_status_conectado_e_desconectado(evolution):
    ok, texto = comunicacao.whatsapp_status()
    assert ok and "open" in texto
    evolution.estado = "close"
    ok, texto = comunicacao.whatsapp_status()
    assert not ok and "QR Code" in texto


def test_whatsapp_erros_de_configuracao_e_autenticacao(evolution, settings):
    settings.EVOLUTION_API_KEY = "errada"
    ok, erro = comunicacao.enviar_whatsapp_documento("11912345678", "x", "c.pdf", "AAAA")
    assert not ok and "401" in erro
    ok, texto = comunicacao.whatsapp_status()
    assert not ok and "Falha" in texto
    ok, erro = comunicacao.enviar_whatsapp_documento("", "x", "c.pdf", "AAAA")
    assert not ok and "Telefone" in erro
    settings.EVOLUTION_API_URL = ""
    assert comunicacao.enviar_whatsapp_documento("11912345678", "x", "c.pdf", "AAAA") == (False, "Evolution API não configurada")


def test_lote_de_certificados_por_whatsapp_com_servidor_real(evolution, cliente, usuarios, sessao, cargos):
    from django.urls import reverse
    from apps.visitas.models import CertificadoVisita, Visitante
    from tests.conftest import SENHA  # noqa: F401
    from tests.test_fluxos import PNG
    vis = Visitante.objects.create(nome="Zé Visitante", grau=3, loja_nome="Loja X", whatsapp="(11) 98888-7777")
    sec = cliente("secretario")
    sec.post(reverse("visitas:sessao", args=[sessao.pk]), {"existente": vis.pk})
    sec.post(reverse("visitas:gerar_certificados", args=[sessao.pk]))
    sec.post(reverse("visitas:assinar_lote", args=[sessao.pk]), {"funcao": "secretario", "assinatura_png": PNG})
    cliente("veneravel").post(reverse("visitas:assinar_lote", args=[sessao.pk]), {"funcao": "veneravel", "assinatura_png": PNG})
    sec.post(reverse("visitas:enviar_lote", args=[sessao.pk]), {"whatsapp": "on"})
    cert = CertificadoVisita.objects.get()
    assert cert.status == "enviado" and "whatsapp ok" in cert.envio_obs
    corpo = evolution.chamadas[-1][3]
    assert corpo["number"] == "5511988887777" and base64.b64decode(corpo["media"]).startswith(b"%PDF")


def test_smtp_real_com_servidor_local(settings, usuarios):
    """Envia por um servidor SMTP de verdade (aiosmtpd) e confere cabeçalhos, HTML e anexo."""
    pytest.importorskip("aiosmtpd")
    from aiosmtpd.controller import Controller
    from email import message_from_bytes

    recebidos = []

    class Handler:
        async def handle_DATA(self, server, session, envelope):
            recebidos.append(message_from_bytes(envelope.content))
            return "250 OK"

    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        porta = sock.getsockname()[1]
    ctl = Controller(Handler(), hostname="127.0.0.1", port=porta)
    ctl.start()
    try:
        settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        settings.EMAIL_HOST, settings.EMAIL_PORT = "127.0.0.1", porta
        settings.EMAIL_USE_TLS = False
        ok = comunicacao.enviar_email("dest@x.org", "Convocação — teste", "Olá, Irmão.\nVeja https://exemplo.org",
                                      anexos=[("c.pdf", b"%PDF-1.4 x", "application/pdf")], contexto="teste")
    finally:
        ctl.stop()
    assert ok and len(recebidos) == 1
    msg = recebidos[0]
    tipos = [p.get_content_type() for p in msg.walk()]
    assert "text/plain" in tipos and "text/html" in tipos and "application/pdf" in tipos
    assert msg["To"] == "dest@x.org" and "Convoca" in str(__import__("email.header", fromlist=["x"]).make_header(
        __import__("email.header", fromlist=["x"]).decode_header(msg["Subject"])))


def test_smtp_indisponivel_registra_falha_sem_quebrar(settings, usuarios):
    from apps.core.models import EmailLog
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_USE_TLS = "127.0.0.1", 1, False
    assert comunicacao.enviar_email("x@x.org", "Falha", "corpo") is False
    log = EmailLog.objects.first()
    assert not log.enviado and log.erro
