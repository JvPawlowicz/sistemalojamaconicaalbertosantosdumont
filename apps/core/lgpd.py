"""Direitos do titular: exportação dos dados do próprio usuário."""
import json
from datetime import date, datetime
from decimal import Decimal


def _json(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    return str(obj)


def exportar_dados(irmao):
    from apps.atas.models import AssinaturaAta
    from apps.core.models import AceiteTermo
    from apps.sessoes.models import Cerimonia, Presenca
    from apps.tesouraria.models import Lancamento
    from apps.visitas.models import VisitaRealizada

    campos = ["username", "nome_completo", "email", "matricula", "grau", "situacao", "data_iniciacao", "data_promocao",
              "data_elevacao", "cpf", "rg", "data_nascimento", "telefone", "whatsapp", "cep", "logradouro", "numero",
              "complemento", "bairro", "cidade", "uf", "contato_emergencia_nome", "contato_emergencia_telefone",
              "formacao_academica", "profissao", "empresa", "plano_saude", "plano_funeral"]
    return {
        "dados_cadastrais": {c: getattr(irmao, c) for c in campos},
        "perfis": irmao.perfis,
        "familiares": [{"parentesco": f.parentesco, "nome": f.nome, "data_nascimento": f.data_nascimento}
                       for f in irmao.familiares.all()],
        "cerimonias": [{"tipo": c.tipo, "data": c.data} for c in Cerimonia.objects.filter(irmao=irmao)],
        "presencas": [{"sessao": p.sessao.data_hora, "situacao": p.situacao}
                      for p in Presenca.objects.filter(irmao=irmao).select_related("sessao")],
        "mensalidades": [{"competencia": l.competencia, "valor": l.valor, "status": l.status, "pago_em": l.pago_em}
                         for l in Lancamento.objects.filter(irmao=irmao)],
        "visitas_realizadas": [{"loja": v.loja_nome, "data": v.data} for v in VisitaRealizada.objects.filter(irmao=irmao)],
        "assinaturas_de_atas": [{"ata": a.ata_id, "versao": a.versao, "assinado_em": a.assinado_em, "ip": a.ip,
                                 "codigo": a.codigo} for a in AssinaturaAta.objects.filter(irmao=irmao)],
        "aceites_do_termo": [{"versao": a.termo.versao, "aceito_em": a.aceito_em, "ip": a.ip}
                             for a in AceiteTermo.objects.filter(irmao=irmao).select_related("termo")],
    }


def exportar_json(irmao):
    return json.dumps(exportar_dados(irmao), default=_json, ensure_ascii=False, indent=2)
