"""Editor rico de atas: sanitização, hash estável, compatibilidade com atas antigas e API do @."""
import pytest
from django.urls import reverse

from apps.atas.models import Ata
from apps.atas.sanitizar import sanitizar_html, texto_para_html, texto_simples
from apps.sessoes import services as ses
from tests.test_fluxos import _assinar, _fluxo_ata


def test_sanitizacao_remove_scripts_eventos_e_estilos_perigosos():
    sujo = ('<p style="text-align:center;color:red;background:url(javascript:x)" onclick="alert(1)">Olá <script>alert(1)</script>'
            '<img src=x onerror=alert(2)><a href="javascript:alert(3)">link</a><strong>forte</strong></p>'
            '<iframe src="//evil"></iframe><h2>Título</h2><h1>não</h1><u>sub</u>')
    limpo = sanitizar_html(sujo)
    assert "script" not in limpo and "onclick" not in limpo and "onerror" not in limpo and "iframe" not in limpo
    assert "javascript" not in limpo and "<img" not in limpo and "<a" not in limpo and "<h1" not in limpo
    assert 'style="text-align: center"' in limpo and "color" not in limpo
    assert "<strong>forte</strong>" in limpo and "<h2>Título</h2>" in limpo and "<u>sub</u>" in limpo


def test_texto_simples_e_conversao_de_ata_antiga():
    html = "<h2>Abertura</h2><p>Primeira linha.</p><p>Segunda &amp; terceira<br>quebra</p><ul><li>a</li><li>b</li></ul>"
    t = texto_simples(html)
    assert t.splitlines()[0] == "Abertura" and "Segunda & terceira\nquebra" in t and "a\nb" in t
    h = texto_para_html("Linha 1\nLinha 2\n\nParágrafo <script>x</script>")
    assert h.startswith("<p>Linha 1<br>Linha 2</p>") and "&lt;script&gt;" in h and "<script>" not in h


def test_salvar_ata_sanitiza_e_assinatura_cobre_o_html_sanitizado(cliente, usuarios, sessao, cargos):
    ses.gerar_escala(sessao)
    sec = cliente("secretario")
    sec.post(reverse("atas:criar", args=[sessao.pk]), {
        "numero": 1, "livro": "1", "folha": "1",
        "conteudo": '<h2>ATA</h2><p onclick="x()">Texto <strong>negrito</strong><script>alert(1)</script></p>'})
    ata = Ata.objects.get(sessao=sessao)
    assert ata.formato == "html" and "<script" not in ata.conteudo and "onclick" not in ata.conteudo
    assert "<strong>negrito</strong>" in ata.conteudo_html
    h1 = ata.hash_conteudo
    sec.post(reverse("atas:circular", args=[ata.pk]))
    sec.post(reverse("atas:aprovar", args=[ata.pk]), {"signatarios": [usuarios["veneravel"].pk, usuarios["secretario"].pk]})
    _assinar(cliente, "veneravel", ata)
    from apps.atas.models import AssinaturaAta
    ass = AssinaturaAta.objects.get()
    assert ass.hash_documento == h1 and ata.hash_conteudo == h1
    # PDF e tela de leitura exibem o HTML formatado
    pdf = cliente("mestre").get(reverse("atas:pdf", args=[ata.pk]))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    det = cliente("mestre").get(reverse("atas:detalhe", args=[ata.pk])).content.decode()
    assert "<strong>negrito</strong>" in det and "<script>alert" not in det


def test_ata_em_branco_e_so_html_vazio_sao_recusadas(cliente, usuarios, sessao):
    r = cliente("secretario").post(reverse("atas:criar", args=[sessao.pk]), {"numero": 1, "conteudo": "<p></p><p><br></p>"})
    assert r.status_code == 200 and "não pode ficar em branco" in r.content.decode() and not Ata.objects.exists()


def test_ata_antiga_em_texto_abre_no_editor_e_vira_html_ao_salvar(cliente, usuarios, sessao):
    ata = Ata.objects.create(sessao=sessao, conteudo="Linha A\nLinha B\n\nSegundo parágrafo", formato="texto", autor=usuarios["secretario"])
    assert "Linha A" in ata.texto and ata.conteudo_html.startswith("<p>Linha A<br>Linha B</p>")
    h_antes = ata.hash_conteudo
    sec = cliente("secretario")
    r = sec.get(reverse("atas:editar", args=[ata.pk]))
    assert "&lt;p&gt;Linha A&lt;br&gt;Linha B&lt;/p&gt;" in r.content.decode()  # converteu para parágrafos no editor
    sec.post(reverse("atas:editar", args=[ata.pk]), {"numero": 3, "conteudo": "<p>Linha A</p><p>Revisado</p>"})
    ata.refresh_from_db()
    assert ata.formato == "html" and ata.numero == 3 and ata.hash_conteudo != h_antes


def test_ata_antiga_assinada_continua_com_o_mesmo_hash(cliente, usuarios, sessao, cargos):
    """Atas em texto simples assinadas antes do editor não podem mudar de hash."""
    ses.gerar_escala(sessao)
    ata = Ata.objects.create(sessao=sessao, numero=1, conteudo="Texto antigo", formato="texto", autor=usuarios["secretario"])
    esperado = ata.hash_conteudo
    sec = cliente("secretario")
    sec.post(reverse("atas:circular", args=[ata.pk]))
    sec.post(reverse("atas:aprovar", args=[ata.pk]), {"signatarios": [usuarios["veneravel"].pk]})
    _assinar(cliente, "veneravel", ata)
    ata.refresh_from_db()
    assert ata.hash_conteudo == esperado and ata.status == "assinada"


def test_editor_carrega_bundle_e_api_do_arroba_traz_modelos_e_irmaos(cliente, usuarios, sessao, cargos):
    from apps.atas.models import ModeloTexto
    ses.gerar_escala(sessao)
    ModeloTexto.objects.create(titulo="Abertura", atalho="abertura", categoria="abertura", texto="Presidida por {{veneravel}}.")
    html = cliente("secretario").get(reverse("atas:criar", args=[sessao.pk])).content.decode()
    assert "vendor/editor-ata.js" in html and "EditorAta.init" in html and 'id="editor-ata"' in html
    api = cliente("secretario").get(reverse("atas:modelos_buscar"), {"sessao": sessao.pk, "q": "abert"}).json()["itens"]
    assert api[0]["tipo"] == "modelo" and "Veneravel" in api[0]["texto"] and api[0]["grupo"] == "Textos prontos"
    api = cliente("secretario").get(reverse("atas:modelos_buscar"), {"sessao": sessao.pk, "q": "veneravel"}).json()["itens"]
    assert any(i["tipo"] == "irmao" and i["texto"].startswith("Ir∴") for i in api)
    r = cliente("secretario").get(reverse("atas:modelos_renderizar"), {"sessao": sessao.pk, "texto": "Hoje é {{data}}"}).json()
    assert "{{" not in r["texto"]
    assert cliente("mestre").get(reverse("atas:modelos_renderizar"), {"sessao": sessao.pk}).status_code == 403


def test_bundle_do_editor_existe_e_tem_licencas():
    from pathlib import Path
    v = Path(__file__).resolve().parent.parent / "static" / "vendor"
    js = (v / "editor-ata.js").read_text()
    assert len(js) > 100_000 and "EditorAta" in js and "Tiptap" in js
    assert "MIT" in (v / "editor-ata.LICENSES.txt").read_text()
