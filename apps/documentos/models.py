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
    texto_extraido = models.TextField(blank=True, editable=False)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["categoria", "titulo"]

    def __str__(self):
        return self.titulo

    def extrair_texto(self):
        """Lê o texto do PDF (para a busca). PDFs escaneados sem texto ficam só com a busca pelo título."""
        if not self.eh_pdf:
            return ""
        from pypdf import PdfReader

        try:
            self.arquivo.open("rb")
            try:
                leitor = PdfReader(self.arquivo)
                paginas = []
                for p in leitor.pages[:400]:
                    paginas.append(p.extract_text() or "")
            finally:
                self.arquivo.close()
        except Exception:  # noqa: BLE001 - PDF corrompido/protegido não deve impedir o envio
            return ""
        return " ".join(" ".join(paginas).split())[:1_000_000]

    def save(self, *args, **kwargs):
        novo_arquivo = self._state.adding or "arquivo" in (kwargs.get("update_fields") or ())
        super().save(*args, **kwargs)
        if novo_arquivo and self.eh_pdf and not self.texto_extraido:
            self.texto_extraido = self.extrair_texto()
            if self.texto_extraido:
                type(self).objects.filter(pk=self.pk).update(texto_extraido=self.texto_extraido)

    def trecho(self, termo, largura=70):
        """Trecho do texto do PDF em volta do termo buscado."""
        i = self.texto_extraido.lower().find(termo.lower())
        if i < 0:
            return ""
        ini = max(0, i - largura)
        return ("…" if ini else "") + self.texto_extraido[ini:i + len(termo) + largura] + "…"

    @property
    def extensao(self):
        return self.arquivo.name.rsplit(".", 1)[-1].lower() if "." in self.arquivo.name else ""

    @property
    def eh_pdf(self):
        return self.extensao == "pdf"

    @property
    def eh_imagem(self):
        return self.extensao in ("png", "jpg", "jpeg", "gif", "webp")
