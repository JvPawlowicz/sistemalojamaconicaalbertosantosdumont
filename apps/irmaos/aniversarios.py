"""Aniversários de vida e maçônicos (iniciação, passagem e exaltação) dos irmãos ativos."""
import calendar
from datetime import date

from .models import Irmao

TIPOS = (
    ("data_nascimento", "vida", "Aniversário"),
    ("data_iniciacao", "iniciacao", "Aniversário de iniciação"),
    ("data_promocao", "promocao", "Aniversário de passagem"),
    ("data_elevacao", "elevacao", "Aniversário de exaltação"),
)


def _dia(d, ano, mes):
    return min(d.day, calendar.monthrange(ano, mes)[1])


def do_mes(ano, mes):
    """[{data, irmao, tipo, rotulo, anos}] ordenado pelo dia (anos só para datas maçônicas)."""
    saida = []
    base = Irmao.objects.filter(is_active=True, grau__isnull=False)
    for campo, tipo, rotulo in TIPOS:
        for i in base.filter(**{f"{campo}__month": mes}):
            d = getattr(i, campo)
            if tipo != "vida" and d.year >= ano:
                continue
            saida.append({"data": date(ano, mes, _dia(d, ano, mes)), "irmao": i, "tipo": tipo, "rotulo": rotulo,
                          "anos": None if tipo == "vida" else ano - d.year})
    return sorted(saida, key=lambda x: (x["data"], x["irmao"].nome_completo))


def do_dia(hoje):
    return [a for a in do_mes(hoje.year, hoje.month) if a["data"] == hoje]
