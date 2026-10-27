import io
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.atas.models import Ata
from apps.core.models import Loja
from apps.sessoes import services as ses
from apps.sessoes.models import Presenca, Sessao
from tests.test_fluxos import PNG, _assinar, _fluxo_ata


def _png(cor="red"):
    b = io.BytesIO()
    Image.new("RGB", (8, 8), cor).save(b, "PNG")
    return b.getvalue()


# --- fotos e brasão (rotas protegidas) ---
def test_foto_e_brasao_servidos_por_rota_protegida(cliente, usuarios):
    from django.test import Client
    m = usuarios["mestre"]
    m.foto = SimpleUploadedFile("f.png", _png(), content_type="image/png")
    m.save()
    url = reverse("core:foto_irmao", args=[m.pk])
    r = cliente("aprendiz").get(url)
    assert r.status_code == 200 and r["Content-Type"] == "image/png" and "max-age" in r["Cache-Control"]
    assert Client().get(url).status_code == 302  # anônimo não vê foto
    loja = Loja.atual()
    loja.brasao = SimpleUploadedFile("b.png", _png("blue"), content_type="image/png")
    loja.save()
    assert Client().get(reverse("core:brasao")).status_code == 200  # institucional (tela de login)
    html = cliente("mestre").get(reverse("irmaos:lista")).content.decode()
    assert url in html and "/media/" not in html


def test_upload_de_foto_rejeita_formato_invalido(cliente, usuarios):
    base = {"nome_completo": "Mestre", "email": "m@x.org", "username": "mestre", "grau": 3, "situacao": "ativo",
            "is_active": "on", "familiares-TOTAL_FORMS": 0, "familiares-INITIAL_FORMS": 0,
            "familiares-MIN_NUM_FORMS": 0, "familiares-MAX_NUM_FORMS": 1000}
    r = cliente("secretario").post(reverse("irmaos:editar", args=[usuarios["mestre"].pk]),
                                   {**base, "foto": SimpleUploadedFile("x.svg", b"<svg onload=alert(1)/>", content_type="image/svg+xml")})
    assert r.status_code == 200 and not usuarios["mestre"].__class__.objects.get(pk=usuarios["mestre"].pk).foto


# --- avisos de assinatura ---
def test_aprovar_avisa_signatarios_e_lembrete_nao_repete(cliente, usuarios, sessao, cargos):
    mail.outbox.clear()
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    avisos = [m for m in mail.outbox if "aguardando a sua assinatura" in m.subject]
    assert len(avisos) == 2 and reverse("atas:assinar", args=[ata.pk]) in avisos[0].body
    assert "Texto da ata" not in avisos[0].body  # conteúdo nunca vai por e-mail
    # lembrete só depois de 2 dias da aprovação e a cada 3 dias
    Ata.objects.filter(pk=ata.pk).update(aprovada_em=timezone.now() - timedelta(days=3))
    ata.signatarios.update(ultimo_aviso_em=None)
    mail.outbox.clear()
    call_command("enviar_lembretes", verbosity=0)
    assert len([m for m in mail.outbox if m.subject.startswith("Lembrete: Ata")]) == 2
    n = len(mail.outbox)
    call_command("enviar_lembretes", verbosity=0)
    assert len(mail.outbox) == n


def test_email_tem_versao_html_com_identidade_da_loja(usuarios):
    from apps.core.comunicacao import enviar_email
    mail.outbox.clear()
    enviar_email("a@x.org", "Assunto", "Olá\nAcesse https://exemplo.org/x", contexto="t")
    html = mail.outbox[0].alternatives[0][0]
    assert Loja.atual().nome in html and 'href="https://exemplo.org/x"' in html and mail.outbox[0].body.startswith("Olá")


# --- regras do regimento ---
def _sessoes_realizadas(n, usuarios, ausente):
    sessoes = []
    for k in range(n):
        s = Sessao.objects.create(data_hora=timezone.now() - timedelta(days=30 - k), grau=1, status="realizada")
        ses.gerar_presencas(s)
        for p in s.presencas.all():
            p.situacao = Presenca.Situacao.AUSENTE if p.irmao == ausente else Presenca.Situacao.PRESENTE
            p.save()
        sessoes.append(s)
    return sessoes


def test_alerta_de_faltas_consecutivas_e_frequencia(usuarios):
    from apps.core.models import AnoMaconico
    from apps.core.regimento import alertas_de_frequencia, faltas_consecutivas
    loja = Loja.atual()
    loja.limite_faltas_consecutivas = 3
    loja.frequencia_minima_percentual = 70
    loja.save()
    _sessoes_realizadas(4, usuarios, usuarios["aprendiz"])
    ano = AnoMaconico.atual()
    assert faltas_consecutivas(usuarios["aprendiz"], ano) == 4
    alertas = dict((i.username, m) for i, m in alertas_de_frequencia(ano))
    assert "4 faltas consecutivas" in alertas["aprendiz"] and "frequência de 0.0%" in alertas["aprendiz"].replace(",", ".")
    assert "mestre" not in alertas


def test_falta_justificada_zera_a_sequencia(usuarios):
    from apps.core.models import AnoMaconico
    from apps.core.regimento import faltas_consecutivas
    ss = _sessoes_realizadas(3, usuarios, usuarios["aprendiz"])
    p = ss[1].presencas.get(irmao=usuarios["aprendiz"])
    p.situacao = Presenca.Situacao.JUSTIFICADA
    p.save()
    assert faltas_consecutivas(usuarios["aprendiz"], AnoMaconico.atual()) == 1


def test_regras_desligadas_nao_geram_alerta(usuarios):
    from apps.core.regimento import alertas_de_frequencia
    _sessoes_realizadas(5, usuarios, usuarios["aprendiz"])
    assert alertas_de_frequencia() == []


def test_quorum_avisa_ao_concluir(cliente, usuarios, sessao):
    Sessao.objects.filter(pk=sessao.pk).update(status="agendada")
    loja = Loja.atual()
    loja.quorum_minimo = 5
    loja.save()
    r = cliente("secretario").post(reverse("sessoes:concluir", args=[sessao.pk]), follow=True)
    assert "quórum não atingido" in r.content.decode()
    html = cliente("secretario").get(reverse("sessoes:detalhe", args=[sessao.pk]), {"aba": "presenca"}).content.decode()
    assert "Quórum: 0 presente(s) / mínimo 5" in html


def test_multa_e_juros_do_regimento(usuarios, categoria):
    from apps.tesouraria import services as tes
    from apps.tesouraria.models import Lancamento
    loja = Loja.atual()
    loja.multa_atraso_percentual = Decimal("2")
    loja.juros_mensal_percentual = Decimal("1")
    loja.dias_carencia_atraso = 5
    loja.save()
    l = Lancamento.objects.create(irmao=usuarios["mestre"], competencia=date(2026, 1, 1), valor=Decimal("100"),
                                  vencimento=date(2026, 1, 10), status="vencido")
    assert tes.valor_atualizado(l, date(2026, 1, 14))["total"] == Decimal("100")  # dentro da carência
    v = tes.valor_atualizado(l, date(2026, 2, 9))  # 30 dias - 5 de carência = 25 dias
    assert v["multa"] == Decimal("2.00") and v["juros"] == Decimal("0.83") and v["total"] == Decimal("102.83")
    l.status = "pago"
    assert tes.valor_atualizado(l, date(2026, 6, 1))["total"] == Decimal("100")
    assert "valor atualizado" in tes.mensagem_cobranca(Lancamento(irmao=usuarios["mestre"], competencia=date(2020, 1, 1),
                                                                   valor=Decimal("100"), vencimento=date(2020, 1, 10), status="vencido"))


# --- versões de ata ---
def test_versoes_da_ata_arquivadas_e_comparaveis(cliente, usuarios, sessao, cargos):
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    _assinar(cliente, "veneravel", ata)
    sec = cliente("secretario")
    sec.post(reverse("atas:nova_versao", args=[ata.pk]))
    sec.post(reverse("atas:editar", args=[ata.pk]), {"numero": 1, "livro": "1", "folha": "1", "conteudo": "Texto da ata CORRIGIDO"})
    ata.refresh_from_db()
    assert ata.versao == 2 and ata.versoes.filter(versao=1).exists()
    html = sec.get(reverse("atas:versoes", args=[ata.pk]), {"a": 1, "b": 2}).content.decode()
    assert "dif-del" in html and "dif-ins" in html and "CORRIGIDO" in html
    # assinatura da v1 continua verificável contra o texto arquivado
    from apps.atas.models import AssinaturaAta
    from django.test import Client
    cod = AssinaturaAta.objects.get(versao=1, irmao=usuarios["veneravel"]).codigo
    pub = Client().get(reverse("verificar", args=[cod])).content.decode()
    assert "versão anterior" in pub and "confere com o hash assinado" in pub
    assert cliente("aprendiz").get(reverse("atas:versoes", args=[ata.pk])).status_code in (200, 404)


# --- pacote do conselho fiscal ---
def test_pacote_do_conselho_fiscal(cliente, usuarios):
    from apps.tesouraria.models import CategoriaFinanceira, MovimentoCaixa
    cat = CategoriaFinanceira.objects.create(nome="Aluguel", tipo="despesa")
    MovimentoCaixa.objects.create(tipo="despesa", categoria=cat, valor=Decimal("300"), data=timezone.localdate(),
                                  descricao="Aluguel do templo", criado_por=usuarios["tesoureiro"])
    r = cliente("tesoureiro").get(reverse("relatorios:pacote_fiscal"))
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and "prestacao-de-contas" in r["Content-Disposition"]
    assert cliente("mestre").get(reverse("relatorios:pacote_fiscal")).status_code == 403
    assert b"Pacote do Conselho Fiscal" in cliente("tesoureiro").get(reverse("relatorios:indice")).content


# --- edição/exclusão e cancelamento ---
def test_cancelar_sessao_com_aviso_e_regras(cliente, usuarios, sessao, db):
    futura = Sessao.objects.create(data_hora=timezone.now() + timedelta(days=3), grau=1)
    mail.outbox.clear()
    cliente("secretario").post(reverse("sessoes:cancelar", args=[futura.pk]), {"avisar": "on", "motivo": "Feriado"})
    futura.refresh_from_db()
    assert futura.status == "cancelada" and any("CANCELADA" in m.body and "Feriado" in m.body for m in mail.outbox)
    cliente("secretario").post(reverse("sessoes:cancelar", args=[sessao.pk]))
    sessao.refresh_from_db()
    assert sessao.status == "realizada"  # realizada não cancela
    assert cliente("aprendiz").post(reverse("sessoes:cancelar", args=[futura.pk])).status_code == 403


def test_editar_excluir_expediente_evento_candidato_patrimonio(cliente, usuarios):
    from apps.candidatos.models import Candidato
    from apps.expediente.models import Correspondencia
    from apps.patrimonio.models import Emprestimo, ItemPatrimonio
    from apps.sessoes.models import Evento
    sec = cliente("secretario")
    c = Correspondencia.objects.create(tipo="recebida", data=date.today(), assunto="Ofício", origem_destino="X",
                                       registrada_por=usuarios["secretario"])
    r = sec.post(reverse("expediente:editar", args=[c.pk]), {"tipo": "recebida", "data": "2026-01-02", "assunto": "Ofício 2",
                                                             "origem_destino": "Y", "grau_minimo": 3, "leva_a_sessao": "on"})
    c.refresh_from_db()
    assert c.assunto == "Ofício 2"
    sec.post(reverse("expediente:excluir", args=[c.pk]))
    assert not Correspondencia.objects.exists()
    e = Evento.objects.create(titulo="Ágape", data_hora=timezone.now() + timedelta(days=2), criado_por=usuarios["secretario"])
    sec.post(reverse("sessoes:evento_excluir", args=[e.pk]))
    assert not Evento.objects.exists()
    cand = Candidato.objects.create(nome="Ini", proposto_por=usuarios["mestre"], data_proposta=date.today(), etapa="iniciado")
    sec.post(reverse("candidatos:excluir", args=[cand.pk]))
    assert Candidato.objects.filter(pk=cand.pk).exists()  # iniciado não exclui
    cand2 = Candidato.objects.create(nome="Novo", proposto_por=usuarios["mestre"], data_proposta=date.today())
    sec.post(reverse("candidatos:editar", args=[cand2.pk]), {"nome": "Novo Editado", "proposto_por": usuarios["mestre"].pk,
                                                             "data_proposta": "2026-02-02"})
    cand2.refresh_from_db()
    assert cand2.nome == "Novo Editado"
    sec.post(reverse("candidatos:excluir", args=[cand2.pk]))
    assert not Candidato.objects.filter(pk=cand2.pk).exists()
    item = ItemPatrimonio.objects.create(nome="Livro", emprestavel=True)
    Emprestimo.objects.create(item=item, irmao=usuarios["mestre"], emprestado_em=date.today())
    sec.post(reverse("patrimonio:excluir", args=[item.pk]))
    assert ItemPatrimonio.objects.filter(pk=item.pk).exists()  # emprestado não exclui
    assert cliente("aprendiz").post(reverse("expediente:excluir", args=[1])).status_code == 403


# --- pré-autorização de certificados ---
def test_preautorizacao_aplica_assinatura_aos_certificados_gerados_depois(cliente, usuarios, sessao, cargos):
    from apps.core.assinatura import assinatura_integra
    from apps.visitas.models import AssinaturaCertificado, AutorizacaoAssinaturaLote, CertificadoVisita, Visitante
    vis = Visitante.objects.create(nome="Visitante", grau=3, loja_nome="Loja X", email="v@x.org")
    sec, ven = cliente("secretario"), cliente("veneravel")
    sec.post(reverse("visitas:sessao", args=[sessao.pk]), {"existente": vis.pk})
    # assina ANTES de gerar os certificados
    assert ven.post(reverse("visitas:preautorizar", args=[sessao.pk]), {"funcao": "veneravel", "assinatura_png": PNG}).status_code == 302
    sec.post(reverse("visitas:preautorizar", args=[sessao.pk]), {"funcao": "secretario", "assinatura_png": PNG})
    assert AutorizacaoAssinaturaLote.objects.count() == 2
    sec.post(reverse("visitas:gerar_certificados", args=[sessao.pk]))
    cert = CertificadoVisita.objects.get()
    assert cert.status == "assinado" and cert.assinaturas.count() == 2
    a = cert.assinaturas.first()
    assert a.autorizacao_id and a.hash_documento == cert.hash_documento and assinatura_integra(a)
    assert "pré-autorização" in a.texto_legal
    pdf = sec.get(reverse("visitas:certificado_pdf", args=[cert.pk]))
    assert pdf.content.startswith(b"%PDF")
    from django.test import Client
    assert "pré-autorizada" in Client().get(reverse("verificar", args=[cert.codigo])).content.decode()
    mail.outbox.clear()
    sec.post(reverse("visitas:enviar_lote", args=[sessao.pk]))
    assert len(mail.outbox) == 1


def test_preautorizacao_expira_apos_7_dias(usuarios, sessao, cargos):
    from apps.visitas import services as vs
    from apps.visitas.models import AutorizacaoAssinaturaLote, CertificadoVisita, VisitaRecebida, Visitante
    from apps.core.assinatura import preparar_assinatura
    from apps.core.utils import sha256_texto
    ev = {"irmao": usuarios["veneravel"], "imagem": PNG, "foto": None, "ip": "1.1.1.1", "user_agent": "", "latitude": None,
          "longitude": None, "precisao_m": None, "autenticacao_2fa": False, "aceite": None, "texto_legal": "x",
          "assinado_em": timezone.now()}
    preparar_assinatura(AutorizacaoAssinaturaLote, sha256_texto("x"), ev, sessao=sessao, funcao="veneravel").save()
    vis = Visitante.objects.create(nome="V", grau=3, loja_nome="L")
    vr = VisitaRecebida.objects.create(sessao=sessao, visitante=vis, registrada_por=usuarios["secretario"])
    CertificadoVisita.objects.create(visita=vr, codigo="ABC")
    Sessao.objects.filter(pk=sessao.pk).update(data_hora=timezone.now() - timedelta(days=9))
    sessao.refresh_from_db()
    assert vs.aplicar_autorizacoes(sessao) == 0


# --- backup e restauração ---
@pytest.mark.django_db(transaction=True)
def test_backup_criptografado_e_restauracao(tmp_path, monkeypatch, settings):
    from apps.irmaos.models import Irmao
    from apps.core.models import TermoAceite
    settings.MEDIA_ROOT = str(tmp_path / "media")
    (tmp_path / "media" / "documentos").mkdir(parents=True)
    (tmp_path / "media" / "documentos" / "a.pdf").write_bytes(b"%PDF-1.4 conteudo")
    TermoAceite.objects.create(versao=1)
    i = Irmao.objects.create(username="bk", nome_completo="Backup Teste", grau=3, email="b@x.org", perfis=["secretario"])
    i.set_password("senha-de-teste-123")
    i.save()
    monkeypatch.setenv("BACKUP_PASSPHRASE", "segredo-forte")
    call_command("backup_dados", str(tmp_path / "bk"), verbosity=0)
    arq = next((tmp_path / "bk").iterdir())
    assert arq.name.endswith(".enc") and b"Backup Teste" not in arq.read_bytes()  # criptografado
    # destrói os dados e os arquivos
    Irmao.objects.all().delete()
    TermoAceite.objects.all().delete()
    (tmp_path / "media" / "documentos" / "a.pdf").unlink()
    with pytest.raises(Exception):
        call_command("restaurar_dados", str(arq), verbosity=0)  # exige --confirmar
    monkeypatch.setenv("BACKUP_PASSPHRASE", "senha-errada")
    with pytest.raises(Exception):
        call_command("restaurar_dados", str(arq), "--confirmar", verbosity=0)
    monkeypatch.setenv("BACKUP_PASSPHRASE", "segredo-forte")
    call_command("restaurar_dados", str(arq), "--confirmar", verbosity=0)
    r = Irmao.objects.get(username="bk")
    assert r.nome_completo == "Backup Teste" and r.check_password("senha-de-teste-123") and r.perfis == ["secretario"]
    assert (tmp_path / "media" / "documentos" / "a.pdf").read_bytes() == b"%PDF-1.4 conteudo"
    assert TermoAceite.objects.count() == 1


# --- 2FA de ponta a ponta ---
def test_2fa_cadastro_verificacao_e_codigo_de_recuperacao(usuarios, settings):
    from django.test import Client
    from django_otp.oath import TOTP
    from django_otp.plugins.otp_static.models import StaticToken
    from django_otp.plugins.otp_totp.models import TOTPDevice
    settings.EXIGIR_2FA = True
    c = Client()
    c.login(username="tesoureiro", password="senha-de-teste-123")
    assert c.get(reverse("tesouraria:painel")).status_code == 302
    r = c.get(reverse("core:2fa_configurar"))
    assert r.status_code == 200 and b"data:image/png;base64" in r.content
    dev = TOTPDevice.objects.get(user=usuarios["tesoureiro"], confirmed=False)
    def codigo(avanco=0):
        # o django-otp recusa reutilizar um código já aceito (anti-replay): o 2º login usa a janela seguinte
        t = TOTP(dev.bin_key, dev.step, dev.t0, dev.digits)
        t.time = __import__("time").time() + avanco
        return str(t.token()).zfill(dev.digits)
    assert b"inv" in c.post(reverse("core:2fa_configurar"), {"token": "000000"}).content.lower()  # inválido
    r = c.post(reverse("core:2fa_configurar"), {"token": codigo()})
    assert r.status_code == 200 and b"2FA ativado" in r.content
    assert c.get(reverse("tesouraria:painel")).status_code == 200  # já verificado nesta sessão
    # novo login: precisa verificar
    c2 = Client()
    c2.login(username="tesoureiro", password="senha-de-teste-123")
    r = c2.get(reverse("tesouraria:painel"))
    assert r.status_code == 302 and r["Location"].startswith(reverse("core:2fa_verificar"))
    assert c2.post(reverse("core:2fa_verificar"), {"token": "123456"}).status_code == 200  # erra
    assert c2.post(reverse("core:2fa_verificar"), {"token": codigo()}).status_code == 200  # replay do mesmo código é recusado
    assert c2.post(reverse("core:2fa_verificar"), {"token": codigo(30)}).status_code == 302
    assert c2.get(reverse("tesouraria:painel")).status_code == 200
    # código de recuperação funciona uma vez
    rec = StaticToken.objects.filter(device__user=usuarios["tesoureiro"]).first().token
    c3 = Client()
    c3.login(username="tesoureiro", password="senha-de-teste-123")
    assert c3.post(reverse("core:2fa_verificar"), {"token": rec}).status_code == 302
    c4 = Client()
    c4.login(username="tesoureiro", password="senha-de-teste-123")
    assert c4.post(reverse("core:2fa_verificar"), {"token": rec}).status_code == 200  # já usado


# --- integrações: testes de configuração ---
def test_botoes_de_teste_de_email_e_whatsapp(cliente, usuarios):
    mail.outbox.clear()
    r = cliente("secretario").post(reverse("core:testar_email"), follow=True)
    assert "E-mail de teste enviado" in r.content.decode() and mail.outbox[-1].to == ["secretario@x.org"]
    r = cliente("secretario").post(reverse("core:testar_whatsapp"), follow=True)
    assert "não configurada" in r.content.decode()
    assert cliente("mestre").post(reverse("core:testar_email")).status_code == 403


def test_paginacao_das_listas(cliente, usuarios):
    from apps.core.models import EmailLog
    EmailLog.objects.bulk_create([EmailLog(destinatario="a@x.org", assunto=f"A{i}") for i in range(120)])
    c = cliente("secretario")
    p1 = c.get(reverse("core:emails")).content.decode()
    assert "Página 1 de 3" in p1
    p3 = c.get(reverse("core:emails"), {"pagina": 3}).content.decode()
    assert "Página 3 de 3" in p3 and "pagina=2" in p3
    assert c.get(reverse("core:emails"), {"pagina": "lixo"}).status_code == 200


@pytest.mark.django_db(transaction=True)
def test_assinaturas_continuam_integras_apos_backup_e_restauracao(tmp_path, monkeypatch, settings, cliente, usuarios, cargos):
    """Regressão: o backup (JSON) trunca microssegundos; o hash usa carimbo canônico (UTC, segundos)."""
    from apps.atas.models import AssinaturaAta
    from apps.core.assinatura import assinatura_integra
    s = Sessao.objects.create(data_hora=timezone.now().replace(microsecond=123456) - timedelta(days=1), grau=1,
                              status="realizada")
    ses.gerar_escala(s)
    ata = _fluxo_ata(cliente, usuarios, s, cargos)
    _assinar(cliente, "veneravel", ata)
    _assinar(cliente, "secretario", ata)
    antes = {a.codigo: a.hash_assinatura for a in AssinaturaAta.objects.all()}
    hash_ata = Ata.objects.get().hash_conteudo
    settings.MEDIA_ROOT = str(tmp_path / "media")
    monkeypatch.setenv("BACKUP_PASSPHRASE", "x")
    call_command("backup_dados", str(tmp_path / "bk"), verbosity=0)
    call_command("restaurar_dados", str(next((tmp_path / "bk").iterdir())), "--confirmar", verbosity=0)
    depois = AssinaturaAta.objects.all()
    assert {a.codigo: a.hash_assinatura for a in depois} == antes
    assert all(assinatura_integra(a) for a in depois) and len(depois) == 2
    assert Ata.objects.get().hash_conteudo == hash_ata
