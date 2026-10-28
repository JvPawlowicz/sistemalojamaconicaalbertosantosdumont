from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import AssinaturaBase, Loja
from apps.core.utils import carimbo, sha256_texto
from apps.sessoes.models import Sessao


class AtaQuerySet(models.QuerySet):
    def visiveis_para(self, user):
        """Ata de sessão de grau X só é visível a irmãos de grau igual ou superior a X."""
        if user.eh_desenvolvedor:
            return self
        if user.grau is None:
            return self.none()
        return self.filter(sessao__grau__lte=user.grau)

    def pendentes_de(self, user):
        """Atas aprovadas em que o usuário é signatário e ainda não assinou a versão atual."""
        qs = self.filter(status=Ata.Status.APROVADA, signatarios__irmao=user).distinct()
        return [a for a in qs if not a.assinaturas.filter(irmao=user, versao=a.versao).exists()]


class Ata(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CIRCULACAO = "circulacao", "Em circulação para aprovação"
        APROVADA = "aprovada", "Aprovada — aguardando assinaturas"
        ASSINADA = "assinada", "Assinada"

    sessao = models.OneToOneField(Sessao, on_delete=models.PROTECT, related_name="ata")
    numero = models.PositiveIntegerField("Nº da ata", null=True, blank=True)
    livro = models.CharField("Livro", max_length=20, blank=True)
    folha = models.CharField("Folha", max_length=20, blank=True)
    conteudo = models.TextField("Texto da ata")
    formato = models.CharField(max_length=5, choices=[("texto", "Texto simples"), ("html", "Texto formatado")], default="html")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    versao = models.PositiveIntegerField(default=1)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    aprovada_em = models.DateTimeField(null=True, blank=True)
    circulacao_enviada_em = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()
    objects = AtaQuerySet.as_manager()

    class Meta:
        ordering = ["-sessao__data_hora"]

    def __str__(self):
        return f"Ata {self.numero or 's/nº'} — {self.sessao}"

    @property
    def conteudo_html(self):
        from .sanitizar import renderizar

        return renderizar(self)

    @property
    def texto(self):
        """Conteúdo como texto puro (comparação de versões, busca, e-mails)."""
        from .sanitizar import texto_simples

        return texto_simples(self.conteudo) if self.formato == "html" else self.conteudo

    @property
    def editavel(self):
        return self.status in (self.Status.RASCUNHO, self.Status.CIRCULACAO)

    @property
    def assinaturas_validas(self):
        return self.assinaturas.filter(versao=self.versao)

    def texto_canonico(self):
        s = self.sessao
        return "\n".join([
            Loja.atual().nome, f"ata:{self.numero or ''}", f"livro:{self.livro}", f"folha:{self.folha}",
            f"sessao:{carimbo(s.data_hora)}", f"grau:{s.grau}", f"tipo:{s.tipo}", f"versao:{self.versao}",
            self.conteudo.strip(),
        ])

    @property
    def hash_conteudo(self):
        return sha256_texto(self.texto_canonico())

    def arquivar_versao(self, usuario=None):
        """Guarda o retrato da versão atual (idempotente)."""
        return AtaVersao.objects.get_or_create(ata=self, versao=self.versao, defaults={
            "conteudo": self.conteudo, "formato": self.formato, "texto_canonico": self.texto_canonico(),
            "hash": self.hash_conteudo,
            "criada_por": usuario})[0]

    def faltam_assinar(self):
        assinaram = set(self.assinaturas_validas.values_list("irmao_id", flat=True))
        return [s for s in self.signatarios.select_related("irmao") if s.irmao_id not in assinaram]


class AtaVersao(models.Model):
    """Retrato imutável do texto de cada versão aprovada (permite comparar e verificar versões antigas)."""

    ata = models.ForeignKey(Ata, on_delete=models.CASCADE, related_name="versoes")
    versao = models.PositiveIntegerField()
    conteudo = models.TextField()
    formato = models.CharField(max_length=5, default="texto")
    texto_canonico = models.TextField()
    hash = models.CharField(max_length=64)
    criada_em = models.DateTimeField(auto_now_add=True)
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = [("ata", "versao")]
        ordering = ["versao"]


class AtaSignatario(models.Model):
    ata = models.ForeignKey(Ata, on_delete=models.CASCADE, related_name="signatarios")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    funcao = models.CharField("Função", max_length=60, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    ultimo_aviso_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("ata", "irmao")]
        ordering = ["ordem", "id"]


class AssinaturaAta(AssinaturaBase):
    ata = models.ForeignKey(Ata, on_delete=models.CASCADE, related_name="assinaturas")
    versao = models.PositiveIntegerField()

    class Meta(AssinaturaBase.Meta):
        unique_together = [("ata", "irmao", "versao")]


class ModeloTexto(models.Model):
    """Texto pré-cadastrado inserido na ata digitando @."""

    class Categoria(models.TextChoices):
        CABECALHO = "cabecalho", "Cabeçalho"
        ABERTURA = "abertura", "Abertura"
        EXPEDIENTE = "expediente", "Expediente"
        ORDEM_DO_DIA = "ordem_do_dia", "Ordem do dia"
        ENCERRAMENTO = "encerramento", "Encerramento"
        FORMULA = "formula", "Fórmula / frase padrão"
        OUTRO = "outro", "Outro"

    titulo = models.CharField(max_length=100)
    atalho = models.SlugField("Atalho", max_length=40, unique=True, help_text="Ex.: abertura-ordinaria")
    categoria = models.CharField(max_length=14, choices=Categoria.choices, default=Categoria.FORMULA)
    texto = models.TextField(help_text="Variáveis: {{data}}, {{data_extenso}}, {{hora}}, {{grau}}, {{tipo}}, "
                             "{{local}}, {{ano_maconico}}, {{loja}}, {{numero_loja}}, {{oriente}}, "
                             "{{veneravel}}, {{secretario}}, {{presentes}}, {{visitantes}}")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria", "titulo"]
        verbose_name = "Modelo de texto"
        verbose_name_plural = "Modelos de texto"

    def __str__(self):
        return self.titulo
