"""Arquitetura de informação: seções do menu e abas, definidas em um único lugar.

Cada seção agrupa módulos relacionados (menos itens no menu, menos cliques para trocar de contexto).
A visibilidade usa as mesmas regras de perfil/grau do restante do sistema.
"""
from dataclasses import dataclass, field

from django.urls import reverse

from . import perfis as P


def _todos(u):
    return True


def _perfil(*perfis):
    return lambda u: u.tem_algum_perfil(*perfis)


def _mestre(u):
    return u.pode_ver_grau(P.MESTRE) or u.tem_perfil(P.SECRETARIO)


@dataclass(frozen=True)
class Item:
    rotulo: str
    url_name: str
    visivel: callable = _todos
    icone: str = ""
    extras: tuple = ()  # outras view_names que mantêm esta aba ativa


@dataclass(frozen=True)
class Secao:
    chave: str
    titulo: str
    icone: str
    itens: tuple
    visivel: callable = _todos
    namespaces: tuple = ()
    nomes: tuple = ()  # view_names específicas (têm prioridade sobre namespaces)
    grupo: str = ""


SECOES = (
    Secao("inicio", "Início", "layout-dashboard", (
        Item("Painel", "core:painel"),
        Item("Mural de avisos", "core:avisos", extras=("core:aviso_novo", "core:aviso_editar", "core:aviso_excluir")),
    ), nomes=("core:painel", "core:avisos", "core:aviso_novo", "core:aviso_editar", "core:aviso_excluir")),
    Secao("agenda", "Agenda", "calendar-days", (
        Item("Calendário", "sessoes:agenda"),
        Item("Sessões", "sessoes:lista", extras=("sessoes:detalhe", "sessoes:criar", "sessoes:editar")),
        Item("Eventos", "sessoes:eventos", extras=("sessoes:evento", "sessoes:evento_novo", "sessoes:evento_editar")),
        Item("Frequência", "sessoes:frequencia"),
        Item("Votações", "votacoes:lista", extras=("votacoes:detalhe", "votacoes:criar")),
    ), namespaces=("sessoes", "votacoes"), grupo="Loja"),
    Secao("atas", "Atas", "scroll-text", (
        Item("Atas", "atas:lista", extras=("atas:detalhe", "atas:criar", "atas:editar", "atas:assinar")),
        Item("Modelos de texto", "atas:modelos", _perfil(P.SECRETARIO), extras=("atas:modelo_novo", "atas:modelo_editar", "atas:modelos_padroes", "atas:modelo_rapido")),
    ), namespaces=("atas",), grupo="Loja"),
    Secao("irmaos", "Irmãos", "users", (
        Item("Quadro", "irmaos:lista", extras=("irmaos:detalhe", "irmaos:criar", "irmaos:editar", "irmaos:importar")),
        Item("Cargos e gestão", "cargos:quadro"),
        Item("Hospitalaria", "hospitalaria:painel", _perfil(P.HOSPITALEIRO), extras=("hospitalaria:caso", "hospitalaria:caso_novo")),
        Item("Candidatos", "candidatos:painel", _mestre, extras=("candidatos:detalhe", "candidatos:criar")),
        Item("Comissões", "comissoes:lista", _mestre, extras=("comissoes:nova", "comissoes:editar")),
        Item("Visitação", "visitas:realizadas", extras=("visitas:nova_realizada", "visitas:visitantes",
                                                       "visitas:visitante_novo", "visitas:visitante_editar", "visitas:lojas", "visitas:loja_nova", "visitas:loja_editar",
                                                       "visitas:certificado_recebido")),
    ), namespaces=("irmaos", "cargos", "candidatos", "comissoes", "visitas", "hospitalaria"), grupo="Loja"),
    Secao("acervo", "Acervo", "book-open", (
        Item("Biblioteca", "documentos:lista", extras=("documentos:ver", "documentos:enviar")),
        Item("Expediente", "expediente:lista", _perfil(P.SECRETARIO), extras=("expediente:novo",)),
        Item("Patrimônio", "patrimonio:lista", _perfil(P.SECRETARIO), extras=("patrimonio:novo", "patrimonio:editar")),
    ), namespaces=("documentos", "expediente", "patrimonio"), grupo="Loja"),
    Secao("financeiro", "Financeiro", "wallet", (
        Item("Visão geral", "tesouraria:painel", _perfil(P.TESOUREIRO)),
        Item("Mensalidades", "tesouraria:mensalidades", _perfil(P.TESOUREIRO), extras=("tesouraria:avulso", "tesouraria:pix")),
        Item("Conciliação", "tesouraria:conciliar", _perfil(P.TESOUREIRO)),
        Item("Caixa", "tesouraria:caixa", _perfil(P.TESOUREIRO)),
        Item("Orçamento", "tesouraria:orcamento", _perfil(P.TESOUREIRO)),
        Item("Categorias", "tesouraria:categorias", _perfil(P.TESOUREIRO)),
        Item("Categorias de irmão", "irmaos:categorias", _perfil(P.TESOUREIRO, P.ADMINISTRADOR),
             extras=("irmaos:categoria_editar",)),
        Item("Ágape", "agape:lista", extras=("agape:detalhe", "agape:criar", "agape:editar", "agape:inventario", "agape:item_novo",
                                           "agape:item_editar", "agape:caixa")),
        Item("Tronco", "hospitalaria:tronco", _perfil(P.HOSPITALEIRO, P.TESOUREIRO)),
        Item("Minhas mensalidades", "tesouraria:minhas"),
    ), namespaces=("tesouraria", "agape"), nomes=("irmaos:categorias", "irmaos:categoria_editar", "hospitalaria:tronco"), grupo="Financeiro"),
    Secao("relatorios", "Relatórios", "chart-column", (Item("Relatórios", "relatorios:indice", extras=("relatorios:ver",)),),
          visivel=_perfil(P.SECRETARIO, P.TESOUREIRO), namespaces=("relatorios",), grupo="Gestão"),
    Secao("admin", "Administração", "settings", (
        Item("Configurações", "core:configuracoes", extras=("core:novo_termo",)),
        Item("Catálogo de cargos", "cargos:catalogo", extras=("cargos:novo", "cargos:editar")),
        Item("Aceites do termo", "core:aceites"),
        Item("Solicitações LGPD", "core:solicitacoes_lgpd"),
        Item("E-mails enviados", "core:emails"),
        Item("Painel técnico", "admin:index", _perfil(P.DESENVOLVEDOR)),
    ), visivel=_perfil(P.ADMINISTRADOR), nomes=("core:configuracoes", "core:novo_termo", "cargos:catalogo", "cargos:novo",
                                                "cargos:editar", "core:aceites", "core:solicitacoes_lgpd", "core:emails"),
          grupo="Gestão"),
)


def itens_visiveis(secao, user):
    return [i for i in secao.itens if i.visivel(user)]


def secoes_visiveis(user):
    return [s for s in SECOES if s.visivel(user) and itens_visiveis(s, user)]


def entrada(secao, user):
    """URL de entrada da seção: primeiro item visível."""
    return reverse(itens_visiveis(secao, user)[0].url_name)


def secao_da_view(view_name):
    """Seção à qual a view pertence (nomes específicos têm prioridade sobre o namespace)."""
    if not view_name:
        return None
    for s in SECOES:
        if view_name in s.nomes:
            return s
    ns = view_name.split(":")[0]
    for s in SECOES:
        if ns in s.namespaces:
            return s
    return None


def item_ativo(secao, view_name):
    for i in secao.itens:
        if view_name == i.url_name or view_name in i.extras:
            return i
    return None


def paginas_para_busca(user):
    """Atalhos de navegação (seção › aba) para a busca rápida."""
    saida = []
    for s in secoes_visiveis(user):
        for i in itens_visiveis(s, user):
            rotulo = i.rotulo if i.rotulo == s.titulo else f"{s.titulo} › {i.rotulo}"
            saida.append({"rotulo": rotulo, "url": reverse(i.url_name)})
    return saida
