from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import AnoMaconico


class CategoriaFinanceira(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    nome = models.CharField(max_length=80)
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nome"]
        unique_together = [("nome", "tipo")]
        verbose_name = "Categoria financeira"
        verbose_name_plural = "Categorias financeiras"

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Lancamento(models.Model):
    """Mensalidade/contribuição de um irmão em uma competência."""

    class Status(models.TextChoices):
        PREVISTO = "previsto", "Previsto"
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"
        VENCIDO = "vencido", "Vencido"
        ISENTO = "isento", "Isento"
        DISPENSADO = "dispensado", "Dispensado"

    class Forma(models.TextChoices):
        PIX = "pix", "PIX"
        BOLETO = "boleto", "Boleto"
        DINHEIRO = "dinheiro", "Dinheiro"
        TRANSFERENCIA = "transferencia", "Transferência"
        OUTRA = "outra", "Outra"

    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lancamentos")
    competencia = models.DateField("Competência (1º dia do mês)")
    descricao = models.CharField(max_length=120, default="Mensalidade")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    pago_em = models.DateField(null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    forma = models.CharField(max_length=14, choices=Forma.choices, blank=True)
    boleto = models.FileField("Boleto (arquivo)", upload_to="boletos/", blank=True)
    comprovante = models.FileField(upload_to="comprovantes/", blank=True)
    observacao = models.CharField(max_length=200, blank=True)
    baixa_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    ultima_cobranca_em = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-competencia", "irmao__nome_completo"]
        unique_together = [("irmao", "competencia", "descricao")]

    def __str__(self):
        return f"{self.descricao} {self.competencia:%m/%Y} — {self.irmao}"

    @property
    def em_aberto(self):
        return self.status in (self.Status.PENDENTE, self.Status.VENCIDO, self.Status.PREVISTO)


class MovimentoCaixa(models.Model):
    tipo = models.CharField(max_length=8, choices=CategoriaFinanceira.Tipo.choices)
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.PROTECT, related_name="movimentos")
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    descricao = models.CharField(max_length=200)
    comprovante = models.FileField(upload_to="comprovantes/", blank=True)
    lancamento = models.OneToOneField(Lancamento, null=True, blank=True, on_delete=models.SET_NULL, related_name="movimento")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "Movimento de caixa"
        verbose_name_plural = "Movimentos de caixa"

    @property
    def valor_assinado(self):
        return self.valor if self.tipo == CategoriaFinanceira.Tipo.RECEITA else -self.valor


class Orcamento(models.Model):
    ano = models.ForeignKey(AnoMaconico, on_delete=models.CASCADE, related_name="orcamentos")
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.PROTECT)
    valor_previsto = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("ano", "categoria")]
        verbose_name = "Orçamento"


class ExtratoImportado(models.Model):
    """Transações de extrato já conciliadas (evita dar baixa duas vezes no mesmo crédito)."""

    fitid = models.CharField(max_length=120, unique=True)
    data = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    descricao = models.CharField(max_length=250, blank=True)
    lancamento = models.ForeignKey(Lancamento, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    importado_em = models.DateTimeField(auto_now_add=True)
