from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .perfis import ADMINISTRATIVOS, expandir

_ISENTOS_ACEITE = ("/sair/", "/aceite-termo/", "/static/", "/privacidade/", "/verificar/", "/2fa/")
_ISENTOS_2FA = ("/sair/", "/2fa/", "/static/", "/verificar/", "/privacidade/", "/aceite-termo/")


class AceiteTermoMiddleware:
    """Obriga o aceite do termo de assinatura eletrônica vigente no primeiro acesso."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not request.path.startswith(_ISENTOS_ACEITE):
            from .models import TermoAceite

            termo = TermoAceite.vigente()
            if termo and not user.aceites.filter(termo=termo).exists():
                return redirect(reverse("core:aceite_termo"))
        return self.get_response(request)


class Exigir2FAMiddleware:
    """Perfis administrativos precisam de 2FA (TOTP) verificado na sessão."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            getattr(settings, "EXIGIR_2FA", True)
            and user is not None
            and user.is_authenticated
            and not request.path.startswith(_ISENTOS_2FA)
            and expandir(user.perfis) & ADMINISTRATIVOS
            and not user.is_verified()
        ):
            if user.totpdevice_set.filter(confirmed=True).exists():
                return redirect(f"{reverse('core:2fa_verificar')}?next={request.path}")
            return redirect(reverse("core:2fa_configurar"))
        return self.get_response(request)
