from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.cargos.models import Cargo, Gestao
from apps.core import perfis as P
from apps.core.models import AnoMaconico, TermoAceite
from apps.irmaos.models import CategoriaIrmao, Irmao
from apps.sessoes.models import Sessao

SENHA = "senha-de-teste-123"


def _irmao(username, grau, perfis=(), **kw):
    i = Irmao.objects.create(username=username, nome_completo=username.title(), grau=grau, perfis=list(perfis),
                             email=f"{username}@x.org", **kw)
    i.set_password(SENHA)
    i.save()
    return i


@pytest.fixture
def termo(db):
    return TermoAceite.objects.create(versao=1)


@pytest.fixture
def categoria(db):
    return CategoriaIrmao.objects.create(nome="Integral", valor_mensal=Decimal("100"))


@pytest.fixture
def usuarios(db, termo, categoria):
    u = {
        "aprendiz": _irmao("aprendiz", 1, categoria=categoria),
        "companheiro": _irmao("companheiro", 2, categoria=categoria),
        "mestre": _irmao("mestre", 3, categoria=categoria),
        "veneravel": _irmao("veneravel", 3, [P.VENERAVEL], categoria=categoria),
        "secretario": _irmao("secretario", 3, [P.SECRETARIO], categoria=categoria),
        "tesoureiro": _irmao("tesoureiro", 3, [P.TESOUREIRO], categoria=categoria),
        "dev": _irmao("dev", None, [P.DESENVOLVEDOR]),
    }
    from apps.core.models import AceiteTermo

    for i in u.values():
        AceiteTermo.objects.create(irmao=i, termo=termo, hash_termo=termo.hash)
    return u


@pytest.fixture
def cliente(usuarios):
    def _login(nome):
        c = Client()
        assert c.login(username=nome, password=SENHA)
        return c
    return _login


@pytest.fixture
def sessao(db):
    return Sessao.objects.create(data_hora=timezone.now() - timedelta(days=1), grau=1, tipo="ordinaria",
                                 status="realizada", pauta="Pauta")


@pytest.fixture
def cargos(db, usuarios):
    ano = AnoMaconico.atual()
    vm = Cargo.objects.create(nome="Venerável Mestre", ordem=1)
    sec = Cargo.objects.create(nome="Secretário", ordem=2)
    Gestao.objects.create(ano=ano, cargo=vm, irmao=usuarios["veneravel"])
    Gestao.objects.create(ano=ano, cargo=sec, irmao=usuarios["secretario"])
    return vm, sec
