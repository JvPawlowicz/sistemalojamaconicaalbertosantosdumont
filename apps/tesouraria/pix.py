"""PIX copia-e-cola (BR Code estático, padrão EMV do Banco Central) e leitura de extratos OFX."""
import re
import unicodedata
from datetime import date
from decimal import Decimal


def _ascii(texto, tamanho):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9 .\-]", "", t).strip()[:tamanho]


def _tlv(id_, valor):
    return f"{id_}{len(valor):02d}{valor}"


def crc16(texto: str) -> str:
    """CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF) exigido pelo BR Code."""
    crc = 0xFFFF
    for byte in texto.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def txid_da_mensalidade(pk: int) -> str:
    return f"L{pk}"


def br_code(chave: str, nome: str, cidade: str, valor: Decimal | None = None, txid: str = "***") -> str:
    """Monta o payload "PIX copia e cola" com valor fixo e identificador (txid)."""
    conta = _tlv("00", "br.gov.bcb.pix") + _tlv("01", chave.strip())
    txid = re.sub(r"[^A-Za-z0-9]", "", txid)[:25] or "***"
    corpo = (_tlv("00", "01") + _tlv("26", conta) + _tlv("52", "0000") + _tlv("53", "986")
             + (_tlv("54", f"{valor:.2f}") if valor else "")
             + _tlv("58", "BR") + _tlv("59", _ascii(nome, 25).upper() or "LOJA")
             + _tlv("60", _ascii(cidade, 15).upper() or "SAO PAULO") + _tlv("62", _tlv("05", txid)))
    corpo += "6304"
    return corpo + crc16(corpo)


def lancamentos_ofx(conteudo: bytes | str):
    """Lê as transações de um OFX (créditos e débitos). Devolve [{fitid, data, valor, descricao}]."""
    if isinstance(conteudo, bytes):
        try:
            conteudo = conteudo.decode("utf-8")
        except UnicodeDecodeError:
            conteudo = conteudo.decode("latin-1")
    saida = []
    for bloco in re.findall(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|$)", conteudo, re.S | re.I):
        def campo(nome):
            m = re.search(rf"<{nome}>([^<\r\n]*)", bloco, re.I)
            return m.group(1).strip() if m else ""

        bruto = campo("DTPOSTED")[:8]
        try:
            data = date(int(bruto[:4]), int(bruto[4:6]), int(bruto[6:8]))
            valor = Decimal(campo("TRNAMT").replace(",", "."))
        except (ValueError, ArithmeticError):
            continue
        saida.append({"fitid": campo("FITID") or f"{bruto}-{valor}-{campo('MEMO')}", "data": data, "valor": valor,
                      "descricao": " ".join(x for x in (campo("NAME"), campo("MEMO")) if x)})
    return saida


def sugerir_lancamento(transacao, abertos):
    """Escolhe a mensalidade em aberto mais provável para um crédito: txid na descrição, senão nome + valor."""
    from .services import valor_atualizado

    desc = transacao["descricao"].upper()
    m = re.search(r"\bL(\d{1,9})\b", desc)
    if m:
        for l in abertos:
            if l.pk == int(m.group(1)):
                return l, "txid"
    candidatos = [l for l in abertos if transacao["valor"] in (l.valor, valor_atualizado(l)["total"])]
    for l in candidatos:
        partes = [p for p in unicodedata.normalize("NFKD", l.irmao.nome_completo).encode("ascii", "ignore").decode().upper().split() if len(p) > 2]
        if partes and sum(p in desc for p in partes) >= 2:
            return l, "nome e valor"
    return None, ""
