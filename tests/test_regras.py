from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.atas.models import Ata
from apps.core import perfis as P
from apps.core.comunicacao import link_whatsapp
from apps.core.models import AnoMaconico
from apps.core.utils import ano_maconico_de
from apps.relatorios.exportar import _seguro_csv
from apps.sessoes import services as ses
from apps.sessoes.models import Presenca, Sessao
from apps.tesouraria import services as tes
from apps.tesouraria.models import CategoriaFinanceira, Lancamento


def test_ano_maconico_vai_de_julho_a_junho():
    assert ano_maconico_de(date(2026, 7, 1))[2] == "2026/2027"
    assert ano_maconico_de(date(2026, 6, 30))[2] == "2025/2026"
    assert ano_maconico_de(date(2027, 1, 15))[2] == "2026/2027"
    ano = AnoMaconico(nome="2026/2027", inicio=date(2026, 7, 1), fim=date(2027, 6, 30))
    assert [m.month for m in ano.meses] == [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]


def test_perfis_implicitos():
    assert P.ADMINISTRADOR in P.expandir([P.SECRETARIO])
    assert {P.SECRETARIO, P.TESOUREIRO, P.ADMINISTRADOR} <= P.expandir([P.VENERAVEL])
    assert P.TESOUREIRO not in P.expandir([P.SECRETARIO])
    assert P.expandir([P.DESENVOLVEDOR]) >= {P.VENERAVEL, P.TESOUREIRO, P.SECRETARIO, P.ADMINISTRADOR}


def test_grau_igual_ou_superior(usuarios):
    assert usuarios["aprendiz"].pode_ver_grau(1) and not usuarios["aprendiz"].pode_ver_grau(2)
    assert usuarios["companheiro"].pode_ver_grau(2) and not usuarios["companheiro"].pode_ver_grau(3)
    assert usuarios["mestre"].pode_ver_grau(3)
    assert usuarios["dev"].pode_ver_grau(3)


def test_visibilidade_das_atas_por_grau(usuarios):
    atas = {}
    for grau in (1, 2, 3):
        s = Sessao.objects.create(data_hora=timezone.now() - timedelta(days=grau), grau=grau)
        atas[grau] = Ata.objects.create(sessao=s, conteudo=f"ata {grau}", autor=usuarios["secretario"])
    def ids(u): return set(Ata.objects.visiveis_para(usuarios[u]).values_list("pk", flat=True))
    assert ids("aprendiz") == {atas[1].pk}
    assert ids("companheiro") == {atas[1].pk, atas[2].pk}
    assert ids("mestre") == {atas[1].pk, atas[2].pk, atas[3].pk}


def test_escala_usa_titulares_e_presenca_so_de_elegiveis(usuarios, cargos, sessao):
    ses.gerar_escala(sessao)
    assert sessao.escala.count() == 2
    ses.gerar_presencas(sessao)
    assert set(sessao.presencas.values_list("irmao__username", flat=True)) >= {"aprendiz", "mestre"}
    sessao_c = Sessao.objects.create(data_hora=timezone.now(), grau=2)
    ses.gerar_presencas(sessao_c)
    assert not sessao_c.presencas.filter(irmao__username="aprendiz").exists()


def test_frequencia(usuarios, sessao):
    ses.gerar_presencas(sessao)
    p = sessao.presencas.get(irmao=usuarios["mestre"])
    p.situacao = Presenca.Situacao.PRESENTE
    p.save()
    f = ses.frequencia(usuarios["mestre"], sessao.ano)
    assert f["presentes"] == 1 and f["total"] == 1 and f["percentual"] == 100.0


def test_mensalidades_remido_e_baixa(usuarios, categoria):
    from apps.irmaos.models import CategoriaIrmao

    remido = CategoriaIrmao.objects.create(nome="Remido", isento=True)
    usuarios["mestre"].categoria = remido
    usuarios["mestre"].save()
    n = tes.gerar_mensalidades(date(2026, 8, 15))
    assert n >= 5
    assert tes.gerar_mensalidades(date(2026, 8, 20)) == 0  # idempotente
    l_remido = Lancamento.objects.get(irmao=usuarios["mestre"])
    assert l_remido.status == "isento" and l_remido.valor == 0
    l = Lancamento.objects.get(irmao=usuarios["veneravel"])
    assert l.valor == Decimal("100") and l.vencimento == date(2026, 8, 10)
    tes.dar_baixa(l, usuarios["tesoureiro"], date(2026, 8, 12), Decimal("100"), "pix")
    assert tes.saldo_caixa() == Decimal("100")
    tes.estornar_baixa(l)
    assert tes.saldo_caixa() == Decimal("0")


def test_vencidos_atualizados(usuarios, categoria):
    tes.gerar_mensalidades(date(2020, 1, 1))
    assert Lancamento.objects.filter(status="vencido").exists()


def test_orcamento_vs_realizado(usuarios):
    ano = AnoMaconico.atual()
    cat = CategoriaFinanceira.objects.create(nome="Aluguel", tipo="despesa")
    from apps.tesouraria.models import MovimentoCaixa, Orcamento

    Orcamento.objects.create(ano=ano, categoria=cat, valor_previsto=Decimal("500"))
    MovimentoCaixa.objects.create(tipo="despesa", categoria=cat, valor=Decimal("600"), data=timezone.localdate(),
                                  descricao="x", criado_por=usuarios["tesoureiro"])
    linha = [l for l in tes.orcamento_vs_realizado(ano) if l["categoria"] == cat][0]
    assert linha["diferenca"] == Decimal("100")


def test_link_whatsapp():
    url = link_whatsapp("(11) 91234-5678", "Olá irmão")
    assert url == "https://wa.me/5511912345678?text=Ol%C3%A1%20irm%C3%A3o"
    assert link_whatsapp("", "x") == ""


def test_csv_nao_injeta_formula():
    assert _seguro_csv("=1+1").startswith("'")
    assert _seguro_csv("-12,50") == "-12,50"
    assert _seguro_csv("Ana") == "Ana"
