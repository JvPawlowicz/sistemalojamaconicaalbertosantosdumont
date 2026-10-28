from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class CasoHospitalaria(models.Model):
    """Acompanhamento sigiloso de irmão (ou familiar) em situação de saúde, luto ou dificuldade."""

    class Tipo(models.TextChoices):
        SAUDE = "saude", "Saúde / internação"
        LUTO = "luto", "Luto"
        DIFICULDADE = "dificuldade", "Dificuldade financeira"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        ACOMPANHANDO = "acompanhando", "Em acompanhamento"
        ENCERRADO = "encerrado", "Encerrado"

    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    beneficiado = models.CharField("Beneficiado (se não for irmão)", max_length=150, blank=True)
    parentesco = models.CharField(max_length=60, blank=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.SAUDE)
    descricao = models.TextField("Situação (sigilosa)")
    data_inicio = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACOMPANHANDO)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+", verbose_name="Irmão responsável pelo contato")
    encerrado_em = models.DateField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["status", "-data_inicio"]
        verbose_name = "Caso de hospitalaria"
        verbose_name_plural = "Casos de hospitalaria"

    def __str__(self):
        return self.nome

    @property
    def nome(self):
        return self.irmao.nome_completo if self.irmao_id else (self.beneficiado or "—")

    @property
    def ultimo_contato(self):
        a = self.acompanhamentos.first()
        return a.data if a else self.data_inicio


class Acompanhamento(models.Model):
    class Tipo(models.TextChoices):
        VISITA = "visita", "Visita"
        LIGACAO = "ligacao", "Ligação / mensagem"
        AJUDA = "ajuda", "Ajuda prestada"
        OUTRO = "outro", "Outro"

    caso = models.ForeignKey(CasoHospitalaria, on_delete=models.CASCADE, related_name="acompanhamentos")
    data = models.DateField()
    tipo = models.CharField(max_length=8, choices=Tipo.choices, default=Tipo.VISITA)
    descricao = models.TextField(blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-data", "-id"]


class MovimentoTronco(models.Model):
    """Tronco de Beneficência: arrecadações (geralmente nas sessões) e destinações."""

    class Tipo(models.TextChoices):
        ARRECADACAO = "arrecadacao", "Arrecadação"
        DESTINACAO = "destinacao", "Destinação"

    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    descricao = models.CharField(max_length=200, blank=True)
    sessao = models.ForeignKey("sessoes.Sessao", null=True, blank=True, on_delete=models.SET_NULL, related_name="tronco")
    caso = models.ForeignKey(CasoHospitalaria, null=True, blank=True, on_delete=models.SET_NULL, related_name="movimentos")
    comprovante = models.FileField(upload_to="tronco/", blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "Movimento do Tronco"
        verbose_name_plural = "Tronco de Beneficência"

    @property
    def valor_assinado(self):
        return self.valor if self.tipo == self.Tipo.ARRECADACAO else -self.valor

    @classmethod
    def saldo(cls):
        from decimal import Decimal

        from django.db.models import Sum

        a = cls.objects.filter(tipo="arrecadacao").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        d = cls.objects.filter(tipo="destinacao").aggregate(s=Sum("valor"))["s"] or Decimal(0)
        return a - d
