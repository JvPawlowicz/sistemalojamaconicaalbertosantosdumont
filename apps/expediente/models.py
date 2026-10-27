from django.conf import settings
from django.db import models

from apps.core import perfis as P


class Correspondencia(models.Model):
    class Tipo(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        ENVIADA = "enviada", "Enviada"

    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    data = models.DateField()
    assunto = models.CharField(max_length=200)
    origem_destino = models.CharField("Remetente / destinatário", max_length=150)
    descricao = models.TextField(blank=True)
    arquivo = models.FileField(upload_to="expediente/", blank=True)
    grau_minimo = models.PositiveSmallIntegerField(choices=P.GRAU_CHOICES, default=P.MESTRE)
    leva_a_sessao = models.BooleanField("Ler no expediente da próxima sessão", default=True)
    lida_em_sessao = models.ForeignKey(
        "sessoes.Sessao", null=True, blank=True, on_delete=models.SET_NULL, related_name="expedientes"
    )
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "Correspondência"
        verbose_name_plural = "Expediente"

    def __str__(self):
        return self.assunto
