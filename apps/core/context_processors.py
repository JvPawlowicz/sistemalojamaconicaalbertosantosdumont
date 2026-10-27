from .models import Loja
from .perfis import GRAU_NOMES


def loja(request):
    ctx = {"loja": Loja.atual()}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        ctx["grau_nome"] = GRAU_NOMES.get(user.grau, "")
    return ctx
