from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class Candidato(models.Model):
    class Etapa(models.TextChoices):
        PROPOSTO = "proposto", "Proposto"
        SINDICANCIA = "sindicancia", "Em sindicância"
        ESCRUTINIO = "escrutinio", "Escrutínio"
        APROVADO = "aprovado", "Aprovado"
        REPROVADO = "reprovado", "Reprovado"
        INICIADO = "iniciado", "Iniciado"
        DESISTIU = "desistiu", "Desistiu"

    nome = models.CharField(max_length=150)
    data_nascimento = models.DateField(null=True, blank=True)
    profissao = models.CharField(max_length=100, blank=True)
    telefone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    proposto_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="propostas")
    data_proposta = models.DateField()
    etapa = models.CharField(max_length=12, choices=Etapa.choices, default=Etapa.PROPOSTO)
    etapa_desde = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data_proposta"]

    def __str__(self):
        return self.nome


class Parecer(models.Model):
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, related_name="pareceres")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    data = models.DateField()
    favoravel = models.BooleanField("Parecer favorável", default=True)
    texto = models.TextField()

    class Meta:
        ordering = ["-data"]
