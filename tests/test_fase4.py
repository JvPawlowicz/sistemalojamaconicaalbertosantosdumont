from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.sessoes.models import Presenca, Sessao


@pytest.fixture
def agora_sessao(db):
    return Sessao.objects.create(data_hora=timezone.now() + timedelta(minutes=30), grau=2, tipo="ordinaria")


# --- presença por QR ---
def test_qr_registra_presenca_com_janela_e_grau(cliente, usuarios, agora_sessao):
    url = reverse("sessoes:presenca_qr", args=[agora_sessao.token_presenca])
    assert len(agora_sessao.token_presenca) >= 20
    assert Client().get(url).status_code == 302  # anônimo vai ao login
    mestre = cliente("mestre")
    r = mestre.get(url)
    assert r.status_code == 200 and "Confirmar presença" in r.content.decode()
    r = mestre.post(url, follow=True)
    assert "Presença registrada" in r.content.decode()
    p = Presenca.objects.get(sessao=agora_sessao, irmao=usuarios["mestre"])
    assert p.situacao == "presente" and p.origem == "qr" and p.registrada_em and not p.remota
    assert "já está registrada" in mestre.get(url).content.decode()
    # aprendiz não tem grau para sessão de Companheiro
    r = cliente("aprendiz").post(url)
    assert not Presenca.objects.filter(sessao=agora_sessao, irmao=usuarios["aprendiz"], situacao="presente").exists()
    assert "grau" in cliente("aprendiz").get(url).content.decode()
    assert cliente("companheiro").post(url).status_code == 302


def test_qr_fora_da_janela_e_token_invalido(cliente, usuarios):
    cedo = Sessao.objects.create(data_hora=timezone.now() + timedelta(hours=5), grau=1)
    tarde = Sessao.objects.create(data_hora=timezone.now() - timedelta(hours=9), grau=1)
    for s, frase in ((cedo, "O registro abre"), (tarde, "já encerrou")):
        url = reverse("sessoes:presenca_qr", args=[s.token_presenca])
        r = cliente("mestre").post(url)
        assert not Presenca.objects.filter(sessao=s, situacao="presente").exists()
        assert frase in cliente("mestre").get(url).content.decode()
    assert cliente("mestre").get(reverse("sessoes:presenca_qr", args=["token-que-nao-existe"])).status_code == 404


def test_renovar_qr_invalida_o_anterior_e_so_secretaria(cliente, usuarios, agora_sessao):
    antigo = agora_sessao.token_presenca
    assert cliente("mestre").post(reverse("sessoes:renovar_qr", args=[agora_sessao.pk])).status_code == 403
    cliente("secretario").post(reverse("sessoes:renovar_qr", args=[agora_sessao.pk]))
    agora_sessao.refresh_from_db()
    assert agora_sessao.token_presenca != antigo
    assert cliente("mestre").get(reverse("sessoes:presenca_qr", args=[antigo])).status_code == 404
    html = cliente("secretario").get(reverse("sessoes:detalhe", args=[agora_sessao.pk]), {"aba": "presenca"}).content.decode()
    assert "Presença por QR Code" in html and "data:image/png;base64" in html
    assert cliente("secretario").get(reverse("sessoes:qr_tela", args=[agora_sessao.pk])).status_code == 200
    assert cliente("mestre").get(reverse("sessoes:qr_tela", args=[agora_sessao.pk])).status_code == 403


def test_qr_cancelada_nao_registra(cliente, usuarios, agora_sessao):
    Sessao.objects.filter(pk=agora_sessao.pk).update(status="cancelada")
    cliente("mestre").post(reverse("sessoes:presenca_qr", args=[agora_sessao.token_presenca]))
    assert not Presenca.objects.filter(sessao=agora_sessao, situacao="presente").exists()


# --- sessão online ---
def test_sessao_online_gera_sala_e_registra_presenca_remota(cliente, usuarios, settings):
    settings.JITSI_URL = "https://jitsi.exemplo.org"
    s = Sessao.objects.create(data_hora=timezone.now() + timedelta(minutes=10), grau=1, online=True)
    assert s.sala_online.startswith("Loja-") and s.link_online == f"https://jitsi.exemplo.org/{s.sala_online}"
    off = Sessao.objects.create(data_hora=timezone.now(), grau=1)
    assert off.link_online == "" and cliente("mestre").get(reverse("sessoes:entrar_online", args=[off.pk])).status_code == 404
    r = cliente("mestre").post(reverse("sessoes:entrar_online", args=[s.pk]))
    assert r.status_code == 302 and r["Location"] == s.link_online
    p = Presenca.objects.get(sessao=s, irmao=usuarios["mestre"])
    assert p.remota and p.situacao == "presente"
    assert "videoconferência" in cliente("mestre").get(reverse("sessoes:detalhe", args=[s.pk])).content.decode()


# --- carteirinha ---
def test_carteirinha_digital_e_verificacao_publica(cliente, usuarios):
    m = usuarios["mestre"]
    m.refresh_from_db()
    assert len(m.codigo_carteirinha) == 12
    r = cliente("mestre").get(reverse("irmaos:carteirinha"))
    html = r.content.decode()
    assert r.status_code == 200 and "Mestre" in html and m.codigo_carteirinha in html and "data:image/png" in html
    pub = Client().get(reverse("verificar_carteirinha_publica", args=[m.codigo_carteirinha]))
    t = pub.content.decode()
    assert pub.status_code == 200 and "situação regular" in t and m.nome_completo in t
    assert "CPF" not in t and m.email not in t  # não vaza dados pessoais
    m.situacao = "desligado"
    m.save()
    assert "Sem situação regular" in Client().get(reverse("verificar_carteirinha_publica", args=[m.codigo_carteirinha])).content.decode()
    assert Client().get(reverse("verificar_carteirinha_publica", args=["ZZZZZZZZZZZZ"])).status_code == 404
    pdf = cliente("aprendiz").get(reverse("irmaos:carteirinha_pdf"))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert cliente("dev").get(reverse("irmaos:carteirinha")).status_code == 403  # conta técnica sem grau


# --- mural de avisos ---
def test_mural_por_grau_fixado_expiracao_e_email(cliente, usuarios):
    from apps.core.models import Aviso
    sec = cliente("secretario")
    mail.outbox.clear()
    r = sec.post(reverse("core:aviso_novo"), {"titulo": "Sessão magna", "texto": "Traje a rigor", "grau_minimo": 3,
                                              "fixado": "on", "publicar_em": (timezone.localtime() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M"),
                                              "enviar_email": "on"})
    assert r.status_code == 302
    a = Aviso.objects.get()
    assert a.fixado and a.enviado_por_email_em
    destinos = {m.to[0] for m in mail.outbox}
    assert "mestre@x.org" in destinos and "aprendiz@x.org" not in destinos
    assert "Sessão magna" in cliente("mestre").get(reverse("core:avisos")).content.decode()
    assert "Sessão magna" not in cliente("aprendiz").get(reverse("core:avisos")).content.decode()
    assert "Sessão magna" in cliente("mestre").get("/").content.decode()
    Aviso.objects.update(expira_em=timezone.now() - timedelta(hours=1))
    assert "Sessão magna" not in cliente("mestre").get(reverse("core:avisos")).content.decode()
    assert cliente("mestre").post(reverse("core:aviso_novo"), {}).status_code == 403
    sec.post(reverse("core:aviso_excluir", args=[a.pk]))
    assert not Aviso.objects.exists()


# --- diretório de lojas ---
def test_diretorio_de_lojas_preenche_visita(cliente, usuarios):
    from apps.visitas.models import LojaCoirma, VisitaRealizada
    sec = cliente("secretario")
    sec.post(reverse("visitas:loja_nova"), {"nome": "Loja União", "numero": "1234", "oriente": "Campinas", "potencia": "GLESP",
                                            "dia_sessoes": "Quartas, 20h"})
    loja = LojaCoirma.objects.get()
    assert "Loja União" in sec.get(reverse("visitas:lojas")).content.decode()
    r = sec.post(reverse("visitas:nova_realizada"), {"irmao": usuarios["mestre"].pk, "loja": loja.pk, "data": "2026-05-10",
                                                     "grau_sessao": 3})
    assert r.status_code == 302
    v = VisitaRealizada.objects.get()
    assert v.loja_nome == "Loja União" and v.loja_numero == "1234" and v.oriente == "Campinas"
    r = sec.post(reverse("visitas:nova_realizada"), {"irmao": usuarios["mestre"].pk, "data": "2026-05-10"})
    assert r.status_code == 200 and "Escolha uma loja do diretório" in r.content.decode()
    assert cliente("mestre").get(reverse("visitas:lojas")).status_code == 403
