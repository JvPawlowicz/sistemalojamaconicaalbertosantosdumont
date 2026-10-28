"""Textos padrão para o Secretário (inseridos na ata digitando @). Editáveis no sistema.

Variáveis: {{data}}, {{data_extenso}}, {{hora}}, {{grau}}, {{tipo}}, {{local}}, {{ano_maconico}}, {{loja}},
{{numero_loja}}, {{oriente}}, {{veneravel}}, {{secretario}}, {{presentes}}, {{visitantes}}.
"""

CAB, ABR, EXP, ORD, ENC, FOR, COM = "cabecalho", "abertura", "expediente", "ordem_do_dia", "encerramento", "formula", "completa"

MODELOS = [
    # titulo, atalho, categoria, texto
    ("Cabeçalho da ata", "cabecalho", CAB,
     "ATA Nº ____ da Sessão {{tipo}} de {{grau}}, realizada em {{data_extenso}}, às {{hora}}, no Templo da {{loja}} nº {{numero_loja}}, "
     "Oriente de {{oriente}}, sob a presidência do Venerável Mestre {{veneravel}}, secretariada por {{secretario}}."),
    ("Cabeçalho — sessão magna", "cabecalho-magna", CAB,
     "ATA Nº ____ da Sessão Magna de {{grau}}, realizada em {{data_extenso}}, às {{hora}}, em {{local}}, Oriente de {{oriente}}, "
     "convocada pela {{loja}} nº {{numero_loja}}, sob a presidência do Venerável Mestre {{veneravel}}, secretariada por {{secretario}}."),
    ("Abertura dos trabalhos", "abertura", ABR,
     "Constatada a presença de {{presentes}} irmãos e a regularidade do quórum, o Venerável Mestre declarou abertos os trabalhos "
     "no Grau de {{grau}}, invocando a proteção do Grande Arquiteto do Universo."),
    ("Abertura — conferência de quórum", "abertura-quorum", ABR,
     "O Venerável Mestre determinou ao Primeiro Vigilante a verificação da regularidade dos presentes e, atestada a existência de quórum "
     "regimental com {{presentes}} irmãos, deu início aos trabalhos ritualísticos do Grau de {{grau}}."),
    ("Leitura e aprovação da ata anterior", "ata-anterior", EXP,
     "Foi lida e, posta em discussão, aprovada sem emendas a ata da sessão anterior."),
    ("Ata anterior aprovada com emendas", "ata-anterior-emendas", EXP,
     "Foi lida a ata da sessão anterior que, posta em discussão, foi aprovada com as seguintes emendas: ____________________."),
    ("Visitantes", "visitantes", EXP,
     "Registrou-se a presença de {{visitantes}} visitante(s), recebidos fraternalmente com as honras de estilo."),
    ("Visitantes — saudação nominal", "visitantes-nominal", EXP,
     "O Venerável Mestre saudou os irmãos visitantes ____________________, da Loja ____________________, Oriente de ____________________, "
     "que foram convidados a tomar assento no Oriente / Coluna do Sul."),
    ("Expediente recebido", "expediente-recebido", EXP,
     "O Secretário deu conhecimento do expediente recebido: ____________________."),
    ("Expediente expedido", "expediente-expedido", EXP,
     "O Secretário deu conhecimento do expediente expedido: ____________________."),
    ("Balaústre do Tesoureiro", "tesoureiro", EXP,
     "O Irmão Tesoureiro apresentou o balancete do período, informando o saldo em caixa de R$ ________, que foi posto em discussão e aprovado."),
    ("Tronco de Beneficência", "tronco", EXP,
     "Circulou o Tronco de Beneficência, tendo sido arrecadado o valor de R$ ________, destinado ao socorro e à solidariedade."),
    ("Saco de Propostas e Informações", "saco-propostas", EXP,
     "Circulou o Saco de Propostas e Informações, nada tendo sido apresentado / tendo sido apresentado o seguinte: ____________________."),
    ("Palavra a bem da Ordem em geral", "palavra", EXP,
     "A palavra foi franqueada a bem da Ordem em geral, da Loja e do quadro, tendo se manifestado: ____________________."),
    ("Ordem do dia — instrução", "ordem-instrucao", ORD,
     "Na Ordem do Dia, o Irmão ____________________ apresentou a instrução sobre o tema “____________________”, que foi debatida pelos presentes."),
    ("Ordem do dia — iniciação", "ordem-iniciacao", ORD,
     "Na Ordem do Dia, cumpridas as formalidades regimentais, procedeu-se à Iniciação do profano ____________________, que recebeu a Luz "
     "e foi proclamado Aprendiz Maçom."),
    ("Ordem do dia — elevação/passagem", "ordem-passagem", ORD,
     "Na Ordem do Dia, cumpridas as formalidades regimentais, procedeu-se à Passagem ao Grau de Companheiro do Irmão ____________________."),
    ("Ordem do dia — exaltação", "ordem-exaltacao", ORD,
     "Na Ordem do Dia, cumpridas as formalidades regimentais, procedeu-se à Exaltação ao Grau de Mestre do Irmão ____________________."),
    ("Ordem do dia — votação", "ordem-votacao", ORD,
     "Posta em votação a matéria “____________________”, o resultado apurado foi de ____ votos favoráveis, ____ contrários e ____ abstenções, "
     "sendo a proposta (aprovada / rejeitada)."),
    ("Eleição e posse", "eleicao-posse", ORD,
     "Procedeu-se à eleição da Administração para o ano maçônico {{ano_maconico}}, sendo eleito(a) o Irmão ____________________ para o cargo de "
     "____________________, empossado(a) na forma regimental."),
    ("Sindicância / proposta", "proposta", ORD,
     "Foi apresentada a proposta de iniciação do profano ____________________, subscrita pelo Irmão ____________________, a qual foi encaminhada "
     "à Comissão de Sindicância."),
    ("Homenagem / comenda", "homenagem", ORD,
     "O Venerável Mestre prestou homenagem ao Irmão ____________________, em reconhecimento aos serviços prestados à Loja e à Ordem."),
    ("Falecimento — pesar", "pesar", ORD,
     "O Venerável Mestre comunicou, com profundo pesar, o falecimento de ____________________, determinando o registro em ata do voto de pesar "
     "e a transmissão de condolências à família."),
    ("Justificativa de ausências", "ausencias", EXP,
     "Foram justificadas as ausências dos irmãos: ____________________."),
    ("Aniversariantes", "aniversariantes", FOR,
     "O Venerável Mestre cumprimentou os aniversariantes do mês: ____________________."),
    ("Agradecimento ao Grande Arquiteto", "gadu", FOR,
     "Agradecemos ao Grande Arquiteto do Universo por mais esta reunião realizada em paz, harmonia e fraternidade."),
    ("Encerramento", "encerramento", ENC,
     "Nada mais havendo a tratar, o Venerável Mestre encerrou os trabalhos às ____ horas, do que, para constar, "
     "eu, {{secretario}}, Secretário, lavrei a presente ata que, lida e aprovada, vai assinada pelos Irmãos competentes."),
    ("Encerramento — ágape", "encerramento-agape", ENC,
     "Nada mais havendo a tratar, o Venerável Mestre encerrou os trabalhos às ____ horas, convidando os irmãos para o Ágape fraterno. "
     "Eu, {{secretario}}, Secretário, lavrei a presente ata."),
]


# Atas completas: usadas como ponto de partida ao criar a ata (atalho "ata-<tipo da sessão>").
_ABERTURA = ("Constatada a presença de {{presentes}} irmãos e a regularidade do quórum, o Venerável Mestre declarou abertos os trabalhos "
             "no Grau de {{grau}}, invocando a proteção do Grande Arquiteto do Universo.")
_EXPEDIENTE = ("Foi lida e aprovada a ata da sessão anterior. Registrou-se a presença de {{visitantes}} visitante(s). "
               "O Secretário deu conhecimento do expediente: ____________________. Circularam o Saco de Propostas e Informações e o Tronco de Beneficência.")
_ENCERRAMENTO = ("Nada mais havendo a tratar, o Venerável Mestre encerrou os trabalhos às ____ horas, do que, para constar, "
                 "eu, {{secretario}}, Secretário, lavrei a presente ata que, lida e aprovada, vai assinada pelos Irmãos competentes.")
_CAB = ("ATA Nº ____ da Sessão {{tipo}} de {{grau}}, realizada em {{data_extenso}}, às {{hora}}, no Templo da {{loja}} nº {{numero_loja}}, "
        "Oriente de {{oriente}}, sob a presidência do Venerável Mestre {{veneravel}}, secretariada por {{secretario}}.")


def _completa(ordem):
    return "\n\n".join([_CAB, _ABERTURA, _EXPEDIENTE, ordem, _ENCERRAMENTO])


MODELOS += [
    ("Ata completa — sessão ordinária", "ata-ordinaria", COM,
     _completa("Na Ordem do Dia, tratou-se de: ____________________. A palavra foi franqueada a bem da Ordem em geral, da Loja e do quadro.")),
    ("Ata completa — sessão de instrução", "ata-instrucao", COM,
     _completa("Na Ordem do Dia, o Irmão ____________________ apresentou a instrução sobre o tema “____________________”, debatida pelos presentes.")),
    ("Ata completa — sessão econômica", "ata-economica", COM,
     _completa("Na Ordem do Dia, tratou-se de assuntos administrativos e financeiros: ____________________. O Tesoureiro apresentou o balancete, aprovado pelo Plenário.")),
    ("Ata completa — sessão magna", "ata-magna", COM,
     _completa("Em sessão magna, procedeu-se a ____________________, com a presença de autoridades e visitantes, recebidos com as honras de estilo.")),
    ("Ata completa — iniciação", "ata-iniciacao", COM,
     _completa("Cumpridas as formalidades regimentais, procedeu-se à Iniciação do profano ____________________, que recebeu a Luz e foi proclamado Aprendiz Maçom.")),
    ("Ata completa — passagem (promoção)", "ata-promocao", COM,
     _completa("Cumpridas as formalidades regimentais, procedeu-se à Passagem ao Grau de Companheiro do Irmão ____________________.")),
    ("Ata completa — exaltação (elevação)", "ata-elevacao", COM,
     _completa("Cumpridas as formalidades regimentais, procedeu-se à Exaltação ao Grau de Mestre do Irmão ____________________.")),
]
