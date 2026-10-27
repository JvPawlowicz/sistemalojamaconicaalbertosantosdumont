from django.conf import settings
from django.db import models

from apps.core import perfis as P


class Documento(models.Model):
    class Categoria(models.TextChoices):
        REGIMENTO = "regimento", "Regimento e estatuto"
        BIBLIOTECA = "biblioteca", "Biblioteca"
        PRANCHA = "prancha", "Prancha / trabalho"
        RITUAL = "ritual", "Ritual e instrução"
        CERTIFICADO = "certificado", "Certificado / diploma"
        OUTRO = "outro", "Outro"

    titulo = models.CharField(max_length=150)
    categoria = models.CharField(max_length=12, choices=Categoria.choices, default=Categoria.BIBLIOTECA)
    descricao = models.TextField(blank=True)
    arquivo = models.FileField(upload_to="documentos/")
    grau_minimo = models.PositiveSmallIntegerField(
        "Grau mínimo para acessar", choices=P.GRAU_CHOICES, default=P.APRENDIZ
    )
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["categoria", "titulo"]

    def __str__(self):
        return self.titulo

    @property
    def extensao(self):
        return self.arquivo.name.rsplit(".", 1)[-1].lower() if "." in self.arquivo.name else ""

    @property
    def eh_pdf(self):
        return self.extensao == "pdf"

    @property
    def eh_imagem(self):
        return self.extensao in ("png", "jpg", "jpeg", "gif", "webp")
