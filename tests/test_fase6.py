from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.agape.models import Agape, AgapeLancamento, Item, Movimento, Participante
from apps.atas import services as atas_services
from apps.atas.models import Ata
from apps.core.models import Loja
from apps.tesouraria.models import MovimentoCaixa


def _agape(cliente, sessao=None, valor="50"):
    dados = {"data": timezone.localdate(), "descricao": "Ágape", "valor_por_pessoa": valor}
    if sessao:
        dados["sessao"] = sessao.pk
    cliente("tesoureiro").post(reverse("agape:criar"), dados)
    return Agape.objects.latest("pk")


def test_agape_so_tesoureiro_gerencia_e_cria_subpresenca(cliente, usuarios):
    assert cliente("mestre").get(reverse("agape:criar")).status_code == 403
    assert cliente("mestre").get(reverse("agape:caixa")).status_code == 403
    assert cliente("mestre").get(reverse("agape:inventario")).status_code == 403
    a = _agape(cliente)
    assert a.participantes.count() >= 5 and a.n_irmaos == a.participantes.count()
    # o irmão decide se vai; só ele altera a própria participação
    r = cliente("mestre").post(reverse("agape:confirmar", args=[a.pk]), {"vai": "0"}, follow=True)
    assert "não vai" in r.content.decode().lower()
    assert not a.participantes.get(irmao=usuarios["mestre"]).vai


def test_caixa_do_agape_nao_se_mistura_com_o_da_loja(cliente, usuarios):
    a = _agape(cliente, valor="40")
    t = cliente("tesoureiro")
    t.post(reverse("agape:participante", args=[a.pk, usuarios["mestre"].pk]), {"acao": "pago"})
    assert AgapeLancamento.saldo() == Decimal("40")
    assert MovimentoCaixa.objects.count() == 0  # nada caiu no caixa da loja
    t.post(reverse("agape:participante", args=[a.pk, usuarios["mestre"].pk]), {"acao": "pago"})  # estorno
    assert AgapeLancamento.saldo() == 0


def test_visitantes_sao_custo_da_loja_com_repasse_unico(cliente, usuarios):
    a = _agape(cliente, valor="30")
    t = cliente("tesoureiro")
    for n in ("Visitante A", "Visitante B"):
        t.post(reverse("agape:visitante_novo", args=[a.pk]), {"v-nome": n, "v-loja": "Loja X"})
    assert a.n_visitantes == 2 and a.custo_visitantes == Decimal("60")
    t.post(reverse("agape:repasse", args=[a.pk]))
    t.post(reverse("agape:repasse", args=[a.pk]))  # idempotente
    assert AgapeLancamento.saldo() == Decimal("60")
    despesas = MovimentoCaixa.objects.filter(tipo="despesa")
    assert despesas.count() == 1 and despesas.first().valor == Decimal("60")


def test_sincroniza_com_a_presenca_da_sessao(cliente, usuarios, sessao):
    from apps.sessoes.models import Presenca

    Presenca.objects.update_or_create(sessao=sessao, irmao=usuarios["mestre"], defaults={"situacao": "presente"})
    a = _agape(cliente, sessao)
    cliente("tesoureiro").post(reverse("agape:sincronizar", args=[a.pk]))
    assert a.participantes.get(irmao=usuarios["mestre"]).vai
    assert not a.participantes.get(irmao=usuarios["aprendiz"]).vai


def test_inventario_estoque_minimo_ajuste_e_compra_no_caixa(cliente, usuarios):
    item = Item.objects.create(nome="Guaraná 2L", unidade="un", minimo=6)
    t = cliente("tesoureiro")
    hoje = timezone.localdate()
    t.post(reverse("agape:inventario"), {"item": item.pk, "tipo": "entrada", "quantidade": 12, "data": hoje, "custo_total": "84.00"})
    assert item.estoque == 12 and AgapeLancamento.saldo() == Decimal("-84")
    t.post(reverse("agape:inventario"), {"item": item.pk, "tipo": "consumo", "quantidade": 8, "data": hoje})
    assert item.estoque == 4 and item.baixo
    t.post(reverse("agape:inventario"), {"item": item.pk, "tipo": "ajuste", "quantidade": 10, "data": hoje})
    assert item.estoque == 10 and not item.baixo
    from apps.core.pendencias import tarefas_do_usuario

    Movimento.objects.create(item=item, tipo="perda", quantidade=-8, data=hoje)
    assert any("repor" in x["texto"] for x in tarefas_do_usuario(usuarios["tesoureiro"]))


def test_numeracao_da_ata_parte_do_numero_inicial_da_loja(db, sessao, usuarios):
    loja = Loja.atual()
    loja.ata_numero_inicial = 1287
    loja.save()
    assert atas_services.proximo_numero(sessao) == 1287
    ata = Ata.objects.create(sessao=sessao, numero=1287, conteudo="x", autor=usuarios["secretario"])
    assert atas_services.proximo_numero(sessao) == 1288
    assert ata.identificacao == f"1287/{sessao.ano.nome.replace('/', '-')}"
    loja.ata_numeracao = "gestao"
    loja.save()
    assert atas_services.proximo_numero(sessao) == 1288  # mesma gestão


def test_textos_padrao_do_secretario_sao_idempotentes(cliente, usuarios):
    from apps.atas.models import ModeloTexto
    from apps.atas.modelos_padrao import MODELOS

    assert cliente("mestre").post(reverse("atas:modelos_padroes")).status_code == 403
    s = cliente("secretario")
    assert s.get(reverse("atas:modelos_padroes")).status_code == 200
    s.post(reverse("atas:modelos_padroes"))
    assert ModeloTexto.objects.count() == len(MODELOS) >= 25
    ModeloTexto.objects.filter(atalho="encerramento").update(texto="Editado pela Secretaria")
    s.post(reverse("atas:modelos_padroes"))
    assert ModeloTexto.objects.count() == len(MODELOS)
    assert ModeloTexto.objects.get(atalho="encerramento").texto == "Editado pela Secretaria"


def test_logo_e_marca_dagua_nos_pdfs(db, settings, tmp_path):
    import io

    from django.core.files.base import ContentFile
    from PIL import Image

    from apps.core.pdf import logo_data_uri, marca_dagua_data_uri

    settings.MEDIA_ROOT = tmp_path
    loja = Loja.atual()
    assert logo_data_uri(loja) == "" and marca_dagua_data_uri(loja) == ""
    buf = io.BytesIO()
    Image.new("RGBA", (50, 50), (10, 100, 160, 255)).save(buf, "PNG")
    loja.brasao.save("l.png", ContentFile(buf.getvalue()))
    loja.marca_dagua.save("m.png", ContentFile(buf.getvalue()))
    loja.marca_dagua_intensidade = 10
    loja.save()
    assert logo_data_uri(loja).startswith("data:image/png;base64,")
    m = Image.open(io.BytesIO(__import__("base64").b64decode(marca_dagua_data_uri(loja).split(",")[1])))
    assert m.getchannel("A").getextrema()[1] == 25  # 255 * 10%


def test_ata_nova_parte_do_modelo_completo_do_tipo_da_sessao(cliente, usuarios, sessao):
    s = cliente("secretario")
    s.post(reverse("atas:modelos_padroes"))
    sessao.tipo = "iniciacao"
    sessao.save()
    html = s.get(reverse("atas:criar", args=[sessao.pk])).content.decode()
    assert "Iniciação do profano" in html and "Nada mais havendo a tratar" in html


def test_marca_compasso_no_rodape_e_manifesto(cliente, usuarios):
    assert "Compasso" in cliente("mestre").get(reverse("core:painel")).content.decode()
    assert cliente("mestre").get(reverse("core:manifest")).json()["short_name"] == "Compasso"


def test_secretario_salva_trecho_como_texto_padrao_e_lista_todos(cliente, usuarios, sessao):
    import json

    from apps.atas.models import ModeloTexto

    s = cliente("secretario")
    for _ in range(2):
        r = s.post(reverse("atas:modelo_rapido"), json.dumps({"titulo": "Abertura solene", "texto": "Texto {{loja}}"}), content_type="application/json")
        assert r.status_code == 200
    assert set(ModeloTexto.objects.values_list("atalho", flat=True)) == {"abertura-solene", "abertura-solene-2"}
    assert cliente("mestre").post(reverse("atas:modelo_rapido"), "{}", content_type="application/json").status_code == 403
    s.post(reverse("atas:modelos_padroes"))
    todos = s.get(reverse("atas:modelos_buscar"), {"sessao": sessao.pk, "q": "", "todos": 1}).json()["itens"]
    assert len(todos) > 10


# --- PIX e conciliação ---
def test_br_code_tem_crc_valido_e_campos_do_pix():
    from apps.tesouraria.pix import br_code, crc16

    c = br_code("loja@exemplo.com", "Loja Maçônica Alberto Santos Dumont", "São Paulo", Decimal("150.00"), "L42")
    assert c.startswith("000201") and "br.gov.bcb.pix" in c and "5406150.00" in c and "0503L42" in c
    assert c[-4:] == crc16(c[:-4])
    assert crc16("123456789") == "29B1"  # vetor de teste padrão CRC16/CCITT-FALSE


OFX = """OFXHEADER:100
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261005120000<TRNAMT>150.00<FITID>A1<MEMO>PIX RECEBIDO L{pk} JOAO
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261006120000<TRNAMT>150,00<FITID>A2<NAME>CARLOS SECRETARIO SOUZA<MEMO>PIX
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261007<TRNAMT>-40.00<FITID>A3<MEMO>TARIFA
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""


def test_conciliacao_ofx_sugere_por_txid_e_por_nome_e_da_baixa_sem_duplicar(cliente, usuarios):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.tesouraria.models import ExtratoImportado, Lancamento

    hoje = timezone.localdate()
    l1 = Lancamento.objects.create(irmao=usuarios["mestre"], competencia=hoje.replace(day=1), valor=Decimal("150"), vencimento=hoje, status="pendente")
    l2 = Lancamento.objects.create(irmao=usuarios["secretario"], competencia=hoje.replace(day=1), valor=Decimal("150"), vencimento=hoje, status="pendente")
    t = cliente("tesoureiro")
    arq = SimpleUploadedFile("extrato.ofx", OFX.format(pk=l1.pk).encode())
    html = t.post(reverse("tesouraria:conciliar"), {"arquivo": arq}).content.decode()
    assert "txid" in html and "nome e valor" in html and "TARIFA" not in html
    dados = {"acao": "confirmar", "baixar": [f"A1|{l1.pk}", f"A2|{l2.pk}"], "valor_A1": "150.00", "data_A1": "2026-10-05",
             "valor_A2": "150.00", "data_A2": "2026-10-06"}
    t.post(reverse("tesouraria:conciliar"), dados)
    t.post(reverse("tesouraria:conciliar"), dados)  # repetir não duplica
    l1.refresh_from_db(); l2.refresh_from_db()
    assert l1.status == "pago" and l2.status == "pago" and ExtratoImportado.objects.count() == 2
    assert MovimentoCaixa.objects.filter(tipo="receita").count() == 2
    assert cliente("mestre").get(reverse("tesouraria:conciliar")).status_code == 403


def test_pix_da_mensalidade_so_para_o_dono_ou_tesoureiro(cliente, usuarios):
    from apps.tesouraria.models import Lancamento

    loja = Loja.atual()
    loja.chave_pix = "loja@exemplo.com"
    loja.save()
    hoje = timezone.localdate()
    l = Lancamento.objects.create(irmao=usuarios["mestre"], competencia=hoje.replace(day=1), valor=Decimal("150"), vencimento=hoje, status="pendente")
    assert "PIX" in cliente("mestre").get(reverse("tesouraria:pix", args=[l.pk])).content.decode()
    assert cliente("tesoureiro").get(reverse("tesouraria:pix", args=[l.pk])).status_code == 200
    assert cliente("aprendiz").get(reverse("tesouraria:pix", args=[l.pk])).status_code == 403


# --- aniversários ---
def test_aniversarios_de_vida_e_macônicos_no_painel_e_email_sem_duplicar(cliente, usuarios, mailoutbox):
    from datetime import date

    from django.core.management import call_command

    from apps.irmaos.aniversarios import do_dia
    from apps.irmaos.models import AniversarioEnviado

    hoje = timezone.localdate()
    m = usuarios["mestre"]
    m.data_nascimento = date(1980, hoje.month, hoje.day)
    m.data_iniciacao = date(hoje.year - 5, hoje.month, hoje.day)
    m.email = "mestre@exemplo.com"
    m.save()
    tipos = {a["tipo"] for a in do_dia(hoje) if a["irmao"] == m}
    assert tipos == {"vida", "iniciacao"}
    html = cliente("aprendiz").get(reverse("core:painel")).content.decode()
    assert "5 anos de iniciação" in html
    loja = Loja.atual()
    loja.aniversario_email = True
    loja.save()
    call_command("enviar_lembretes", verbosity=0)
    call_command("enviar_lembretes", verbosity=0)  # segunda execução no mesmo dia não repete
    assert AniversarioEnviado.objects.filter(irmao=m).count() == 2
    assert len([x for x in mailoutbox if "Parabéns" in x.subject]) == 2


# --- busca dentro de PDFs ---
def test_busca_no_texto_dos_pdfs_respeita_o_grau(cliente, usuarios, settings, tmp_path):
    from django.core.files.base import ContentFile
    from weasyprint import HTML

    from apps.documentos.models import Documento

    settings.MEDIA_ROOT = tmp_path
    pdf = HTML(string="<p>O Landmark da reverência ao Grande Arquiteto do Universo é antigo.</p>").write_pdf()
    d = Documento(titulo="Prancha X", categoria="prancha", grau_minimo=3, enviado_por=usuarios["secretario"])
    d.arquivo.save("p.pdf", ContentFile(pdf))
    assert "reverência" in d.texto_extraido
    html = cliente("mestre").get(reverse("documentos:lista"), {"q": "reverência"}).content.decode()
    assert "Prancha X" in html and "no texto" in html
    assert "Prancha X" not in cliente("aprendiz").get(reverse("documentos:lista"), {"q": "reverência"}).content.decode()
    busca = cliente("mestre").get(reverse("core:busca"), {"q": "reverência"}).json()["resultados"]
    assert any(r["rotulo"] == "Prancha X" for r in busca)


def test_saude_publica_sem_login(client, db):
    r = client.get(reverse("core:saude"))
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_ajuda_mostra_manual_conforme_o_perfil(cliente, usuarios):
    t = cliente("tesoureiro").get(reverse("core:ajuda")).content.decode()
    assert "Manual do Tesoureiro" in t and "Manual do Secretário" not in t
    a = cliente("aprendiz").get(reverse("core:ajuda")).content.decode()
    assert "Para todos os irmãos" in a and "Manual do Tesoureiro" not in a
