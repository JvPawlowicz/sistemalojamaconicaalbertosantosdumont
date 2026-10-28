import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core import perfis as P


class Votacao(models.Model):
    """Votação ou escrutínio sigiloso.

    Sigilo: o *voto* (``Voto``) não guarda usuário nem data/hora; a *participação* (``Participacao``) registra apenas
    QUEM votou, nunca COMO. O resultado só é divulgado ao encerrar.
    """

    class Tipo(models.TextChoices):
        ESCRUTINIO = "escrutinio", "Escrutínio de candidato"
        GERAL = "geral", "Votação geral"

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Preparação"
        ABERTA = "aberta", "Aberta"
        ENCERRADA = "encerrada", "Encerrada"

    titulo = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.GERAL)
    sessao = models.ForeignKey("sessoes.Sessao", null=True, blank=True, on_delete=models.SET_NULL, related_name="votacoes")
    candidato = models.ForeignKey("candidatos.Candidato", null=True, blank=True, on_delete=models.SET_NULL, related_name="votacoes")
    grau_minimo = models.PositiveSmallIntegerField("Grau mínimo para votar", choices=P.GRAU_CHOICES, default=P.MESTRE)
    exigir_presenca = models.BooleanField("Só vota quem está presente na sessão", default=True)
    negativos_maximos = models.PositiveSmallIntegerField(
        "Votos contrários que ainda permitem aprovação", default=0,
        help_text="0 = unanimidade (um voto contrário rejeita). Em votação geral vale a maioria simples dos válidos.")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    aberta_em = models.DateTimeField(null=True, blank=True)
    encerrada_em = models.DateTimeField(null=True, blank=True)
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    resultado_aplicado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Votação"
        verbose_name_plural = "Votações"

    def __str__(self):
        return self.titulo

    def eleitores(self):
        """Irmãos habilitados a votar agora."""
        from apps.irmaos.models import Irmao

        qs = Irmao.objects.filter(is_active=True, grau__gte=self.grau_minimo, situacao__in=["ativo", "remido"])
        if self.exigir_presenca and self.sessao_id:
            qs = qs.filter(presencas__sessao_id=self.sessao_id, presencas__situacao="presente")
        return qs.distinct()

    def pode_votar(self, user):
        if self.status != self.Status.ABERTA or user.grau is None:
            return False, "A votação não está aberta."
        if not user.pode_ver_grau(self.grau_minimo):
            return False, "Você não tem grau para participar desta votação."
        if self.exigir_presenca and self.sessao_id and not user.presencas.filter(
                sessao_id=self.sessao_id, situacao="presente").exists():
            return False, "Só vota quem tem a presença registrada na sessão."
        if self.participacoes.filter(irmao=user).exists():
            return False, "Você já votou."
        return True, ""

    def apuracao(self):
        """Totais e resultado. Só deve ser exibida após o encerramento."""
        v = self.votos
        sim, nao, abst = (v.filter(opcao=o).count() for o in ("sim", "nao", "abstencao"))
        if self.tipo == self.Tipo.ESCRUTINIO:
            aprovada = nao <= self.negativos_maximos and sim > 0
        else:
            aprovada = sim > nao
        return {"sim": sim, "nao": nao, "abstencao": abst, "total": sim + nao + abst, "aprovada": aprovada,
                "participantes": self.participacoes.count(), "habilitados": self.eleitores().count()}


class Participacao(models.Model):
    """Quem votou (nunca como votou)."""

    votacao = models.ForeignKey(Votacao, on_delete=models.CASCADE, related_name="participacoes")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = [("votacao", "irmao")]


class Voto(models.Model):
    """O voto em si: sem usuário, sem data/hora e com identificador aleatório."""

    OPCOES = [("sim", "Favorável"), ("nao", "Contrário"), ("abstencao", "Abstenção")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    votacao = models.ForeignKey(Votacao, on_delete=models.CASCADE, related_name="votos")
    opcao = models.CharField(max_length=10, choices=OPCOES)
