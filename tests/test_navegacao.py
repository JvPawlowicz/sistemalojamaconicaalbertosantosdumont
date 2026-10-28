"""Arquitetura de informação: menu enxuto, abas, central de pendências, busca rápida e área de trabalho da sessão."""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core import navegacao as nav
from apps.sessoes.models import Sessao


def _secoes(usuarios, nome):
    return [s.chave for s in nav.secoes_visiveis(usuarios[nome])]


def test_menu_enxuto_por_perfil(usuarios):
    assert _secoes(usuarios, "aprendiz") == ["inicio", "agenda", "atas", "irmaos", "acervo", "financeiro"]
    assert "relatorios" not in _secoes(usuarios, "mestre") and "admin" not in _secoes(usuarios, "mestre")
    assert _secoes(usuarios, "tesoureiro")[-1] == "relatorios"
    assert _secoes(usuarios, "veneravel") == ["inicio", "agenda", "atas", "irmaos", "acervo", "financeiro", "relatorios", "admin"]
    assert len(_secoes(usuarios, "veneravel")) <= 8  # antes: 22 itens no menu


def test_toda_url_nomeada_pertence_a_uma_secao_ou_a_conta():
    """Garante que nenhuma tela 'solta' fique sem aba/menu ativo (exceto conta, sistema e autenticação)."""
    from django.urls import get_resolver

    livres = {"core:aceite_termo", "core:privacidade", "core:2fa_configurar", "core:2fa_verificar", "core:meus_dados",
              "core:exportar_meus_dados", "core:busca", "core:brasao", "core:identidade", "core:foto_irmao", "core:manifest", "core:service_worker", "core:offline", "core:ajuda", "core:saude", "core:testar_email", "core:testar_whatsapp", "irmaos:carteirinha", "irmaos:carteirinha_pdf", "sessoes:presenca_qr", "sessoes:qr_tela", "sessoes:renovar_qr", "sessoes:entrar_online", "irmaos:meu_perfil", "irmaos:modelo_importacao", "irmaos:convidar",
              "irmaos:resetar_2fa", "irmaos:alternar_acesso"}
    nomes = []
    for ns, (_, resolver) in get_resolver().namespace_dict.items():
        if ns in ("admin",):
            continue
        for nome in resolver.reverse_dict.keys():
            if isinstance(nome, str):
                nomes.append(f"{ns}:{nome}")
    sem = [n for n in nomes if nav.secao_da_view(n) is None and n not in livres]
    assert not sem, sem


def test_abas_aparecem_na_pagina_certa(cliente, usuarios):
    html = cliente("veneravel").get(reverse("irmaos:lista")).content.decode()
    for rotulo in ("Quadro", "Cargos e gestão", "Candidatos", "Comissões", "Visitação"):
        assert f">{rotulo}</a>" in html
    # categorias de irmão ficam em Financeiro, não em Irmãos
    fin = cliente("tesoureiro").get(reverse("irmaos:categorias")).content.decode()
    assert ">Mensalidades</a>" in fin and ">Categorias de irmão</a>" in fin
    # irmão comum não vê abas administrativas
    ap = cliente("aprendiz").get(reverse("tesouraria:minhas")).content.decode()
    assert ">Caixa</a>" not in ap


def test_conta_fora_do_menu_lateral(cliente, usuarios):
    html = cliente("mestre").get(reverse("core:painel")).content.decode()
    assert "menu-usuario" in html and "Meu cadastro" in html
    lateral = html.split('aria-label="Menu principal"')[1].split("</nav>")[0]
    assert "Meu cadastro" not in lateral and "Alterar senha" not in lateral


def test_central_de_pendencias(cliente, usuarios, sessao, cargos):
    from apps.core.pendencias import tarefas_do_usuario
    from tests.test_fluxos import _fluxo_ata
    ata = _fluxo_ata(cliente, usuarios, sessao, cargos)  # ata aprovada: venerável e secretário precisam assinar
    textos = [t["texto"] for t in tarefas_do_usuario(usuarios["veneravel"])]
    assert any("Assinar a ata" in t for t in textos)
    assert not any("Assinar a ata" in t for t in [x["texto"] for x in tarefas_do_usuario(usuarios["mestre"])])
    # tarefas urgentes vêm primeiro
    niveis = [t["nivel"] for t in tarefas_do_usuario(usuarios["veneravel"])]
    assert niveis == sorted(niveis, key=lambda n: {"urgente": 0, "atencao": 1, "info": 2}[n])
    # painel mostra o botão com link direto para a ação
    html = cliente("veneravel").get(reverse("core:painel")).content.decode()
    assert reverse("atas:assinar", args=[ata.pk]) in html


def test_pendencia_sessao_sem_ata_e_tesouraria(cliente, usuarios, sessao):
    from apps.core.pendencias import tarefas_do_usuario
    t = [x["texto"] for x in tarefas_do_usuario(usuarios["secretario"])]
    assert any("Redigir a ata" in x for x in t)
    t = [x["texto"] for x in tarefas_do_usuario(usuarios["tesoureiro"])]
    assert any("Gerar as mensalidades" in x for x in t)


def test_busca_rapida_respeita_grau_e_perfil(cliente, usuarios):
    from datetime import timedelta
    from apps.documentos.models import Documento
    from django.core.files.uploadedfile import SimpleUploadedFile
    Documento.objects.create(titulo="Ritual secreto de Mestre", grau_minimo=3, enviado_por=usuarios["secretario"],
                             arquivo=SimpleUploadedFile("r.pdf", b"%PDF-1", content_type="application/pdf"))
    r = cliente("aprendiz").get(reverse("core:busca"), {"q": "ritual"}).json()["resultados"]
    assert not [x for x in r if x["grupo"] == "Biblioteca"]
    r = cliente("mestre").get(reverse("core:busca"), {"q": "ritual"}).json()["resultados"]
    assert [x for x in r if x["grupo"] == "Biblioteca"]
    r = cliente("mestre").get(reverse("core:busca"), {"q": "veneravel"}).json()["resultados"]
    assert any(x["grupo"] == "Irmãos" for x in r)
    sem_q = cliente("aprendiz").get(reverse("core:busca")).json()["resultados"]
    assert sem_q and all(x["grupo"] == "Ir para" for x in sem_q)
    assert not any("Tesouraria" in x["rotulo"] for x in sem_q)
    from django.test import Client
    assert Client().get(reverse("core:busca")).status_code == 302


def test_sessao_em_abas_e_urls_antigas_redirecionam(cliente, usuarios, sessao, cargos):
    sec = cliente("secretario")
    base = reverse("sessoes:detalhe", args=[sessao.pk])
    html = sec.get(base).content.decode()
    for rot in ("Resumo", "Escala", "Presença", "Visitantes", "Cerimônias", "Ata"):
        assert f"{rot}" in html
    # irmão comum só vê Resumo e Ata
    ap = cliente("aprendiz").get(base).content.decode()
    assert "Presença" not in ap.split('aria-label="Seções da sessão"')[1].split("</nav>")[0]
    assert cliente("aprendiz").get(base, {"aba": "presenca"}).content.decode().count("Marcar todos presentes") == 0
    # as telas antigas redirecionam para a aba correspondente
    for nome, aba in (("sessoes:escala", "escala"), ("sessoes:presenca", "presenca"), ("sessoes:cerimonias", "cerimonias"),
                      ("visitas:sessao", "visitantes")):
        r = sec.get(reverse(nome, args=[sessao.pk] if nome != "visitas:sessao" else [sessao.pk]))
        assert r.status_code == 302 and r["Location"].endswith(f"?aba={aba}"), nome
    # salvar a presença volta para a mesma aba
    r = sec.post(reverse("sessoes:presenca", args=[sessao.pk]), {})
    assert r["Location"].endswith("?aba=presenca")


def test_visitante_invalido_reexibe_aba_com_erros(cliente, usuarios, sessao):
    r = cliente("secretario").post(reverse("visitas:sessao", args=[sessao.pk]), {"novo-nome": "", "novo-grau": 3})
    html = r.content.decode()
    assert r.status_code == 200 and "Novo visitante" in html and 'class="erro"' in html


def test_formulario_do_irmao_em_abas(cliente, usuarios):
    html = cliente("secretario").get(reverse("irmaos:editar", args=[usuarios["mestre"].pk])).content.decode()
    for aba in ("Maçônico", "Pessoal", "Endereço", "Profissional", "Saúde e plano", "Acesso", "Família"):
        assert f">{aba}</button>" in html
    assert 'name="cpf"' in html and 'name="plano_saude"' in html and 'name="perfis"' in html
    # perfis não aparecem no "meu cadastro" (cadastro próprio não altera perfil/grau)
    meu = cliente("mestre").get(reverse("irmaos:meu_perfil")).content.decode()
    assert 'name="perfis"' not in meu and 'name="grau"' not in meu


def test_landing_publica_e_pwa(cliente, usuarios):
    from django.test import Client
    anon = Client().get("/")
    html = anon.content.decode()
    assert anon.status_code == 200 and "Tradição e tecnologia" in html and reverse("login") in html
    assert "Esquadro e compasso" in html and "data-tilt" in html and "prefers-reduced-motion" not in html  # css fica no arquivo
    # logado, a mesma URL mostra o painel
    assert "O que precisa da sua atenção" in cliente("mestre").get("/").content.decode()
    # PWA
    m = Client().get(reverse("core:manifest"))
    dados = m.json()
    assert m["Content-Type"].startswith("application/manifest+json") and dados["display"] == "standalone"
    assert {i["purpose"] for i in dados["icons"]} == {"any", "maskable"} and dados["theme_color"] == "#4fb3e8"
    sw = Client().get(reverse("core:service_worker"))
    assert sw["Content-Type"].startswith("application/javascript") and sw["Service-Worker-Allowed"] == "/"
    assert b"/static/" in sw.content and b"navigate" in sw.content
    assert b"/api/" not in sw.content  # nenhuma rota autenticada é guardada em cache
    assert Client().get(reverse("core:offline")).status_code == 200


def test_arquivos_de_icones_existem():
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent / "static"
    for nome in ("icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png", "favicon-32.png"):
        assert (base / "icons" / nome).stat().st_size > 500, nome
    assert "G" in (base / "img" / "emblema.svg").read_text()
