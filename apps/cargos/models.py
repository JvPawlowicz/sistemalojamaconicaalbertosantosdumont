from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import AnoMaconico


class Cargo(models.Model):
    """Catálogo de cargos da Loja (configurável; o Rito Schröder tem quadro reduzido)."""

    nome = models.CharField(max_length=80, unique=True)
    sigla = models.CharField(max_length=10, blank=True)
    ordem = models.PositiveSmallIntegerField(default=100, help_text="Ordem de exibição no quadro")
    descricao = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class Gestao(models.Model):
    """Titular de um cargo em um ano maçônico."""

    ano = models.ForeignKey(AnoMaconico, on_delete=models.CASCADE, related_name="gestao")
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name="titulares")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cargos")
    history = HistoricalRecords()

    class Meta:
        unique_together = [("ano", "cargo")]
        ordering = ["ano__inicio", "cargo__ordem"]
        verbose_name = "Gestão"
        verbose_name_plural = "Gestões"

    def __str__(self):
        return f"{self.cargo} {self.ano}: {self.irmao}"
