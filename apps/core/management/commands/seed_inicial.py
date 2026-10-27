"""Dados iniciais: configuração da Loja, termo, cargos, categorias e modelos de texto.

Uso:  python manage.py seed_inicial            (produção/primeiro uso)
      python manage.py seed_inicial --demo     (inclui usuários e dados fictícios para testes)
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.atas.models import ModeloTexto
from apps.cargos.models import Cargo, Gestao
from apps.core import perfis as P
from apps.core.models import AnoMaconico, Loja, TermoAceite
from apps.irmaos.models import CategoriaIrmao, Irmao
from apps.sessoes.models import Sessao
from apps.tesouraria.models import CategoriaFinanceira

CARGOS = [
    ("Venerável Mestre", "VM", 1), ("1º Vigilante", "1V", 2), ("2º Vigilante", "2V", 3), ("Orador", "OR", 4),
    ("Secretário", "SEC", 5), ("Tesoureiro", "TES", 6), ("Mestre de Cerimônias", "MC", 7), ("Chanceler", "CH", 8),
]

MODELOS = [
    ("Cabeçalho da ata", "cabecalho", "cabecalho",
     "ATA Nº ____ da Sessão {{tipo}} de {{grau}}, realizada em {{data_extenso}}, às {{hora}}, no Templo da {{loja}} nº {{numero_loja}}, "
     "Oriente de {{oriente}}, sob a presidência do Venerável Mestre {{veneravel}}, secretariada por {{secretario}}."),
    ("Abertura dos trabalhos", "abertura", "abertura",
     "Constatada a presença de {{presentes}} irmãos e a regularidade do quórum, o Venerável Mestre declarou abertos os trabalhos "
     "no Grau de {{grau}}, invocando a proteção do Grande Arquiteto do Universo."),
    ("Leitura e aprovação da ata anterior", "ata-anterior", "expediente",
     "Foi lida e, posta em discussão, aprovada sem emendas a ata da sessão anterior."),
    ("Visitantes", "visitantes", "expediente",
     "Registrou-se a presença de {{visitantes}} visitante(s), recebidos fraternalmente."),
    ("Encerramento", "encerramento", "encerramento",
     "Nada mais havendo a tratar, o Venerável Mestre encerrou os trabalhos às ____ horas, do que, para constar, "
     "eu, {{secretario}}, Secretário, lavrei a presente ata que, lida e aprovada, vai assinada pelos Irmãos competentes."),
]


class Command(BaseCommand):
    help = "Cria dados iniciais (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Cria usuários e dados fictícios (NÃO usar em produção).")

    def handle(self, *args, **opts):
        Loja.atual()
        if not TermoAceite.objects.exists():
            TermoAceite.objects.create(versao=1)
        for nome, sigla, ordem in CARGOS:
            Cargo.objects.get_or_create(nome=nome, defaults={"sigla": sigla, "ordem": ordem})
        CategoriaIrmao.objects.get_or_create(nome="Integral", defaults={"valor_mensal": Decimal("0")})
        CategoriaIrmao.objects.get_or_create(nome="Remido", defaults={"isento": True})
        for nome, tipo in (("Mensalidades", "receita"), ("Doações", "receita"), ("Aluguel", "despesa"),
                           ("Material de consumo", "despesa"), ("Contribuição à Potência", "despesa")):
            CategoriaFinanceira.objects.get_or_create(nome=nome, tipo=tipo)
        for titulo, atalho, cat, texto in MODELOS:
            ModeloTexto.objects.get_or_create(atalho=atalho, defaults={"titulo": titulo, "categoria": cat, "texto": texto})
        AnoMaconico.atual()
        self.stdout.write(self.style.SUCCESS("Dados iniciais criados."))
        if opts["demo"]:
            self._demo()

    def _demo(self):
        senha = "demo-senha-123"
        integral = CategoriaIrmao.objects.get(nome="Integral")
        integral.valor_mensal = Decimal("150")
        integral.save()
        usuarios = [
            ("veneravel", "João Venerável da Silva", 3, [P.VENERAVEL]),
            ("secretario", "Carlos Secretário Souza", 3, [P.SECRETARIO]),
            ("tesoureiro", "Pedro Tesoureiro Lima", 3, [P.TESOUREIRO]),
            ("mestre", "Antônio Mestre Costa", 3, []),
            ("companheiro", "Rafael Companheiro Alves", 2, []),
            ("aprendiz", "Lucas Aprendiz Rocha", 1, []),
        ]
        criados = {}
        for username, nome, grau, perfis in usuarios:
            i, novo = Irmao.objects.get_or_create(username=username, defaults={
                "nome_completo": nome, "grau": grau, "perfis": perfis, "email": f"{username}@exemplo.org",
                "categoria": integral, "telefone": "(11) 91234-5678", "data_iniciacao": timezone.localdate() - timedelta(days=900)})
            if novo:
                i.set_password(senha)
                i.save()
            criados[username] = i
        ano = AnoMaconico.atual()
        for cargo_nome, username in (("Venerável Mestre", "veneravel"), ("Secretário", "secretario"), ("Tesoureiro", "tesoureiro")):
            Gestao.objects.get_or_create(ano=ano, cargo=Cargo.objects.get(nome=cargo_nome), defaults={"irmao": criados[username]})
        agora = timezone.now().replace(minute=0, second=0, microsecond=0)
        Sessao.objects.get_or_create(data_hora=agora + timedelta(days=7), grau=1, defaults={"tipo": "ordinaria", "local": "Templo", "pauta": "1. Abertura\n2. Expediente\n3. Ordem do dia\n4. Encerramento"})
        self.stdout.write(self.style.WARNING(f"Usuários de demonstração criados (senha: {senha}). Não use em produção."))
