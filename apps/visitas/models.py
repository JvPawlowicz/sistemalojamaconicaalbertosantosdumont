from django.conf import settings
from django.db import models

from apps.core import perfis as P
from apps.core.models import AssinaturaBase
from apps.sessoes.models import Sessao


class VisitaRealizada(models.Model):
    """Visita de um irmão nosso a outra loja (certificado escaneado e vinculado)."""

    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visitas")
    loja_nome = models.CharField("Loja visitada", max_length=150)
    loja_numero = models.CharField("Nº", max_length=20, blank=True)
    oriente = models.CharField(max_length=100, blank=True)
    potencia = models.CharField("Potência", max_length=150, blank=True)
    data = models.DateField("Data da sessão")
    grau_sessao = models.PositiveSmallIntegerField("Grau da sessão", choices=P.GRAU_CHOICES, null=True, blank=True)
    certificado = models.FileField("Certificado (PDF ou imagem)", upload_to="certificados_recebidos/", blank=True)
    observacao = models.CharField(max_length=200, blank=True)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-data"]
        verbose_name = "Visita realizada"
        verbose_name_plural = "Visitas realizadas"


class Visitante(models.Model):
    """Banco de visitantes recebidos (reaproveitado em visitas futuras)."""

    nome = models.CharField(max_length=150)
    grau = models.PositiveSmallIntegerField(choices=P.GRAU_CHOICES, default=P.MESTRE)
    loja_nome = models.CharField("Loja", max_length=150)
    loja_numero = models.CharField("Nº", max_length=20, blank=True)
    oriente = models.CharField(max_length=100, blank=True)
    potencia = models.CharField("Potência", max_length=150, blank=True)
    registro = models.CharField("Matrícula/registro", max_length=40, blank=True)
    email = models.EmailField(blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} — {self.loja_nome}"


class VisitaRecebida(models.Model):
    sessao = models.ForeignKey(Sessao, on_delete=models.CASCADE, related_name="visitantes")
    visitante = models.ForeignKey(Visitante, on_delete=models.PROTECT, related_name="visitas")
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("sessao", "visitante")]
        ordering = ["visitante__nome"]
        verbose_name = "Visita recebida"
        verbose_name_plural = "Visitas recebidas"


class CertificadoVisita(models.Model):
    class Status(models.TextChoices):
        GERADO = "gerado", "Gerado"
        PARCIAL = "parcial", "Assinado em parte"
        ASSINADO = "assinado", "Assinado"
        ENVIADO = "enviado", "Enviado"
        FALHA = "falha", "Falha no envio"

    visita = models.OneToOneField(VisitaRecebida, on_delete=models.CASCADE, related_name="certificado")
    codigo = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.GERADO)
    enviado_em = models.DateTimeField(null=True, blank=True)
    envio_obs = models.CharField(max_length=300, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    @property
    def texto_canonico(self):
        v = self.visita
        return "\n".join([
            "certificado-visita", self.codigo, v.visitante.nome, str(v.visitante.grau), v.visitante.loja_nome,
            v.visitante.loja_numero, v.visitante.oriente, v.sessao.data_hora.date().isoformat(), str(v.sessao.grau),
        ])

    @property
    def hash_documento(self):
        from apps.core.utils import sha256_texto

        return sha256_texto(self.texto_canonico)


class AssinaturaCertificado(AssinaturaBase):
    certificado = models.ForeignKey(CertificadoVisita, on_delete=models.CASCADE, related_name="assinaturas")
    funcao = models.CharField(max_length=20)  # veneravel | secretario

    class Meta(AssinaturaBase.Meta):
        unique_together = [("certificado", "funcao")]
