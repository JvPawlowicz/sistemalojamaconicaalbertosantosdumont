from django.conf import settings
from django.db import models

from apps.core.models import AnoMaconico


class Comissao(models.Model):
    class Tipo(models.TextChoices):
        SINDICANCIA = "sindicancia", "Sindicância"
        CONSELHO_FISCAL = "conselho_fiscal", "Conselho Fiscal"
        AUDITORIA = "auditoria", "Auditoria"
        EVENTOS = "eventos", "Eventos"
        OUTRA = "outra", "Outra"

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=16, choices=Tipo.choices, default=Tipo.OUTRA)
    ano = models.ForeignKey(AnoMaconico, on_delete=models.PROTECT, related_name="comissoes")
    objetivo = models.TextField(blank=True)
    prazo = models.DateField(null=True, blank=True)
    encerrada = models.BooleanField(default=False)
    parecer = models.TextField(blank=True)
    parecer_em = models.DateField(null=True, blank=True)
    candidato = models.ForeignKey(
        "candidatos.Candidato", null=True, blank=True, on_delete=models.SET_NULL, related_name="comissoes"
    )

    class Meta:
        ordering = ["-ano__inicio", "nome"]
        verbose_name = "Comissão"
        verbose_name_plural = "Comissões"

    def __str__(self):
        return self.nome


class MembroComissao(models.Model):
    comissao = models.ForeignKey(Comissao, on_delete=models.CASCADE, related_name="membros")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comissoes")
    papel = models.CharField(max_length=60, default="Membro")

    class Meta:
        unique_together = [("comissao", "irmao")]
