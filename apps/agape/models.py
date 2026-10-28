"""Ágape (confraternização após a sessão): caixa próprio, subpresença e inventário de bebidas.

O caixa do Ágape nunca se mistura com o da loja. Só os irmãos que vão ao Ágape pagam o rateio;
o custo dos visitantes é da loja e entra no caixa do Ágape como repasse (e sai do caixa da loja).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from simple_history.models import HistoricalRecords


class Agape(models.Model):
    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        ENCERRADO = "encerrado", "Encerrado"

    sessao = models.OneToOneField("sessoes.Sessao", null=True, blank=True, on_delete=models.SET_NULL, related_name="agape")
    data = models.DateField()
    descricao = models.CharField(max_length=150, default="Ágape")
    valor_por_pessoa = models.DecimalField("Valor por pessoa", max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTO)
    repasse = models.OneToOneField("AgapeLancamento", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", editable=False)
    observacao = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data"]
        verbose_name = "Ágape"
        verbose_name_plural = "Ágapes"

    def __str__(self):
        return f"{self.descricao} de {self.data:%d/%m/%Y}"

    @property
    def aberto(self):
        return self.status == self.Status.ABERTO

    @property
    def vao(self):
        return self.participantes.filter(vai=True)

    @property
    def n_irmaos(self):
        return self.vao.count()

    @property
    def n_visitantes(self):
        return self.visitantes.count()

    @property
    def custo_visitantes(self):
        return self.valor_por_pessoa * self.n_visitantes

    @property
    def a_receber(self):
        return self.valor_por_pessoa * self.vao.filter(pago=False).count()

    @property
    def total_pessoas(self):
        return self.n_irmaos + self.n_visitantes


class Participante(models.Model):
    """Subpresença: quem vai (ou não vai) ao Ágape — nem todo irmão participa."""

    agape = models.ForeignKey(Agape, on_delete=models.CASCADE, related_name="participantes")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agapes")
    vai = models.BooleanField("Vai ao Ágape", default=True)
    pago = models.BooleanField(default=False)
    pago_em = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("agape", "irmao")]
        ordering = ["irmao__nome_completo"]


class Visitante(models.Model):
    """Visitante do Ágape — a loja arca com o custo."""

    agape = models.ForeignKey(Agape, on_delete=models.CASCADE, related_name="visitantes")
    nome = models.CharField(max_length=150)
    loja = models.CharField("Loja de origem", max_length=150, blank=True)

    class Meta:
        ordering = ["nome"]


class AgapeLancamento(models.Model):
    """Caixa próprio do Ágape (independente do caixa da tesouraria da loja)."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    class Categoria(models.TextChoices):
        RATEIO = "rateio", "Rateio dos irmãos"
        REPASSE = "repasse", "Repasse da loja (visitantes)"
        COMPRA = "compra", "Compra / insumos"
        BEBIDA = "bebida", "Bebidas"
        OUTRO = "outro", "Outro"

    agape = models.ForeignKey(Agape, null=True, blank=True, on_delete=models.SET_NULL, related_name="lancamentos")
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    categoria = models.CharField(max_length=8, choices=Categoria.choices, default=Categoria.OUTRO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    descricao = models.CharField(max_length=200)
    participante = models.OneToOneField(Participante, null=True, blank=True, on_delete=models.CASCADE, related_name="lancamento")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "Lançamento do caixa do Ágape"
        verbose_name_plural = "Caixa do Ágape"

    @property
    def valor_assinado(self):
        return self.valor if self.tipo == self.Tipo.ENTRADA else -self.valor

    @classmethod
    def saldo(cls):
        e = cls.objects.filter(tipo="entrada").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        s = cls.objects.filter(tipo="saida").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        return e - s


class Item(models.Model):
    """Item do inventário do Ágape (refrigerantes, cervejas, descartáveis…)."""

    nome = models.CharField(max_length=100, unique=True)
    unidade = models.CharField(max_length=20, default="un")
    minimo = models.PositiveIntegerField("Estoque mínimo", default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Item do inventário"
        verbose_name_plural = "Inventário do Ágape"

    def __str__(self):
        return self.nome

    @property
    def estoque(self):
        return self.movimentos.aggregate(s=Sum("quantidade"))["s"] or 0

    @property
    def baixo(self):
        return self.ativo and self.estoque <= self.minimo


class Movimento(models.Model):
    """Quantidade com sinal: entrada (+), consumo/perda (−) ou ajuste de contagem (±)."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada (compra/doação)"
        CONSUMO = "consumo", "Consumo no Ágape"
        PERDA = "perda", "Perda / quebra"
        AJUSTE = "ajuste", "Ajuste de contagem"

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="movimentos")
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    quantidade = models.IntegerField()
    data = models.DateField()
    agape = models.ForeignKey(Agape, null=True, blank=True, on_delete=models.SET_NULL, related_name="movimentos_estoque")
    observacao = models.CharField(max_length=200, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-data", "-id"]
