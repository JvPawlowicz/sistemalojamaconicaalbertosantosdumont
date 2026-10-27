from django.conf import settings
from django.db import models


class ItemPatrimonio(models.Model):
    class Estado(models.TextChoices):
        OTIMO = "otimo", "Ótimo"
        BOM = "bom", "Bom"
        REGULAR = "regular", "Regular"
        RUIM = "ruim", "Ruim"
        BAIXADO = "baixado", "Baixado"

    nome = models.CharField(max_length=150)
    categoria = models.CharField(max_length=60, blank=True, help_text="Ex.: Alfaia, Livro, Mobiliário, Vela")
    quantidade = models.PositiveIntegerField(default=1)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.BOM)
    local = models.CharField("Localização", max_length=100, blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    valor = models.DecimalField("Valor (R$)", max_digits=10, decimal_places=2, null=True, blank=True)
    data_aquisicao = models.DateField(null=True, blank=True)
    observacao = models.TextField(blank=True)
    emprestavel = models.BooleanField("Pode ser emprestado (biblioteca)", default=False)

    class Meta:
        ordering = ["categoria", "nome"]
        verbose_name = "Item de patrimônio"
        verbose_name_plural = "Patrimônio"

    def __str__(self):
        return self.nome

    @property
    def emprestado_a(self):
        e = self.emprestimos.filter(devolvido_em__isnull=True).first()
        return e.irmao if e else None


class Emprestimo(models.Model):
    item = models.ForeignKey(ItemPatrimonio, on_delete=models.CASCADE, related_name="emprestimos")
    irmao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="emprestimos")
    emprestado_em = models.DateField()
    devolver_ate = models.DateField(null=True, blank=True)
    devolvido_em = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-emprestado_em"]
