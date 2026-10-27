from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.cargos.models import Cargo
from apps.core import perfis as P
from apps.core.models import AnoMaconico


class Sessao(models.Model):
    class Tipo(models.TextChoices):
        ORDINARIA = "ordinaria", "Ordinária"
        MAGNA = "magna", "Magna"
        ECONOMICA = "economica", "Econômica"
        INSTRUCAO = "instrucao", "Instrução"
        INICIACAO = "iniciacao", "Iniciação"
        PROMOCAO = "promocao", "Promoção"
        ELEVACAO = "elevacao", "Elevação"
        OUTRA = "outra", "Outra"

    class Status(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    ano = models.ForeignKey(AnoMaconico, on_delete=models.PROTECT, related_name="sessoes", editable=False)
    data_hora = models.DateTimeField("Data e hora")
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.ORDINARIA)
    grau = models.PositiveSmallIntegerField("Grau da sessão", choices=P.GRAU_CHOICES, default=P.APRENDIZ)
    local = models.CharField(max_length=150, blank=True)
    pauta = models.TextField(blank=True)
    expediente = models.TextField("Expediente do dia", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AGENDADA)
    observacoes = models.TextField(blank=True)
    convocacao_enviada_em = models.DateTimeField(null=True, blank=True)
    lembrete_enviado_em = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"

    def __str__(self):
        return f"Sessão {self.get_tipo_display()} de {self.get_grau_display()} — {self.data_hora:%d/%m/%Y}"

    def save(self, *args, **kwargs):
        self.ano = AnoMaconico.para_data(self.data_hora.date())
        super().save(*args, **kwargs)

    @property
    def titulo(self):
        return f"{self.get_tipo_display()} — Grau de {self.get_grau_display()}"

    def elegiveis(self):
        """Irmãos que podem participar: ativos e com grau igual ou superior ao da sessão."""
        from apps.irmaos.models import Irmao

        return Irmao.objects.filter(
            is_active=True, grau__gte=self.grau, situacao__in=[Irmao.Situacao.ATIVO, Irmao.Situacao.REMIDO]
        )


class Escala(models.Model):
    """Quem ocupa cada cargo em uma sessão (titular ou substituto)."""

    sessao = models.ForeignKey(Sessao, on_delete=models.CASCADE, related_name="escala")
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="escalas")
    substituicao = models.BooleanField(default=False)
    titular = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        unique_together = [("sessao", "cargo")]
        ordering = ["cargo__ordem"]


class Presenca(models.Model):
    class Situacao(models.TextChoices):
        PRESENTE = "presente", "Presente"
        JUSTIFICADA = "justificada", "Ausência justificada"
        AUSENTE = "ausente", "Ausente"

    sessao = models.ForeignKey(Sessao, on_delete=models.CASCADE, related_name="presencas")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="presencas")
    situacao = models.CharField(max_length=12, choices=Situacao.choices, default=Situacao.AUSENTE)
    justificativa = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("sessao", "irmao")]
        ordering = ["irmao__nome_completo"]


class Cerimonia(models.Model):
    """Iniciação, promoção ou elevação realizada em uma sessão (atualiza o grau do irmão)."""

    class Tipo(models.TextChoices):
        INICIACAO = "iniciacao", "Iniciação"
        PROMOCAO = "promocao", "Promoção"
        ELEVACAO = "elevacao", "Elevação"

    sessao = models.ForeignKey(Sessao, on_delete=models.PROTECT, related_name="cerimonias")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cerimonias")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    data = models.DateField()
    grau_resultante = models.PositiveSmallIntegerField(choices=P.GRAU_CHOICES)
    observacao = models.CharField(max_length=200, blank=True)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    forcada = models.BooleanField("Registrada apesar do interstício mínimo", default=False)

    class Meta:
        ordering = ["data", "id"]
        unique_together = [("irmao", "tipo")]
        verbose_name = "Cerimônia"
        verbose_name_plural = "Cerimônias"

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.irmao} em {self.data:%d/%m/%Y}"


class Evento(models.Model):
    """Agenda social da Loja (ágapes, confraternizações, instalações)."""

    class Tipo(models.TextChoices):
        AGAPE = "agape", "Ágape"
        SOCIAL = "social", "Confraternização"
        INSTALACAO = "instalacao", "Instalação / posse"
        BENEFICENTE = "beneficente", "Beneficente"
        OUTRO = "outro", "Outro"

    titulo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.AGAPE)
    data_hora = models.DateTimeField("Data e hora")
    local = models.CharField(max_length=150, blank=True)
    descricao = models.TextField(blank=True)
    valor_por_pessoa = models.DecimalField("Valor por pessoa (R$)", max_digits=8, decimal_places=2, null=True, blank=True)
    grau_minimo = models.PositiveSmallIntegerField("Visível a partir do grau", choices=P.GRAU_CHOICES, default=P.APRENDIZ)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["data_hora"]

    def __str__(self):
        return self.titulo

    @property
    def total_confirmados(self):
        return sum(1 + c.acompanhantes for c in self.confirmacoes.filter(resposta="sim"))


class ConfirmacaoEvento(models.Model):
    class Resposta(models.TextChoices):
        SIM = "sim", "Vou"
        NAO = "nao", "Não vou"
        TALVEZ = "talvez", "Talvez"

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="confirmacoes")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="confirmacoes")
    resposta = models.CharField(max_length=6, choices=Resposta.choices)
    acompanhantes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("evento", "irmao")]
