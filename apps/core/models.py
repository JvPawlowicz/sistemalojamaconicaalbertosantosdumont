from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .utils import ano_maconico_de, sha256_texto

TEXTO_LEGAL_PADRAO = (
    "Assinatura eletrônica avançada, válida nos termos do art. 10, §2º, da Medida Provisória "
    "nº 2.200-2/2001 e do art. 4º, II, da Lei nº 14.063/2020, mediante aceite prévio das partes. "
    "Autoria e integridade comprovadas por hash SHA-256, identificação do usuário autenticado com "
    "2FA, IP, data/hora e geolocalização registrados."
)

TERMO_PADRAO = (
    "Declaro que li e aceito que as minhas assinaturas eletrônicas realizadas neste sistema "
    "(atas, certificados e demais documentos) sejam consideradas válidas e vinculantes para a Loja, "
    "como assinatura eletrônica avançada, nos termos do art. 10, §2º, da MP 2.200-2/2001 e do art. 4º, II, "
    "da Lei 14.063/2020. Estou ciente de que, a cada assinatura, serão registrados o meu usuário, o "
    "desenho da assinatura, o endereço IP, o dispositivo, a data e a hora, a geolocalização (quando "
    "autorizada no navegador) e o hash do documento, para comprovar autoria e integridade, conforme a "
    "política de privacidade (LGPD)."
)


class Loja(models.Model):
    """Configuração única da Loja (registro singleton)."""

    nome = models.CharField("Nome da Loja", max_length=150, default="Loja Maçônica Alberto Santos Dumont")
    numero = models.CharField("Número", max_length=20, blank=True)
    oriente = models.CharField("Oriente", max_length=100, blank=True)
    potencia = models.CharField(
        "Potência", max_length=150, default="Grande Loja Maçônica do Estado de São Paulo"
    )
    rito = models.CharField("Rito", max_length=60, default="Schröder")
    cnpj = models.CharField("CNPJ", max_length=18, blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    email_contato = models.EmailField("E-mail de contato", blank=True)
    brasao = models.ImageField("Brasão", upload_to="loja/", blank=True)
    cabecalho_documentos = models.TextField(
        "Cabeçalho dos documentos",
        blank=True,
        help_text="Texto impresso no topo de atas e certificados. Em branco, usa o nome, número e oriente.",
    )
    texto_legal = models.TextField("Fundamentação legal da assinatura", default=TEXTO_LEGAL_PADRAO)
    mensalidade_dia_vencimento = models.PositiveSmallIntegerField("Dia de vencimento da mensalidade", default=10)
    chave_pix = models.CharField("Chave PIX (para cobrança)", max_length=120, blank=True)
    intersticio_promocao_meses = models.PositiveSmallIntegerField(
        "Interstício mínimo: iniciação → promoção (meses)", default=0, help_text="0 = sem exigência")
    intersticio_elevacao_meses = models.PositiveSmallIntegerField(
        "Interstício mínimo: promoção → elevação (meses)", default=0, help_text="0 = sem exigência")
    lembrete_sessao_horas = models.PositiveSmallIntegerField(
        "Lembrete automático de sessão (horas antes)", default=48, help_text="0 = desligado")
    # Regras do regimento interno (0 = não aplicar)
    limite_faltas_consecutivas = models.PositiveSmallIntegerField(
        "Limite de faltas consecutivas não justificadas", default=0, help_text="0 = sem alerta")
    frequencia_minima_percentual = models.PositiveSmallIntegerField(
        "Frequência mínima no ano maçônico (%)", default=0, help_text="0 = sem alerta")
    quorum_minimo = models.PositiveSmallIntegerField(
        "Quórum mínimo para abrir a sessão (irmãos presentes)", default=0, help_text="0 = sem exigência")
    multa_atraso_percentual = models.DecimalField(
        "Multa por atraso (%)", max_digits=5, decimal_places=2, default=0, help_text="Aplicada uma vez após o vencimento")
    juros_mensal_percentual = models.DecimalField(
        "Juros por mês de atraso (%)", max_digits=5, decimal_places=2, default=0, help_text="Pro rata por dia de atraso")
    dias_carencia_atraso = models.PositiveSmallIntegerField("Dias de carência antes de multa/juros", default=0)
    cobranca_automatica = models.BooleanField(
        "Enviar cobrança por e-mail automaticamente às mensalidades vencidas (semanal)", default=False)

    class Meta:
        verbose_name = "Loja"
        verbose_name_plural = "Loja"

    def __str__(self):
        return self.nome

    @classmethod
    def atual(cls):
        obj = cls.objects.first()
        return obj or cls.objects.create()

    def save(self, *args, **kwargs):
        if not self.pk and Loja.objects.exists():
            raise ValidationError("Só pode existir uma configuração de Loja.")
        super().save(*args, **kwargs)

    @property
    def cabecalho(self):
        if self.cabecalho_documentos.strip():
            return self.cabecalho_documentos
        partes = [self.nome]
        if self.numero:
            partes[0] += f" nº {self.numero}"
        if self.oriente:
            partes.append(f"Oriente de {self.oriente}")
        partes.append(self.potencia)
        return "\n".join(partes)


class AnoMaconico(models.Model):
    nome = models.CharField(max_length=9, unique=True, help_text="Ex.: 2025/2026")
    inicio = models.DateField()
    fim = models.DateField()

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Ano maçônico"
        verbose_name_plural = "Anos maçônicos"

    def __str__(self):
        return self.nome

    @classmethod
    def para_data(cls, data):
        """Devolve (criando se preciso) o ano maçônico que contém a data."""
        inicio, fim, nome = ano_maconico_de(data)
        obj, _ = cls.objects.get_or_create(nome=nome, defaults={"inicio": inicio, "fim": fim})
        return obj

    @classmethod
    def atual(cls):
        return cls.para_data(timezone.localdate())

    @classmethod
    def seguinte(cls, ano):
        from datetime import timedelta

        return cls.para_data(ano.fim + timedelta(days=1))

    def contem(self, data):
        return self.inicio <= data <= self.fim

    @property
    def meses(self):
        """Primeiro dia de cada um dos 12 meses do ano maçônico."""
        from datetime import date

        return [
            date(self.inicio.year + (self.inicio.month - 1 + i) // 12, (self.inicio.month - 1 + i) % 12 + 1, 1)
            for i in range(12)
        ]


class TermoAceite(models.Model):
    """Termo que cada irmão aceita para validar suas assinaturas eletrônicas."""

    versao = models.PositiveIntegerField(unique=True)
    texto = models.TextField(default=TERMO_PADRAO)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-versao"]

    def __str__(self):
        return f"Termo v{self.versao}"

    @property
    def hash(self):
        return sha256_texto(self.texto)

    @classmethod
    def vigente(cls):
        return cls.objects.filter(ativo=True).order_by("-versao").first()


class AceiteTermo(models.Model):
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aceites")
    termo = models.ForeignKey(TermoAceite, on_delete=models.PROTECT, related_name="aceites")
    hash_termo = models.CharField(max_length=64)
    aceito_em = models.DateTimeField(default=timezone.now)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = [("irmao", "termo")]
        ordering = ["-aceito_em"]


class EmailLog(models.Model):
    """Registro de e-mails enviados pelo sistema (entregas e falhas)."""

    destinatario = models.EmailField()
    assunto = models.CharField(max_length=200)
    contexto = models.CharField(max_length=60, blank=True)
    enviado = models.BooleanField(default=False)
    erro = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class AssinaturaBase(models.Model):
    """Evidências de uma assinatura eletrônica avançada (usada por atas e certificados)."""

    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    imagem = models.TextField("Desenho da assinatura (PNG base64)", blank=True)
    foto = models.ImageField("Foto da assinatura (opcional)", upload_to="assinaturas/", blank=True)
    hash_documento = models.CharField(max_length=64)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    precisao_m = models.PositiveIntegerField(null=True, blank=True)
    autenticacao_2fa = models.BooleanField(default=False)
    assinado_em = models.DateTimeField(default=timezone.now)
    codigo = models.CharField(max_length=20, unique=True)
    hash_assinatura = models.CharField(max_length=64)
    aceite = models.ForeignKey(AceiteTermo, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    texto_legal = models.TextField(blank=True)

    class Meta:
        abstract = True
        ordering = ["assinado_em"]

    @property
    def imagem_src(self):
        """Imagem da assinatura como data URI (desenho ou foto), para embutir em PDFs."""
        if self.imagem:
            return self.imagem
        if self.foto:
            import base64
            import mimetypes

            try:
                with self.foto.open("rb") as f:
                    dados = f.read()
            except FileNotFoundError:
                return ""
            tipo = mimetypes.guess_type(self.foto.name)[0] or "image/png"
            return f"data:{tipo};base64," + base64.b64encode(dados).decode()
        return ""


class SolicitacaoLGPD(models.Model):
    """Pedido de titular de dados (acesso, correção, eliminação, portabilidade)."""

    class Tipo(models.TextChoices):
        ACESSO = "acesso", "Acesso aos meus dados"
        CORRECAO = "correcao", "Correção de dados"
        ELIMINACAO = "eliminacao", "Eliminação de dados"
        PORTABILIDADE = "portabilidade", "Portabilidade"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        ATENDIDA = "atendida", "Atendida"
        NEGADA = "negada", "Negada (com justificativa)"

    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitacoes_lgpd")
    tipo = models.CharField(max_length=14, choices=Tipo.choices)
    mensagem = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    resposta = models.TextField(blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    resolvida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "Solicitação LGPD"
        verbose_name_plural = "Solicitações LGPD"


class Aviso(models.Model):
    """Mural de avisos da Loja, por grau, com opção de fixar e de expirar."""

    titulo = models.CharField(max_length=150)
    texto = models.TextField()
    grau_minimo = models.PositiveSmallIntegerField("Visível a partir do grau", default=1,
                                                   choices=[(1, "Aprendiz"), (2, "Companheiro"), (3, "Mestre")])
    fixado = models.BooleanField(default=False)
    publicar_em = models.DateTimeField(default=timezone.now)
    expira_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    enviado_por_email_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fixado", "-publicar_em"]

    def __str__(self):
        return self.titulo

    @classmethod
    def vigentes_para(cls, user):
        agora = timezone.now()
        qs = cls.objects.filter(publicar_em__lte=agora).filter(models.Q(expira_em__isnull=True) | models.Q(expira_em__gt=agora))
        return [a for a in qs if user.pode_ver_grau(a.grau_minimo)]
