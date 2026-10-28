from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from simple_history.models import HistoricalRecords

from apps.core import perfis as P

UF_CHOICES = [(u, u) for u in (
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)]

telefone_validator = RegexValidator(
    r"^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$", "Informe o telefone no formato (11) 91234-5678."
)
cep_validator = RegexValidator(r"^\d{5}-?\d{3}$", "Informe o CEP no formato 12345-678.")
cpf_validator = RegexValidator(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$", "Informe o CPF no formato 123.456.789-09.")


class CategoriaIrmao(models.Model):
    """Categoria de cobrança (integral, remido, etc.)."""

    nome = models.CharField(max_length=60, unique=True)
    valor_mensal = models.DecimalField("Valor mensal (R$)", max_digits=10, decimal_places=2, default=0)
    isento = models.BooleanField("Isento de mensalidade (ex.: remido)", default=False)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Categoria de irmão"
        verbose_name_plural = "Categorias de irmão"

    def __str__(self):
        return self.nome


class Irmao(AbstractUser):
    """Cada usuário do sistema é um irmão (exceto contas técnicas, sem grau)."""

    class Situacao(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        LICENCIADO = "licenciado", "Licenciado"
        REMIDO = "remido", "Remido"
        AFASTADO = "afastado", "Afastado"
        FALECIDO = "falecido", "Falecido"
        DESLIGADO = "desligado", "Desligado"

    # Maçônicos
    nome_completo = models.CharField(max_length=150)
    matricula = models.CharField("Matrícula na Potência", max_length=30, blank=True)
    grau = models.PositiveSmallIntegerField(choices=P.GRAU_CHOICES, null=True, blank=True)
    situacao = models.CharField(max_length=12, choices=Situacao.choices, default=Situacao.ATIVO)
    categoria = models.ForeignKey(CategoriaIrmao, null=True, blank=True, on_delete=models.PROTECT)
    data_iniciacao = models.DateField("Data de iniciação", null=True, blank=True)
    data_promocao = models.DateField("Data de promoção (a Companheiro)", null=True, blank=True)
    data_elevacao = models.DateField("Data de elevação (a Mestre)", null=True, blank=True)
    perfis = models.JSONField("Perfis", default=list, blank=True)
    codigo_carteirinha = models.CharField(max_length=16, blank=True, editable=False, db_index=True)
    aceita_whatsapp = models.BooleanField("Aceita receber avisos por WhatsApp", default=True)

    # Pessoais
    cpf = models.CharField("CPF", max_length=14, blank=True, validators=[cpf_validator])
    rg = models.CharField("RG", max_length=20, blank=True)
    data_nascimento = models.DateField("Data de nascimento", null=True, blank=True)
    telefone = models.CharField("Telefone", max_length=15, blank=True, validators=[telefone_validator])
    whatsapp = models.CharField("WhatsApp", max_length=15, blank=True, validators=[telefone_validator])
    foto = models.ImageField(upload_to="irmaos/", blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True, validators=[cep_validator])
    logradouro = models.CharField(max_length=150, blank=True)
    numero = models.CharField("Número", max_length=15, blank=True)
    complemento = models.CharField(max_length=60, blank=True)
    bairro = models.CharField(max_length=80, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    uf = models.CharField("UF", max_length=2, choices=UF_CHOICES, blank=True)
    contato_emergencia_nome = models.CharField("Contato de emergência", max_length=120, blank=True)
    contato_emergencia_telefone = models.CharField(
        "Telefone do contato de emergência", max_length=15, blank=True, validators=[telefone_validator]
    )

    # Profissionais
    formacao_academica = models.CharField("Formação acadêmica", max_length=150, blank=True)
    profissao = models.CharField("Profissão", max_length=100, blank=True)
    empresa = models.CharField("Empresa / atuação", max_length=120, blank=True)

    # Saúde e previdência (visibilidade restrita)
    plano_saude = models.CharField("Plano de saúde", max_length=120, blank=True)
    plano_funeral = models.CharField("Plano funeral", max_length=120, blank=True)

    REQUIRED_FIELDS = ["email", "nome_completo"]

    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    class Meta:
        ordering = ["nome_completo"]
        verbose_name = "Irmão"
        verbose_name_plural = "Irmãos"
        constraints = [
            models.CheckConstraint(
                condition=Q(grau__isnull=True) | Q(grau__in=[1, 2, 3]), name="irmao_grau_valido"
            )
        ]

    def __str__(self):
        return self.nome_completo or self.get_username()

    # --- perfis e graus ---
    @property
    def perfis_efetivos(self):
        perfis = set(self.perfis or [])
        if self.is_superuser:
            perfis.add(P.DESENVOLVEDOR)
        return P.expandir(perfis)

    def tem_perfil(self, perfil):
        return perfil in self.perfis_efetivos

    def tem_algum_perfil(self, *perfis):
        return bool(self.perfis_efetivos & set(perfis))

    @property
    def eh_desenvolvedor(self):
        return self.tem_perfil(P.DESENVOLVEDOR)

    def pode_ver_grau(self, grau_do_conteudo):
        """Conteúdo de grau X é visível para irmãos de grau igual ou superior a X."""
        if self.eh_desenvolvedor:
            return True
        return self.grau is not None and self.grau >= grau_do_conteudo

    @property
    def grau_nome(self):
        return P.GRAU_NOMES.get(self.grau, "—")

    @property
    def ativo_no_quadro(self):
        return self.is_active and self.situacao in (self.Situacao.ATIVO, self.Situacao.REMIDO)

    @property
    def iniciais(self):
        partes = (self.nome_completo or self.username).split()
        return "".join(p[0] for p in partes[:2]).upper()

    def save(self, *args, **kwargs):
        if not self.codigo_carteirinha:
            import secrets

            self.codigo_carteirinha = secrets.token_hex(6).upper()
        if not self.first_name and self.nome_completo:
            self.first_name = self.nome_completo.split()[0][:150]
        super().save(*args, **kwargs)


class Familiar(models.Model):
    class Parentesco(models.TextChoices):
        CONJUGE = "conjuge", "Esposa / cunhada"
        FILHO = "filho", "Filho"
        FILHA = "filha", "Filha"
        OUTRO = "outro", "Outro"

    irmao = models.ForeignKey(Irmao, on_delete=models.CASCADE, related_name="familiares")
    parentesco = models.CharField(max_length=10, choices=Parentesco.choices)
    nome = models.CharField(max_length=150)
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=15, blank=True, validators=[telefone_validator])

    class Meta:
        ordering = ["parentesco", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_parentesco_display()})"


class AniversarioEnviado(models.Model):
    """Registro dos e-mails de parabéns já enviados (impede envio em duplicidade no mesmo ano)."""

    irmao = models.ForeignKey(Irmao, on_delete=models.CASCADE, related_name="+")
    tipo = models.CharField(max_length=10)
    ano = models.PositiveSmallIntegerField()
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("irmao", "tipo", "ano")]
