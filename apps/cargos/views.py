from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.core import perfis as P
from apps.core.crud import CriarView, EditarView, ListaView
from apps.core.models import AnoMaconico
from apps.irmaos.models import Irmao

from .forms import CargoForm
from .models import Cargo, Gestao


@login_required
def quadro(request):
    anos = AnoMaconico.objects.all()
    ano = AnoMaconico.atual()
    if request.GET.get("ano"):
        ano = get_object_or_404(AnoMaconico, pk=request.GET["ano"])
    pode_editar = request.user.tem_perfil(P.SECRETARIO)
    if request.method == "POST":
        if not pode_editar:
            raise PermissionDenied
        cargo = get_object_or_404(Cargo, pk=request.POST.get("cargo"))
        irmao_id = request.POST.get("irmao")
        if irmao_id:
            irmao = get_object_or_404(Irmao, pk=irmao_id, is_active=True, grau__isnull=False)
            Gestao.objects.update_or_create(ano=ano, cargo=cargo, defaults={"irmao": irmao})
            messages.success(request, f"{cargo.nome}: {irmao.nome_completo}.")
        else:
            Gestao.objects.filter(ano=ano, cargo=cargo).delete()
            messages.info(request, f"{cargo.nome}: vago.")
        return redirect(f"{request.path}?ano={ano.pk}")
    titulares = {g.cargo_id: g for g in Gestao.objects.filter(ano=ano).select_related("irmao")}
    linhas = [(c, titulares.get(c.pk)) for c in Cargo.objects.filter(ativo=True)]
    return render(request, "cargos/quadro.html", {
        "ano": ano, "anos": anos, "linhas": linhas, "pode_editar": pode_editar,
        "irmaos": Irmao.objects.filter(is_active=True, grau__isnull=False),
    })


@login_required
def copiar_gestao(request):
    """Copia a gestão do ano anterior para o ano informado (ponto de partida da nova gestão)."""
    if not request.user.tem_perfil(P.SECRETARIO) or request.method != "POST":
        raise PermissionDenied
    ano = get_object_or_404(AnoMaconico, pk=request.POST.get("ano"))
    anterior = AnoMaconico.para_data(ano.inicio.replace(year=ano.inicio.year - 1))
    n = 0
    for g in Gestao.objects.filter(ano=anterior):
        _, criado = Gestao.objects.get_or_create(ano=ano, cargo=g.cargo, defaults={"irmao": g.irmao})
        n += criado
    messages.success(request, f"{n} cargo(s) copiado(s) de {anterior}.")
    return redirect(f"{reverse_lazy('cargos:quadro')}?ano={ano.pk}")


class CatalogoView(ListaView):
    perfis_permitidos = (P.ADMINISTRADOR,)
    titulo = "Catálogo de cargos"
    subtitulo = "Configure os cargos da Loja (o Rito Schröder tem quadro reduzido)."
    colunas = [("Ordem", lambda o: o.ordem), ("Cargo", lambda o: o.nome), ("Sigla", lambda o: o.sigla),
               ("Ativo", lambda o: "Sim" if o.ativo else "Não")]
    url_novo = reverse_lazy("cargos:novo")
    rotulo_novo = "Novo cargo"

    def get_objetos(self):
        return Cargo.objects.all()

    def url_de(self, obj):
        return reverse_lazy("cargos:editar", args=[obj.pk])


class NovoCargo(CriarView):
    perfis_permitidos = (P.ADMINISTRADOR,)
    model = Cargo
    form_class = CargoForm
    titulo = "Novo cargo"
    success_url = reverse_lazy("cargos:catalogo")


class EditarCargo(EditarView):
    perfis_permitidos = (P.ADMINISTRADOR,)
    model = Cargo
    form_class = CargoForm
    titulo = "Editar cargo"
    success_url = reverse_lazy("cargos:catalogo")
