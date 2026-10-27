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

from apps.candidatos.models import Candidato
from apps.core.models import Loja
from apps.irmaos.models import Irmao
from apps.sessoes import services as ses
from apps.sessoes.models import Cerimonia, ConfirmacaoEvento, Evento, Sessao


@pytest.fixture
def sessao_futura(db):
    return Sessao.objects.create(data_hora=timezone.now() + timedelta(hours=30), grau=1, tipo="ordinaria")


def test_promocao_e_elevacao_atualizam_grau_e_datas(usuarios, sessao):
    apr = usuarios["aprendiz"]
    ses.registrar_cerimonia(sessao, apr, "promocao", usuarios["veneravel"])
    apr.refresh_from_db()
    assert apr.grau == 2 and apr.data_promocao == sessao.data_hora.date()
    with pytest.raises(ses.CerimoniaInvalida):  # repetir não pode
        ses.registrar_cerimonia(sessao, apr, "promocao", usuarios["veneravel"])
    ses.registrar_cerimonia(sessao, apr, "elevacao", usuarios["veneravel"])
    apr.refresh_from_db()
    assert apr.grau == 3 and apr.data_elevacao
    with pytest.raises(ses.CerimoniaInvalida):  # mestre não é promovido
        ses.registrar_cerimonia(sessao, usuarios["mestre"], "promocao", usuarios["veneravel"])


def test_intersticio_minimo_e_dispensa(usuarios, sessao):
    loja = Loja.atual()
    loja.intersticio_promocao_meses = 6
    loja.save()
    apr = usuarios["aprendiz"]
    apr.data_iniciacao = sessao.data_hora.date() - timedelta(days=30)
    apr.save()
    with pytest.raises(ses.CerimoniaInvalida) as e:
        ses.registrar_cerimonia(sessao, apr, "promocao", usuarios["veneravel"])
    assert "Interstício" in str(e.value)
    c = ses.registrar_cerimonia(sessao, apr, "promocao", usuarios["veneravel"], forcar=True)
    assert c.forcada


def test_apenas_veneravel_pode_dispensar_intersticio(cliente, usuarios, sessao):
    loja = Loja.atual()
    loja.intersticio_promocao_meses = 12
    loja.save()
    apr = usuarios["aprendiz"]
    apr.data_iniciacao = sessao.data_hora.date() - timedelta(days=10)
    apr.save()
    url = reverse("sessoes:cerimonias", args=[sessao.pk])
    cliente("secretario").post(url, {"tipo": "promocao", "irmao": apr.pk, "forcar": "on"})
    apr.refresh_from_db()
    assert apr.grau == 1  # secretário não dispensa
    cliente("veneravel").post(url, {"tipo": "promocao", "irmao": apr.pk, "forcar": "on"})
    apr.refresh_from_db()
    assert apr.grau == 2


def test_iniciar_candidato_aprovado(cliente, usuarios, sessao, categoria):
    cand = Candidato.objects.create(nome="João Candidato", email="cand@x.org", proposto_por=usuarios["mestre"],
                                    data_proposta=date.today(), etapa="proposto")
    sec = cliente("secretario")
    r = sec.post(reverse("candidatos:iniciar", args=[cand.pk]), {"sessao": sessao.pk})
    assert Irmao.objects.filter(email="cand@x.org").count() == 0  # ainda não aprovado
    sec.post(reverse("candidatos:mover", args=[cand.pk]), {"etapa": "aprovado"})
    r = sec.post(reverse("candidatos:iniciar", args=[cand.pk]), {"sessao": sessao.pk})
    novo = Irmao.objects.get(email="cand@x.org")
    assert novo.grau == 1 and novo.data_iniciacao == sessao.data_hora.date() and not novo.has_usable_password()
    cand.refresh_from_db()
    assert cand.etapa == "iniciado" and Cerimonia.objects.filter(irmao=novo, tipo="iniciacao").exists()


def test_importacao_valida_e_importa(cliente, usuarios, categoria):
    csv_ok = ("nome_completo;email;grau;situacao;categoria;data_iniciacao\n"
              "Ana Teste;ana@x.org;Mestre;ativo;Integral;10/05/2005\n"
              "Beto Teste;beto@x.org;Aprendiz;ativo;;01/02/2024\n").encode()
    sec = cliente("secretario")
    url = reverse("irmaos:importar")
    r = sec.post(url, {"planilha": SimpleUploadedFile("q.csv", csv_ok), "acao": "validar"})
    assert r.status_code == 200 and not Irmao.objects.filter(email="ana@x.org").exists()
    sec.post(url, {"planilha": SimpleUploadedFile("q.csv", csv_ok), "acao": "importar"})
    ana = Irmao.objects.get(email="ana@x.org")
    assert ana.grau == 3 and ana.data_iniciacao == date(2005, 5, 10) and ana.categoria == categoria
    # reimportar atualiza, não duplica
    sec.post(url, {"planilha": SimpleUploadedFile("q.csv", csv_ok), "acao": "importar"})
    assert Irmao.objects.filter(email="ana@x.org").count() == 1


def test_importacao_com_erro_nao_grava_nada(cliente, usuarios):
    ruim = ("nome_completo;email;grau\nOk Irmão;ok@x.org;Mestre\nSem Grau;sg@x.org;Rei\n").encode()
    r = cliente("secretario").post(reverse("irmaos:importar"), {"planilha": SimpleUploadedFile("q.csv", ruim), "acao": "importar"})
    assert b"grau deve ser" in r.content
    assert not Irmao.objects.filter(email="ok@x.org").exists()
    assert cliente("aprendiz").get(reverse("irmaos:importar")).status_code == 403


def test_importacao_xlsx(cliente, usuarios):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["nome_completo", "email", "grau", "data_nascimento"])
    ws.append(["Xis Lsx", "xlsx@x.org", "Companheiro", date(1980, 1, 2)])
    buf = io.BytesIO()
    wb.save(buf)
    cliente("secretario").post(reverse("irmaos:importar"), {"planilha": SimpleUploadedFile("q.xlsx", buf.getvalue()), "acao": "importar"})
    i = Irmao.objects.get(email="xlsx@x.org")
    assert i.grau == 2 and i.data_nascimento == date(1980, 1, 2)


def test_eventos_confirmacao_e_visibilidade(cliente, usuarios):
    e = Evento.objects.create(titulo="Ágape de Mestres", data_hora=timezone.now() + timedelta(days=5), grau_minimo=3,
                              criado_por=usuarios["secretario"])
    assert cliente("aprendiz").get(reverse("sessoes:evento", args=[e.pk])).status_code == 403
    m = cliente("mestre")
    m.post(reverse("sessoes:evento", args=[e.pk]), {"resposta": "sim", "acompanhantes": "2"})
    assert e.total_confirmados == 3
    m.post(reverse("sessoes:evento", args=[e.pk]), {"resposta": "nao", "acompanhantes": "0"})
    assert ConfirmacaoEvento.objects.filter(evento=e).count() == 1 and e.total_confirmados == 0
    assert cliente("aprendiz").get(reverse("sessoes:eventos")).status_code == 200


def test_agenda_e_ics(cliente, usuarios, sessao_futura):
    r = cliente("mestre").get(reverse("sessoes:agenda"))
    assert r.status_code == 200
    ics = cliente("mestre").get(reverse("sessoes:agenda_ics"))
    assert ics["Content-Type"].startswith("text/calendar") and b"BEGIN:VEVENT" in ics.content
    Sessao.objects.create(data_hora=timezone.now() + timedelta(days=9), grau=3)
    ics_ap = cliente("aprendiz").get(reverse("sessoes:agenda_ics")).content
    assert ics_ap.count(b"BEGIN:VEVENT") == 1  # sessão de Mestre não aparece para Aprendiz


def test_lgpd_exportacao_e_solicitacao(cliente, usuarios):
    c = cliente("mestre")
    r = c.get(reverse("core:exportar_meus_dados"))
    dados = json.loads(r.content)
    assert dados["dados_cadastrais"]["username"] == "mestre" and "aceites_do_termo" in dados
    c.post(reverse("core:meus_dados"), {"tipo": "correcao", "mensagem": "Corrigir telefone"})
    sec = cliente("secretario")
    from apps.core.models import SolicitacaoLGPD
    s = SolicitacaoLGPD.objects.get()
    sec.post(reverse("core:solicitacoes_lgpd"), {"id": s.pk, "status": "atendida", "resposta": "Feito"})
    s.refresh_from_db()
    assert s.status == "atendida" and s.resolvida_em
    assert cliente("aprendiz").get(reverse("core:solicitacoes_lgpd")).status_code == 403


def test_lembrete_de_sessao_enviado_uma_unica_vez(usuarios, sessao_futura):
    mail.outbox.clear()
    call_command("enviar_lembretes", verbosity=0)
    n = len(mail.outbox)
    assert n >= 5 and "Lembrete" in mail.outbox[0].subject
    call_command("enviar_lembretes", verbosity=0)
    assert len(mail.outbox) == n


def test_cobranca_automatica_semanal(usuarios, categoria):
    from apps.tesouraria import services as tes
    loja = Loja.atual()
    loja.cobranca_automatica = True
    loja.save()
    tes.gerar_mensalidades(date(2020, 1, 1))
    mail.outbox.clear()
    call_command("enviar_lembretes", verbosity=0)
    n = len(mail.outbox)
    assert n >= 5
    call_command("enviar_lembretes", verbosity=0)
    assert len(mail.outbox) == n  # não repete dentro de 7 dias


def test_lancamento_avulso(cliente, usuarios):
    t = cliente("tesoureiro")
    r = t.post(reverse("tesouraria:avulso"), {"irmao": usuarios["mestre"].pk, "descricao": "Joia", "competencia": "2026-08-15",
                                              "valor": "250,00", "vencimento": "2026-08-30"})
    assert r.status_code == 302
    from apps.tesouraria.models import Lancamento
    l = Lancamento.objects.get(descricao="Joia")
    assert l.valor == Decimal("250.00") and l.competencia == date(2026, 8, 1) and l.status == "pendente"
    assert cliente("aprendiz").get(reverse("tesouraria:avulso")).status_code == 403


def test_resetar_2fa_e_desativar_acesso(cliente, usuarios):
    from django_otp.plugins.otp_totp.models import TOTPDevice
    TOTPDevice.objects.create(user=usuarios["tesoureiro"], name="x", confirmed=True)
    sec = cliente("secretario")
    sec.post(reverse("irmaos:resetar_2fa", args=[usuarios["tesoureiro"].pk]))
    assert not TOTPDevice.objects.filter(user=usuarios["tesoureiro"]).exists()
    sec.post(reverse("irmaos:alternar_acesso", args=[usuarios["aprendiz"].pk]))
    usuarios["aprendiz"].refresh_from_db()
    assert not usuarios["aprendiz"].is_active
    assert cliente("tesoureiro").post(reverse("irmaos:resetar_2fa", args=[usuarios["mestre"].pk])).status_code == 403
    # secretário não mexe no 2FA do desenvolvedor
    assert sec.post(reverse("irmaos:resetar_2fa", args=[usuarios["dev"].pk])).status_code == 403


def test_painel_com_indicadores_e_paginas_de_erro(cliente, usuarios):
    r = cliente("veneravel").get(reverse("core:painel"))
    assert r.status_code == 200 and b"Irm\xc3\xa3os ativos" in r.content
    assert b"Irm\xc3\xa3os ativos" not in cliente("mestre").get(reverse("core:painel")).content
    r = cliente("mestre").get("/pagina-que-nao-existe/")
    assert r.status_code == 404 and b"n\xc3\xa3o encontrada" in r.content
    r = cliente("aprendiz").get(reverse("tesouraria:painel"))
    assert r.status_code == 403 and b"Acesso negado" in r.content


def test_expediente_vai_para_sessao_e_e_marcado_como_lido(cliente, usuarios, sessao_futura):
    from apps.expediente.models import Correspondencia
    c = Correspondencia.objects.create(tipo="recebida", data=date.today(), assunto="Ofício da GLESP", origem_destino="GLESP",
                                       registrada_por=usuarios["secretario"], grau_minimo=1)
    r = cliente("secretario").get(reverse("sessoes:detalhe", args=[sessao_futura.pk]))
    assert b"Of\xc3\xadcio da GLESP" in r.content
    cliente("secretario").post(reverse("sessoes:concluir", args=[sessao_futura.pk]))
    c.refresh_from_db()
    assert c.lida_em_sessao_id == sessao_futura.pk


def test_livro_de_atas_pdf(cliente, usuarios, sessao, cargos):
    from tests.test_fluxos import _assinar, _fluxo_ata
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)
    _assinar(cliente, "veneravel", ata)
    _assinar(cliente, "secretario", ata)
    r = cliente("secretario").get(reverse("atas:livro_pdf"))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert cliente("mestre").get(reverse("atas:livro_pdf")).status_code == 403
