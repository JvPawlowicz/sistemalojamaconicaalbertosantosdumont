import csv
import io
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from django.utils.formats import number_format

from apps.core.pdf import pdf_bytes, resposta_pdf

_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")


def formatar(valor):
    """Texto de exibição (HTML, PDF, CSV) em pt-BR."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M") if timezone.is_aware(valor) else valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, Decimal):
        return number_format(valor, 2, force_grouping=True)
    return str(valor)


def _seguro_csv(texto):
    # Evita injeção de fórmulas ao abrir no Excel/LibreOffice.
    return "'" + texto if texto and texto[0] in _PERIGOSOS and not texto.replace(",", "").replace(".", "").lstrip("-").isdigit() else texto


def para_csv(titulo, cabecalho, linhas):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cabecalho)
    for l in linhas:
        w.writerow([_seguro_csv(formatar(c)) for c in l])
    resp = HttpResponse("﻿" + buf.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{titulo}.csv"'
    return resp


def para_xlsx(titulo, cabecalho, linhas):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31]
    ws.append(list(cabecalho))
    for c in ws[1]:
        c.font = Font(bold=True)
    for l in linhas:
        ws.append([_seguro_csv(formatar(c)) if isinstance(c, str) else (c if isinstance(c, (int, float)) else
                   float(c) if isinstance(c, Decimal) else formatar(c)) for c in l])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 2, 50)
    buf = io.BytesIO()
    wb.save(buf)
    resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{titulo}.xlsx"'
    return resp


def para_pdf(request, titulo, subtitulo, cabecalho, linhas):
    dados = pdf_bytes("relatorios/pdf.html", {
        "titulo": titulo, "subtitulo": subtitulo, "cabecalho": cabecalho,
        "linhas": [[formatar(c) for c in l] for l in linhas], "emitido": timezone.now(), "usuario": request.user,
    }, request)
    return resposta_pdf(f"{titulo}.pdf", dados, inline=False)
