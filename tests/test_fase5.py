from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.candidatos.models import Candidato
from apps.core import perfis as P
from apps.sessoes import services as ses
from apps.sessoes.models import Presenca, Sessao
from apps.votacoes.models import Participacao, Votacao, Voto


def _abrir(cliente, v):
    cliente("secretario").post(reverse("votacoes:abrir", args=[v.pk]))
    v.refresh_from_db()


def _votacao(usuarios, **kw):
    dados = dict(titulo="Escrutínio", tipo="geral", grau_minimo=3, exigir_presenca=False, criada_por=usuarios["secretario"])
    dados.update(kw)
    return Votacao.objects.create(**dados)


# --- votação sigilosa ---
def test_voto_nao_guarda_usuario_nem_horario():
    campos = {f.name for f in Voto._meta.get_fields()}
    assert campos == {"id", "votacao", "opcao"}  # nada que identifique quem votou ou quando
    assert {f.name for f in Participacao._meta.get_fields()} == {"id", "votacao", "irmao"}  # quem votou, nunca como


def test_fluxo_de_votacao_resultado_so_apos_encerrar(cliente, usuarios):
    v = _votacao(usuarios)
    assert cliente("mestre").get(reverse("votacoes:detalhe", args=[v.pk])).status_code == 403  # rascunho: só a gestão
    _abrir(cliente, v)
    assert v.status == "aberta"
    for nome, opcao in (("mestre", "sim"), ("veneravel", "sim"), ("tesoureiro", "nao")):
        r = cliente(nome).post(reverse("votacoes:votar", args=[v.pk]), {"opcao": opcao}, follow=True)
        assert "registrado em sigilo" in r.content.decode()
    # não vota duas vezes, nem aprendiz (grau), nem opção inválida
    assert "já votou" in cliente("mestre").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "nao"}, follow=True).content.decode()
    assert Voto.objects.filter(votacao=v).count() == 3
    cliente("aprendiz").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "sim"})
    cliente("secretario").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "lixo"})
    assert Voto.objects.filter(votacao=v).count() == 3
    # durante a votação, nenhuma tela revela totais
    html = cliente("secretario").get(reverse("votacoes:detalhe", args=[v.pk])).content.decode()
    assert "Resultado" not in html and "Favoráveis" not in html and "Participação: 3" in html
    assert "Mestre" in html  # lista de quem votou (sem o voto)
    cliente("secretario").post(reverse("votacoes:encerrar", args=[v.pk]))
    html = cliente("mestre").get(reverse("votacoes:detalhe", args=[v.pk])).content.decode()
    assert "Resultado" in html and "Favoráveis · 2" in html and "Contrários · 1" in html and "Aprovado" in html
    # encerrada: ninguém mais vota
    assert Voto.objects.filter(votacao=v).count() == 3
    cliente("companheiro").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "sim"})
    assert Voto.objects.filter(votacao=v).count() == 3


def test_escrutinio_unanimidade_e_aplicacao_ao_candidato(cliente, usuarios):
    cand = Candidato.objects.create(nome="Candidato X", proposto_por=usuarios["mestre"], data_proposta=date.today(), etapa="escrutinio")
    v = _votacao(usuarios, tipo="escrutinio", candidato=cand, negativos_maximos=0)
    _abrir(cliente, v)
    cliente("mestre").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "sim"})
    cliente("veneravel").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "nao"})  # uma bola preta rejeita
    cliente("secretario").post(reverse("votacoes:encerrar", args=[v.pk]))
    assert not v.apuracao()["aprovada"]
    cliente("secretario").post(reverse("votacoes:aplicar", args=[v.pk]))
    cand.refresh_from_db(); v.refresh_from_db()
    assert cand.etapa == "reprovado" and v.resultado_aplicado
    cliente("secretario").post(reverse("votacoes:aplicar", args=[v.pk]))  # não aplica duas vezes
    # com tolerância de 1 voto contrário o mesmo resultado aprova
    cand2 = Candidato.objects.create(nome="Y", proposto_por=usuarios["mestre"], data_proposta=date.today(), etapa="escrutinio")
    v2 = _votacao(usuarios, tipo="escrutinio", candidato=cand2, negativos_maximos=1)
    _abrir(cliente, v2)
    cliente("mestre").post(reverse("votacoes:votar", args=[v2.pk]), {"opcao": "sim"})
    cliente("veneravel").post(reverse("votacoes:votar", args=[v2.pk]), {"opcao": "nao"})
    cliente("secretario").post(reverse("votacoes:encerrar", args=[v2.pk]))
    cliente("secretario").post(reverse("votacoes:aplicar", args=[v2.pk]))
    cand2.refresh_from_db()
    assert cand2.etapa == "aprovado"


def test_so_vota_quem_esta_presente_na_sessao(cliente, usuarios, sessao, cargos):
    ses.gerar_presencas(sessao)
    Presenca.objects.filter(sessao=sessao, irmao=usuarios["mestre"]).update(situacao="presente")
    v = _votacao(usuarios, sessao=sessao, exigir_presenca=True, grau_minimo=1)
    _abrir(cliente, v)
    assert "presença registrada" in cliente("veneravel").get(reverse("votacoes:detalhe", args=[v.pk])).content.decode()
    cliente("veneravel").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "sim"})
    assert Voto.objects.filter(votacao=v).count() == 0
    cliente("mestre").post(reverse("votacoes:votar", args=[v.pk]), {"opcao": "sim"})
    assert Voto.objects.filter(votacao=v).count() == 1
    assert v.eleitores().count() == 1


def test_votacao_aberta_aparece_como_pendencia_e_so_gestao_cria(cliente, usuarios):
    from apps.core.pendencias import tarefas_do_usuario
    v = _votacao(usuarios, titulo="Aprovar o balancete")
    _abrir(cliente, v)
    assert any("Votação aberta: Aprovar o balancete" in t["texto"] for t in tarefas_do_usuario(usuarios["mestre"]))
    assert not any("Votação aberta" in t["texto"] for t in tarefas_do_usuario(usuarios["aprendiz"]))
    assert cliente("mestre").get(reverse("votacoes:criar")).status_code == 403
    assert cliente("mestre").post(reverse("votacoes:abrir", args=[v.pk])).status_code == 403


# --- hospitalaria e Tronco ---
@pytest.fixture
def hospitaleiro(usuarios):
    from tests.conftest import _irmao
    return _irmao("hospitaleiro", 3, [P.HOSPITALEIRO])


def test_perfil_hospitaleiro_e_implicito_no_veneravel(usuarios, hospitaleiro):
    assert P.HOSPITALEIRO in P.expandir([P.VENERAVEL]) and P.HOSPITALEIRO not in P.expandir([P.SECRETARIO])
    assert hospitaleiro.tem_perfil(P.HOSPITALEIRO) and P.HOSPITALEIRO in P.ADMINISTRATIVOS  # exige 2FA


def test_hospitalaria_e_sigilosa(cliente, usuarios, hospitaleiro):
    from apps.core.models import AceiteTermo, TermoAceite
    AceiteTermo.objects.create(irmao=hospitaleiro, termo=TermoAceite.vigente(), hash_termo="x")
    from django.test import Client
    h = Client()
    assert h.login(username="hospitaleiro", password="senha-de-teste-123")
    r = h.post(reverse("hospitalaria:caso_novo"), {"irmao": usuarios["mestre"].pk, "tipo": "saude", "descricao": "Internado no hospital X",
                                                   "data_inicio": "2026-10-01", "responsavel": hospitaleiro.pk})
    assert r.status_code == 302
    from apps.hospitalaria.models import CasoHospitalaria
    c = CasoHospitalaria.objects.get()
    assert c.nome == "Mestre"
    for nome in ("secretario", "tesoureiro", "mestre", "aprendiz"):
        assert cliente(nome).get(reverse("hospitalaria:painel")).status_code == 403, nome
        assert cliente(nome).get(reverse("hospitalaria:caso", args=[c.pk])).status_code == 403, nome
    assert cliente("veneravel").get(reverse("hospitalaria:caso", args=[c.pk])).status_code == 200
    assert b"Internado no hospital X" not in cliente("mestre").get(reverse("irmaos:detalhe", args=[usuarios["mestre"].pk])).content
    # acompanhamento, atraso e encerramento
    h.post(reverse("hospitalaria:caso", args=[c.pk]), {"data": "2026-10-05", "tipo": "visita", "descricao": "Visita realizada"})
    assert c.acompanhamentos.count() == 1 and c.ultimo_contato == date(2026, 10, 5)
    assert "atrasado" in h.get(reverse("hospitalaria:painel")).content.decode()  # último contato há mais de 15 dias
    h.post(reverse("hospitalaria:caso_status", args=[c.pk]))
    c.refresh_from_db()
    assert c.status == "encerrado" and c.encerrado_em


def test_tronco_saldo_sessao_e_permissoes(cliente, usuarios, hospitaleiro, sessao):
    from apps.hospitalaria.models import MovimentoTronco
    from django.test import Client
    from apps.core.models import AceiteTermo, TermoAceite
    AceiteTermo.objects.create(irmao=hospitaleiro, termo=TermoAceite.vigente(), hash_termo="x")
    h = Client()
    h.login(username="hospitaleiro", password="senha-de-teste-123")
    h.post(reverse("hospitalaria:tronco_rapido", args=[sessao.pk]), {"valor": "152,50"})
    h.post(reverse("hospitalaria:tronco"), {"tipo": "destinacao", "valor": "50,00", "data": "2026-10-20", "descricao": "Cesta básica"})
    h.post(reverse("hospitalaria:tronco"), {"tipo": "arrecadacao", "valor": "-5", "data": "2026-10-20"})  # inválido
    assert MovimentoTronco.objects.count() == 2 and MovimentoTronco.saldo() == Decimal("102.50")
    assert MovimentoTronco.objects.get(tipo="arrecadacao").sessao == sessao
    html = h.get(reverse("hospitalaria:tronco")).content.decode()
    assert "R$ 102,50" in html and "Cesta básica" in html
    # tesoureiro lê, mas não lança; aprendiz não vê
    t = cliente("tesoureiro")
    assert t.get(reverse("hospitalaria:tronco")).status_code == 200 and "Novo movimento" not in t.get(reverse("hospitalaria:tronco")).content.decode()
    assert t.post(reverse("hospitalaria:tronco"), {"tipo": "arrecadacao", "valor": "1", "data": "2026-10-20"}).status_code == 403
    assert cliente("aprendiz").get(reverse("hospitalaria:tronco")).status_code == 403
    assert cliente("secretario").post(reverse("hospitalaria:tronco_rapido", args=[sessao.pk]), {"valor": "1"}).status_code == 403
    # a aba Resumo da sessão mostra o atalho só para quem pode
    assert "Tronco de Beneficência" in h.get(reverse("sessoes:detalhe", args=[sessao.pk])).content.decode()


def test_abas_hospitalaria_so_para_quem_pode(usuarios, hospitaleiro):
    from apps.core import navegacao as nav

    def abas(u):
        return [i.url_name for s in nav.secoes_visiveis(u) for i in nav.itens_visiveis(s, u)]

    assert "hospitalaria:painel" in abas(hospitaleiro) and "hospitalaria:tronco" in abas(hospitaleiro)
    assert "hospitalaria:tronco" in abas(usuarios["tesoureiro"]) and "hospitalaria:painel" not in abas(usuarios["tesoureiro"])
    assert "hospitalaria:painel" not in abas(usuarios["secretario"]) and "hospitalaria:tronco" not in abas(usuarios["aprendiz"])
