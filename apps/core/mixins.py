from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PerfilRequeridoMixin(LoginRequiredMixin):
    """Exige que o usuário tenha ao menos um dos perfis listados (considerando os implícitos)."""

    perfis_permitidos: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.perfis_permitidos and not request.user.tem_algum_perfil(*self.perfis_permitidos):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def exigir_perfil(user, *perfis):
    if not user.tem_algum_perfil(*perfis):
        raise PermissionDenied
