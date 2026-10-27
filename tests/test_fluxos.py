import base64
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.atas.models import Ata, AssinaturaAta
from apps.core.assinatura import assinatura_integra
from apps.sessoes import services as ses

PNG = "data:image/png;base64," + base64.b64encode(
    (lambda b: (Image.new("RGB", (4, 4), "black").save(b, "PNG"), b.getvalue())[1])(io.BytesIO())
).decode()


def _fluxo_ata(cliente, usuarios, sessao, cargos):
    ses.gerar_escala(sessao)
    sec = cliente("secretario")
    r = sec.post(reverse("atas:criar", args=[sessao.pk]), {"numero": 1, "livro": "1", "folha": "1", "conteudo": "Texto da ata"})
    assert r.status_code == 302
    ata = Ata.objects.get(sessao=sessao)
    sec.post(reverse("atas:circular", args=[ata.pk]), {"por_email": "on"})
    ata.refresh_from_db()
    assert ata.status == "circulacao"
    ids = [usuarios["veneravel"].pk, usuarios["secretario"].pk]
    sec.post(reverse("atas:aprovar", args=[ata.pk]), {"signatarios": ids})
    ata.refresh_from_db()
    assert ata.status == "aprovada"
    return ata


def _assinar(cliente, nome, ata):
    c = cliente(nome)
    return c.post(reverse("atas:assinar", args=[ata.pk]),
                  {"assinatura_png": PNG, "latitude": "-23.550520", "longitude": "-46.633308", "precisao": "20"},
                  REMOTE_ADDR="203.0.113.7")


def test_fluxo_completo_de_assinatura_da_ata(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    hash1 = ata.hash_conteudo
    assert _assinar(cliente, "veneravel", ata).status_code == 302
    ata.refresh_from_db()
    assert ata.status == "aprovada"  # falta o secretário
    assert _assinar(cliente, "secretario", ata).status_code == 302
    ata.refresh_from_db()
    assert ata.status == "assinada"
    ass = AssinaturaAta.objects.get(ata=ata, irmao=usuarios["veneravel"])
    assert ass.hash_documento == hash1 and ass.ip == "203.0.113.7" and str(ass.latitude) == "-23.550520"
    assert ass.texto_legal and assinatura_integra(ass)
    # adulteração do registro é detectada
    ass.ip = "198.51.100.1"
    assert not assinatura_integra(ass)
    # assinar duas vezes não duplica
    _assinar(cliente, "veneravel", ata)
    assert AssinaturaAta.objects.filter(ata=ata, irmao=usuarios["veneravel"]).count() == 1


def test_ata_aprovada_nao_pode_ser_editada_e_nova_versao_invalida_assinaturas(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    _assinar(cliente, "veneravel", ata)
    sec = cliente("secretario")
    r = sec.post(reverse("atas:editar", args=[ata.pk]), {"numero": 1, "conteudo": "ALTERADO"})
    ata.refresh_from_db()
    assert ata.conteudo == "Texto da ata"  # edição bloqueada
    sec.post(reverse("atas:nova_versao", args=[ata.pk]))
    ata.refresh_from_db()
    assert ata.versao == 2 and ata.status == "rascunho" and ata.assinaturas_validas.count() == 0
    assert AssinaturaAta.objects.filter(ata=ata, versao=1).count() == 1  # histórico preservado


def test_assinatura_exige_signatario_e_imagem(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    r = cliente("mestre").post(reverse("atas:assinar", args=[ata.pk]), {"assinatura_png": PNG})
    assert r.status_code == 403  # não é signatário
    r = cliente("veneravel").post(reverse("atas:assinar", args=[ata.pk]), {})
    assert r.status_code == 200 and AssinaturaAta.objects.count() == 0
    r = cliente("veneravel").post(reverse("atas:assinar", args=[ata.pk]), {"assinatura_png": "data:text/html;base64,AAAA"})
    assert AssinaturaAta.objects.count() == 0


def test_assinar_com_foto_opcional(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, "PNG")
    foto = SimpleUploadedFile("ass.png", buf.getvalue(), content_type="image/png")
    r = cliente("veneravel").post(reverse("atas:assinar", args=[ata.pk]), {"foto_assinatura": foto})
    assert r.status_code == 302
    assert AssinaturaAta.objects.get(irmao=usuarios["veneravel"]).imagem_src.startswith("data:image/png;base64,")


def test_pdf_e_verificacao_publica(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    _assinar(cliente, "veneravel", ata)
    _assinar(cliente, "secretario", ata)
    r = cliente("mestre").get(reverse("atas:pdf", args=[ata.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")
    from django.test import Client

    cod = AssinaturaAta.objects.first().codigo
    anon = Client().get(reverse("verificar", args=[cod]))
    assert anon.status_code == 200 and b"Assinatura" in anon.content and "Texto da ata".encode() not in anon.content
    assert Client().get(reverse("verificar", args=["NAOEXISTE"])).status_code == 404


def test_ata_de_grau_superior_nao_abre_para_aprendiz(cliente, usuarios, cargos):
    from datetime import timedelta
    from django.utils import timezone
    from apps.sessoes.models import Sessao

    s = Sessao.objects.create(data_hora=timezone.now() - timedelta(days=2), grau=3, status="realizada")
    ata = Ata.objects.create(sessao=s, conteudo="segredo de mestre", autor=usuarios["secretario"])
    assert cliente("aprendiz").get(reverse("atas:detalhe", args=[ata.pk])).status_code == 404
    assert cliente("companheiro").get(reverse("atas:pdf", args=[ata.pk])).status_code == 404
    assert cliente("mestre").get(reverse("atas:detalhe", args=[ata.pk])).status_code == 200


def test_api_de_modelos_com_variaveis(cliente, usuarios, sessao, cargos):
    from apps.atas.models import ModeloTexto

    ses.gerar_escala(sessao)
    ModeloTexto.objects.create(titulo="Abertura", atalho="abertura", texto="Presidida por {{veneravel}} em {{data}}.")
    r = cliente("secretario").get(reverse("atas:modelos_buscar"), {"sessao": sessao.pk, "q": "abert"})
    itens = r.json()["itens"]
    assert itens and "Veneravel" in itens[0]["texto"] and "{{" not in itens[0]["texto"]
    assert cliente("aprendiz").get(reverse("atas:modelos_buscar"), {"sessao": sessao.pk}).status_code == 403


def test_certificado_de_visita_em_lote(cliente, usuarios, sessao, cargos):
    from django.core import mail
    from apps.visitas.models import CertificadoVisita, Visitante

    vis = Visitante.objects.create(nome="Visitante Teste", grau=3, loja_nome="Loja X", email="v@x.org")
    sec = cliente("secretario")
    sec.post(reverse("visitas:sessao", args=[sessao.pk]), {"existente": vis.pk})
    sec.post(reverse("visitas:gerar_certificados", args=[sessao.pk]))
    cert = CertificadoVisita.objects.get()
    # secretário e venerável assinam em lote
    r = sec.post(reverse("visitas:assinar_lote", args=[sessao.pk]), {"funcao": "secretario", "assinatura_png": PNG})
    assert r.status_code == 302
    cert.refresh_from_db()
    assert cert.status == "parcial"
    mail.outbox.clear()
    sec.post(reverse("visitas:enviar_lote", args=[sessao.pk]))
    assert not mail.outbox  # ainda sem as duas assinaturas
    cliente("veneravel").post(reverse("visitas:assinar_lote", args=[sessao.pk]), {"funcao": "veneravel", "assinatura_png": PNG})
    cert.refresh_from_db()
    assert cert.status == "assinado"
    sec.post(reverse("visitas:enviar_lote", args=[sessao.pk]))
    cert.refresh_from_db()
    assert cert.status == "enviado" and len(mail.outbox) == 1
    assert mail.outbox[0].attachments[0][0].startswith("certificado-") and mail.outbox[0].attachments[0][1][:4] == b"%PDF"
    assert cliente("aprendiz").get(reverse("visitas:certificado_pdf", args=[cert.pk])).status_code == 403
    from django.test import Client
    assert Client().get(reverse("verificar", args=[cert.codigo])).status_code == 200


def test_documentos_por_grau(cliente, usuarios):
    from apps.documentos.models import Documento

    d = Documento.objects.create(titulo="Prancha de Mestre", grau_minimo=3, enviado_por=usuarios["secretario"],
                                 arquivo=SimpleUploadedFile("p.pdf", b"%PDF-1.4 teste", content_type="application/pdf"))
    assert cliente("aprendiz").get(reverse("documentos:ver", args=[d.pk])).status_code == 403
    assert cliente("aprendiz").get(reverse("documentos:arquivo", args=[d.pk])).status_code == 403
    r = cliente("mestre").get(reverse("documentos:arquivo", args=[d.pk]))
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r["X-Content-Type-Options"] == "nosniff"
    assert b"<iframe" in cliente("mestre").get(reverse("documentos:ver", args=[d.pk])).content
    assert d.titulo not in cliente("aprendiz").get(reverse("documentos:lista")).content.decode()


def test_upload_rejeita_formato_perigoso(cliente, usuarios):
    r = cliente("secretario").post(reverse("documentos:enviar"), {
        "titulo": "x", "categoria": "outro", "grau_minimo": 1,
        "arquivo": SimpleUploadedFile("evil.html", b"<script>alert(1)</script>", content_type="text/html")})
    assert r.status_code == 200 and b"Formato n" in r.content


def test_permissoes_por_perfil(cliente, usuarios):
    permitido = {
        "tesouraria:painel": {"tesoureiro", "veneravel", "dev"},
        "irmaos:criar": {"secretario", "veneravel", "dev"},
        "core:configuracoes": {"secretario", "veneravel", "dev"},
        "candidatos:painel": {"mestre", "veneravel", "secretario", "tesoureiro", "dev"},
        "patrimonio:lista": {"secretario", "veneravel", "dev"},
    }
    for rota, quem in permitido.items():
        for nome in ("aprendiz", "companheiro", "mestre", "secretario", "tesoureiro", "veneravel", "dev"):
            r = cliente(nome).get(reverse(rota))
            esperado = 200 if nome in quem else 403
            assert r.status_code == esperado, (rota, nome, r.status_code)


def test_dados_de_saude_so_para_o_proprio_e_secretaria(cliente, usuarios):
    usuarios["mestre"].plano_saude = "UnimedSecreto"
    usuarios["mestre"].save()
    url = reverse("irmaos:detalhe", args=[usuarios["mestre"].pk])
    assert b"UnimedSecreto" not in cliente("aprendiz").get(url).content
    assert b"UnimedSecreto" in cliente("mestre").get(url).content
    assert b"UnimedSecreto" in cliente("secretario").get(url).content
    assert b"UnimedSecreto" not in cliente("tesoureiro").get(url).content


def test_navegacao_geral_sem_erros(cliente, usuarios, sessao, cargos):
    from apps.tesouraria import services as tes
    from datetime import date
    tes.gerar_mensalidades(date.today())
    for nome in ("veneravel", "mestre", "aprendiz"):
        c = cliente(nome)
        for rota in ("core:painel", "irmaos:lista", "cargos:quadro", "sessoes:lista", "atas:lista", "visitas:realizadas",
                     "documentos:lista", "tesouraria:minhas", "relatorios:indice", "irmaos:meu_perfil", "core:privacidade"):
            assert c.get(reverse(rota)).status_code == 200, (nome, rota)
    v = cliente("veneravel")
    for rota in ("tesouraria:mensalidades", "tesouraria:caixa", "tesouraria:orcamento", "tesouraria:categorias",
                 "expediente:lista", "comissoes:lista", "candidatos:painel", "patrimonio:lista", "atas:modelos",
                 "visitas:visitantes", "cargos:catalogo", "irmaos:categorias", "core:aceites", "core:emails",
                 "sessoes:frequencia"):
        assert v.get(reverse(rota)).status_code == 200, rota
    for rota, args in (("sessoes:detalhe", [sessao.pk]), ("sessoes:escala", [sessao.pk]), ("sessoes:presenca", [sessao.pk]),
                       ("sessoes:convocacao_pdf", [sessao.pk]), ("visitas:sessao", [sessao.pk]),
                       ("irmaos:detalhe", [usuarios["mestre"].pk]), ("irmaos:editar", [usuarios["mestre"].pk]),
                       ("tesouraria:extrato_pdf", [usuarios["mestre"].pk])):
        assert v.get(reverse(rota, args=args)).status_code == 200, rota


def test_todos_os_relatorios_e_formatos(cliente, usuarios, sessao, cargos):
    from apps.relatorios.relatorios import RELATORIOS
    v = cliente("dev")
    for slug in RELATORIOS:
        for fmt, ctype in (("", "text/html"), ("csv", "text/csv"), ("xlsx", "spreadsheetml"), ("pdf", "application/pdf")):
            r = v.get(reverse("relatorios:ver", args=[slug]), {"formato": fmt} if fmt else {})
            assert r.status_code == 200, (slug, fmt)
            assert ctype in r["Content-Type"], (slug, fmt, r["Content-Type"])
    assert cliente("aprendiz").get(reverse("relatorios:ver", args=["frequencia"])).status_code == 403


def test_termo_obrigatorio_no_primeiro_acesso(termo, db):
    from apps.irmaos.models import Irmao
    from django.test import Client
    i = Irmao.objects.create(username="novo", nome_completo="Novo", grau=1, email="n@x.org")
    i.set_password("senha-de-teste-123")
    i.save()
    c = Client()
    c.login(username="novo", password="senha-de-teste-123")
    r = c.get(reverse("irmaos:lista"))
    assert r.status_code == 302 and r["Location"] == reverse("core:aceite_termo")
    c.post(reverse("core:aceite_termo"), {"aceito": "on"})
    assert c.get(reverse("irmaos:lista")).status_code == 200
    ace = i.aceites.get()
    assert ace.hash_termo == termo.hash


def test_2fa_exigido_para_perfil_administrativo(usuarios, settings):
    from django.test import Client
    settings.EXIGIR_2FA = True
    c = Client()
    c.login(username="tesoureiro", password="senha-de-teste-123")
    r = c.get(reverse("tesouraria:painel"))
    assert r.status_code == 302 and r["Location"] == reverse("core:2fa_configurar")
    c2 = Client()
    c2.login(username="mestre", password="senha-de-teste-123")  # sem perfil administrativo
    assert c2.get(reverse("irmaos:lista")).status_code == 200


def test_login_logout_e_anonimo_redirecionado(usuarios):
    from django.test import Client
    r = Client().get(reverse("irmaos:lista"))
    assert r.status_code == 302 and r["Location"].startswith(reverse("login"))
    c = Client()
    r = c.post(reverse("login"), {"username": "mestre", "password": "senha-de-teste-123"})
    assert r.status_code == 302
    assert c.post(reverse("logout")).status_code == 302
    assert c.get(reverse("irmaos:lista")).status_code == 302


def test_secretario_nao_concede_nem_remove_perfil_desenvolvedor(cliente, usuarios):
    from apps.irmaos.models import Irmao
    sec = cliente("secretario")
    url = reverse("irmaos:editar", args=[usuarios["mestre"].pk])
    base = {"nome_completo": "Mestre", "email": "m@x.org", "username": "mestre", "grau": 3, "situacao": "ativo",
            "is_active": "on", "categoria": usuarios["mestre"].categoria_id, "familiares-TOTAL_FORMS": 0,
            "familiares-INITIAL_FORMS": 0, "familiares-MIN_NUM_FORMS": 0, "familiares-MAX_NUM_FORMS": 1000}
    r = sec.post(url, {**base, "perfis": ["desenvolvedor"]})
    assert r.status_code == 200  # opção inválida para quem não é desenvolvedor
    usuarios["mestre"].refresh_from_db()
    assert "desenvolvedor" not in usuarios["mestre"].perfis and not usuarios["mestre"].is_superuser
    # editar um desenvolvedor sem ser um não o rebaixa
    dev = usuarios["dev"]
    dev.is_superuser = True
    dev.save()
    r = sec.post(reverse("irmaos:editar", args=[dev.pk]), {**base, "nome_completo": "Dev", "username": "dev", "perfis": []})
    dev.refresh_from_db()
    assert dev.is_superuser and "desenvolvedor" in dev.perfis


def test_ip_nao_aceita_xff_falsificado_sem_proxy(rf, settings):
    from apps.core.utils import ip_do_cliente
    settings.PROXY_COUNT = 0
    req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6", REMOTE_ADDR="10.0.0.5")
    assert ip_do_cliente(req) == "10.0.0.5"
    settings.PROXY_COUNT = 1
    req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9", REMOTE_ADDR="10.0.0.5")
    assert ip_do_cliente(req) == "203.0.113.9"
