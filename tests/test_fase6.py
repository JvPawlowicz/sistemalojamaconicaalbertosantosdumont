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
