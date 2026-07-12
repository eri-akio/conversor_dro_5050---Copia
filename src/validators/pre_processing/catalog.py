"""Catálogo das 34 críticas oficiais de pré-processamento.

As descrições, bases confrontadas, tipo e data de início foram
transcritos do arquivo oficial fornecido ao projeto.
"""

from __future__ import annotations

from src.config import (
    PRE_PROCESSING_CRITICS_PATH,
)
from src.domain.pre_processing import (
    PreProcessingExecutionClass,
    PreProcessingProvider,
    PreProcessingRuleDefinition,
)
from src.domain.regulatory_version import YearMonth


START = YearMonth(2021, 6)


def _rule(
    code: str,
    description: str,
    confronted_base: str,
    scope: str,
    execution_class: PreProcessingExecutionClass,
    dependency: str | None,
    provider: PreProcessingProvider,
) -> PreProcessingRuleDefinition:
    return PreProcessingRuleDefinition(
        code=code,
        document_code="5050",
        official_type="E",
        official_description=description,
        confronted_base=confronted_base,
        start_label="jun/21",
        start_data_base=START,
        scope=scope,
        execution_class=execution_class,
        dependency=dependency,
        provider=provider,
        source_path=PRE_PROCESSING_CRITICS_PATH,
    )


PRE_PROCESSING_RULES: tuple[
    PreProcessingRuleDefinition,
    ...,
] = (
    _rule(
        "DRO001001",
        "Verifica se o código do conglomerado prudencial existe no Unicad.",
        "UNICAD",
        "DOCUMENTO",
        PreProcessingExecutionClass.EXTERNAL,
        "UNICAD",
        PreProcessingProvider.EXTERNAL_CONGLOMERATE,
    ),
    _rule(
        "DRO001002",
        "Verifica se o idBacen (ou idInstal - para os casos de agências localizadas no exterior ) existe nas bases de dados do Bacen.",
        "UNICAD",
        "EVENTO",
        PreProcessingExecutionClass.EXTERNAL,
        "UNICAD/Bacen",
        PreProcessingProvider.EXTERNAL_BACEN_ID,
    ),
    _rule(
        "DRO001101",
        "Verifica unicidade do campo codigoConta no Bloco 4 - Tabela de Subtítulos de Nível Interno.",
        "DRO",
        "CONTA_INTERNA",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.REFERENCE_TABLES,
    ),
    _rule(
        "DRO001102",
        "Verifica unicidade do campo codigoSistema no Bloco 3 - Tabela de Sistemas de Origem.",
        "DRO",
        "SISTEMA_ORIGEM",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.REFERENCE_TABLES,
    ),
    _rule(
        "DRO001103",
        "Verifica a unicidade do idEvento no documento enviado.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.EVENT_VALIDATION,
    ),
    _rule(
        "DRO001201",
        "Verifica, quando informado, se a data de ocorrência é menor ou igual a data de descoberta.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001202",
        "Verifica se o campo dataDescoberta foi devidamente informado para datas de ocorrência maiores ou iguais a 1.1.2021.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001212",
        "Verifica a obrigatoriedade de preenchimento da categoriaNivel2 para eventos cuja data de ocorrência forem maiores ou iguais a 1.1.2021 .",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001231",
        "Verifica se o somatório dos campos totalPerdaEfetiva e totalProvisão é maior ou igual a R$ 1 mil. Valores inferiores a esse patamar devem ser informados de forma consolidada.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001232",
        "Verifica se o total recuperado (totalRecuperado ) é menor ou igual ao somatório, em valores absolutos, dos campos totalPerdaEfetiva e totalProvisao .",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001233",
        "Verifica, quando o campo valorTotalRisco é informado, se há informação a respeito da natureza de contingência (tributária, trabalhista e/ou cívil) .",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001241",
        "Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021 e para eventos cujo somatório do campo totalPerda Efetiva com o campo valorTotalRisco for maior ou igual a R$ 1 milhão, se o campo descricaoEvento foi devidamente preenchido .",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.DOCUMENT_CONFLICT,
        "CONF-022",
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001251",
        "Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo riscoAssociado foi devidamente preenchido.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001252",
        "Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo ligadoRiscoSocioAmbiental foi devidamente preenchido.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001253",
        "Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo ligadoRIscoCibernetico foi devidamente preenchido.",
        "DRO",
        "EVENTO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001301",
        'Para tipoAvaliação igual a "NA", valores de provisão (valorProvisao) não devem ser informados.',
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001302",
        'Verifica, caso tipoAvaliacao seja igual a "I" ou "M", se valores para totalProvisao e/ou valorProvisao foram devidamente informados.',
        "DRO",
        "EVENTO/CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001311",
        "Verifica se o campo valorTotalRisco , quando informado para um dado idEvento , corresponde ao somatório do campo totalProvisao com todos os lançamento informados nos campos valorRisco .",
        "DRO",
        "EVENTO/PROBABILIDADE",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.EVENT_VALIDATION,
    ),
    _rule(
        "DRO001312",
        'Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021 e tipoAvaliacao igual a "I" (individual), se o campo probabilidadePerda foi devidamente preenchido.',
        "DRO",
        "PROBABILIDADE",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.EVENT_VALIDATION,
    ),
    _rule(
        "DRO001313",
        'Verifica, quando o tipoAvaliacao for igual a "M" (massificada), a inexistência de informação no campo probabilidade de perda (probabilidadePerda ). Conforme definido, não deve ser informada probabilidade de perda para eventos com tipo de avaliação massificada.',
        "DRO",
        "PROBABILIDADE",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001314",
        'Verifica se a soma dos campos valorRisco apresenta resultado maior que zero para o seguinte contexto: a) a data de ocorrência é maior ou igual a 1.1.2021; b) o tipoAvaliacao é igual a "I" (Individualizada); c) a naturezaContingencia é diferente de "NA"; e d) foi informada probabilidadePerda .',
        "DRO",
        "PROBABILIDADE",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.EVENT_VALIDATION,
    ),
    _rule(
        "DRO001321",
        "Verifica se o código preenchido para identificação do sistema origem (codigoSistemaOrigem ) está devidamente informado no Bloco 3 - Tabela de Sistemas de Origem.",
        "DRO",
        "EVENTO/SISTEMA_ORIGEM",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.REFERENCE_TABLES,
    ),
    _rule(
        "DRO001401",
        "Verifica, nos casos em que o campo contaBalAnaliticoDebito é informado, se a referida conta está devidamente informada no campo codigoConta do Bloco 4 - Tabela de Subtítulos de Nível Interno",
        "DRO",
        "CONTABILIZACAO/CONTA_INTERNA",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.REFERENCE_TABLES,
    ),
    _rule(
        "DRO001402",
        "Verifica, nos casos em que o campo contaBalAnaliticoCredito é informado, se a referida conta está devidamente informada no campo codigoConta do Bloco 4 - Tabela de Subtítulos de Nível Interno",
        "DRO",
        "CONTABILIZACAO/CONTA_INTERNA",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.REFERENCE_TABLES,
    ),
    _rule(
        "DRO001411",
        "Verifica se o valorRecuperacao é menor ou igual a zero. Por convenção, valores de recuperação devem ser lançados com sinal negativo.",
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001421",
        "Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo fonteRecuperacao foi devidamene informado quando há lançamento referente a valor recuperado.",
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001431",
        "Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifDebito , se foi informada uma conta Cosif válida",
        "DRO COSIF",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.PARTIAL,
        "Cadastro oficial COSIF",
        PreProcessingProvider.COSIF_DEBIT,
    ),
    _rule(
        "DRO001432",
        "Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifCredito , se foi informada uma conta Cosif válida.",
        "DRO COSIF",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.PARTIAL,
        "Cadastro oficial COSIF",
        PreProcessingProvider.COSIF_CREDIT,
    ),
    _rule(
        "DRO001441",
        "Verifica, nos casos em que o campo contaBalAnaliticoDebito é informado, se há informação preenchida no campo contaCosifDebito correspondente .",
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001442",
        "Verifica, nos casos em que o campo contaBalAnaliticoCredito é informado, se há informação preenchida no campo contaCosifCredito correspondente .",
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001443",
        "Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifDebito , se há preenchimento do campo contaBalAnaliticoDebito correspondente.",
        "DRO COSIF",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.PARTIAL,
        "Regra de exigência COSIF",
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001444",
        "Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifCredito , se há preenchimento do campo contaBalAnaliticoCredito correspondente.",
        "DRO COSIF",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.PARTIAL,
        "Regra de exigência COSIF",
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001451",
        "Verifica, para os casos que não se referem apenas a lançamentos de risco, se foram devidamente preenchidos os respectivos campos contábeis. Lançamentos que não sejam exclusivamente de risco têm que ter informações relativas às contas contábeis correspondentes.",
        "DRO",
        "CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.ROW_VALIDATION,
    ),
    _rule(
        "DRO001452",
        'Verifica a inexistência de informação nos campos de informações contábeis, por indevida, nos casos de um idEvento que contenha lançamentos relativos apenas a risco. Ou seja, não é devida a informação de conta contábil nos casos de um contexto de informações exclusivas a valores em risco. O bloco XML "contabilizacao" não deve ser informado.',
        "DRO",
        "EVENTO/CONTABILIZACAO",
        PreProcessingExecutionClass.LOCAL,
        None,
        PreProcessingProvider.EVENT_VALIDATION,
    ),
)


PRE_PROCESSING_CODES: tuple[str, ...] = tuple(
    rule.code
    for rule in PRE_PROCESSING_RULES
)


def get_pre_processing_rule(
    code: str,
) -> PreProcessingRuleDefinition:
    for rule in PRE_PROCESSING_RULES:
        if rule.code == code:
            return rule

    raise KeyError(
        f"Crítica de pré-processamento não catalogada: {code}"
    )
