"""Perfis (o que o usuário pode fazer) e graus (o que o usuário pode ver)."""

IRMAO = "irmao"
TESOUREIRO = "tesoureiro"
SECRETARIO = "secretario"
VENERAVEL = "veneravel"
ADMINISTRADOR = "administrador"
HOSPITALEIRO = "hospitaleiro"
DESENVOLVEDOR = "desenvolvedor"

PERFIL_CHOICES = [
    (IRMAO, "Irmão"),
    (TESOUREIRO, "Tesoureiro"),
    (SECRETARIO, "Secretário"),
    (VENERAVEL, "Venerável"),
    (ADMINISTRADOR, "Administrador"),
    (HOSPITALEIRO, "Hospitaleiro"),
    (DESENVOLVEDOR, "Desenvolvedor"),
]

# Perfis implícitos: quem tem a chave também tem os valores.
IMPLICITOS = {
    SECRETARIO: {ADMINISTRADOR},
    VENERAVEL: {SECRETARIO, TESOUREIRO, ADMINISTRADOR, HOSPITALEIRO},
    DESENVOLVEDOR: {IRMAO, TESOUREIRO, SECRETARIO, VENERAVEL, ADMINISTRADOR, HOSPITALEIRO},
}

ADMINISTRATIVOS = {TESOUREIRO, SECRETARIO, VENERAVEL, ADMINISTRADOR, HOSPITALEIRO, DESENVOLVEDOR}


def expandir(perfis):
    """Devolve o conjunto de perfis efetivos, aplicando os implícitos (transitivamente)."""
    efetivos = {IRMAO}
    pendentes = list(perfis or [])
    while pendentes:
        p = pendentes.pop()
        if p in efetivos and p != IRMAO:
            continue
        efetivos.add(p)
        pendentes.extend(IMPLICITOS.get(p, ()))
    return efetivos


APRENDIZ, COMPANHEIRO, MESTRE = 1, 2, 3
GRAU_CHOICES = [(APRENDIZ, "Aprendiz"), (COMPANHEIRO, "Companheiro"), (MESTRE, "Mestre")]
GRAU_NOMES = dict(GRAU_CHOICES)
