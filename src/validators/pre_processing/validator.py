"""Integração e execução das críticas de pré-processamento.

As regras locais já executadas em validadores especializados são
reutilizadas. O integrador não recalcula regras nem substitui seus
resultados por uma implementação paralela.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from src.domain.base_row_validation import (
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.document_header import DocumentHeader
from src.domain.grouped_event import (
    EventGroupingResult,
    EventsValidationResult,
)
from src.domain.pre_processing import (
    PreProcessingEvidence,
    PreProcessingProvider,
    PreProcessingRuleDefinition,
    PreProcessingRuleResult,
    PreProcessingValidationResult,
)
from src.domain.reference_tables import (
    ReferenceTablesValidationResult,
)
from src.domain.regulatory_version import (
    RegulatoryVersion,
)
from src.validators.pre_processing.catalog import (
    PRE_PROCESSING_RULES,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"


class PreProcessingValidator:
    """Produz exatamente um resultado para cada crítica oficial."""

    def __init__(
        self,
        catalog: tuple[
            PreProcessingRuleDefinition,
            ...,
        ] = PRE_PROCESSING_RULES,
    ) -> None:
        self.catalog = catalog
        self._validate_catalog()

    def validate(
        self,
        *,
        header: DocumentHeader,
        profile: RegulatoryVersion,
        row_validation: BaseRowsValidationResult,
        grouping: EventGroupingResult,
        event_validation: EventsValidationResult,
        references: ReferenceTablesValidationResult,
    ) -> PreProcessingValidationResult:
        row_results = self._index_by_code(
            row_validation.rule_results
        )
        grouping_results = self._index_by_code(
            grouping.rule_results
        )
        event_results = self._index_by_code(
            event_validation.rule_results
        )
        reference_results = self._index_by_code(
            references.rule_results
        )

        rule_results: list[
            PreProcessingRuleResult
        ] = []

        for definition in self.catalog:
            if not definition.applies_to(
                header.data_base
            ):
                evidences = (
                    PreProcessingEvidence(
                        status=(
                            RuleExecutionStatus
                            .NOT_APPLICABLE
                        ),
                        severity=(
                            SEVERITY_INFORMATION
                        ),
                        source_stage="Matriz de vigência",
                        message=(
                            "A crítica ainda não estava "
                            "vigente para esta dataBase."
                        ),
                        values=(
                            (
                                "dataBase",
                                header.data_base,
                            ),
                            (
                                "vigenciaInicial",
                                definition.start_label,
                            ),
                        ),
                    ),
                )
            else:
                evidences = self._resolve_evidences(
                    definition=definition,
                    header=header,
                    grouping=grouping,
                    row_results=row_results,
                    grouping_results=(
                        grouping_results
                    ),
                    event_results=event_results,
                    reference_results=(
                        reference_results
                    ),
                )

            rule_results.append(
                PreProcessingRuleResult(
                    definition=definition,
                    status=(
                        self._aggregate_status(
                            evidences
                        )
                    ),
                    evidences=evidences,
                )
            )

        return PreProcessingValidationResult(
            profile_code=profile.code,
            data_base=header.data_base,
            source_path=self.catalog[0].source_path,
            rule_results=tuple(rule_results),
        )

    def _resolve_evidences(
        self,
        *,
        definition: PreProcessingRuleDefinition,
        header: DocumentHeader,
        grouping: EventGroupingResult,
        row_results: dict[str, list[Any]],
        grouping_results: dict[str, list[Any]],
        event_results: dict[str, list[Any]],
        reference_results: dict[str, list[Any]],
    ) -> tuple[PreProcessingEvidence, ...]:
        provider = definition.provider

        if (
            provider
            == PreProcessingProvider
            .EXTERNAL_CONGLOMERATE
        ):
            return (
                PreProcessingEvidence(
                    status=(
                        RuleExecutionStatus
                        .NOT_EXECUTED
                    ),
                    severity=SEVERITY_NOT_EXECUTED,
                    source_stage=(
                        "Dependência externa UNICAD"
                    ),
                    message=(
                        "A existência do conglomerado não "
                        "foi consultada porque a base UNICAD "
                        "não foi fornecida ao projeto."
                    ),
                    columns=("codigoConglomerado",),
                    values=(
                        (
                            "codigoConglomerado",
                            header.codigo_conglomerado,
                        ),
                    ),
                ),
            )

        if (
            provider
            == PreProcessingProvider
            .EXTERNAL_BACEN_ID
        ):
            return self._bacen_id_evidences(
                grouping
            )

        if provider == PreProcessingProvider.COSIF_DEBIT:
            return self._cosif_evidences(
                grouping=grouping,
                cosif_field="contaCosifDebito",
                internal_field=(
                    "contaBalAnaliticoDebito"
                ),
            )

        if provider == PreProcessingProvider.COSIF_CREDIT:
            return self._cosif_evidences(
                grouping=grouping,
                cosif_field="contaCosifCredito",
                internal_field=(
                    "contaBalAnaliticoCredito"
                ),
            )

        source_map: dict[
            PreProcessingProvider,
            tuple[
                dict[str, list[Any]],
                str,
            ],
        ] = {
            PreProcessingProvider.ROW_VALIDATION: (
                row_results,
                "Validação local por linha",
            ),
            PreProcessingProvider.GROUPING: (
                grouping_results,
                "Agrupamento por idEvento",
            ),
            PreProcessingProvider.EVENT_VALIDATION: (
                event_results,
                "Validação do evento agrupado",
            ),
            PreProcessingProvider.REFERENCE_TABLES: (
                reference_results,
                "Tabelas de referência",
            ),
        }

        indexed, source_stage = source_map[provider]
        raw_results = indexed.get(
            definition.code,
            [],
        )

        if not raw_results:
            return (
                PreProcessingEvidence(
                    status=(
                        RuleExecutionStatus
                        .NOT_EXECUTED
                    ),
                    severity=SEVERITY_NOT_EXECUTED,
                    source_stage=(
                        "Integração de pré-processamento"
                    ),
                    message=(
                        "Nenhuma evidência técnica foi "
                        "produzida para a crítica."
                    ),
                    values=(
                        (
                            "provedorEsperado",
                            provider.value,
                        ),
                    ),
                ),
            )

        return tuple(
            self._adapt_result(
                result,
                source_stage=source_stage,
            )
            for result in raw_results
        )

    @staticmethod
    def _bacen_id_evidences(
        grouping: EventGroupingResult,
    ) -> tuple[PreProcessingEvidence, ...]:
        if not grouping.events:
            return (
                PreProcessingEvidence(
                    status=(
                        RuleExecutionStatus
                        .NOT_APPLICABLE
                    ),
                    severity=SEVERITY_INFORMATION,
                    source_stage=(
                        "Dependência externa Bacen"
                    ),
                    message=(
                        "Não existem eventos agrupados "
                        "com idBacen para consultar."
                    ),
                    columns=("idBacen",),
                ),
            )

        return tuple(
            PreProcessingEvidence(
                status=(
                    RuleExecutionStatus
                    .NOT_EXECUTED
                ),
                severity=SEVERITY_NOT_EXECUTED,
                source_stage=(
                    "Dependência externa UNICAD/Bacen"
                ),
                message=(
                    "O identificador foi normalizado "
                    "localmente, mas sua existência não "
                    "foi consultada na base do Bacen."
                ),
                row_numbers=event.row_numbers,
                columns=("idBacen",),
                id_evento=event.id_evento,
                values=(
                    (
                        "idBacen",
                        event.get_serialized_value(
                            "idBacen"
                        ),
                    ),
                ),
            )
            for event in grouping.events
        )

    @staticmethod
    def _cosif_evidences(
        *,
        grouping: EventGroupingResult,
        cosif_field: str,
        internal_field: str,
    ) -> tuple[PreProcessingEvidence, ...]:
        evidences: list[PreProcessingEvidence] = []

        for event in grouping.events:
            for accounting in event.accountings:
                cosif_code = (
                    accounting.get_serialized_value(
                        cosif_field
                    )
                )
                internal_code = (
                    accounting.get_serialized_value(
                        internal_field
                    )
                )

                if cosif_code is None:
                    if internal_code is None:
                        status = (
                            RuleExecutionStatus
                            .NOT_APPLICABLE
                        )
                        severity = SEVERITY_INFORMATION
                        message = (
                            "A contabilização não informou "
                            "a conta interna nem a conta "
                            "COSIF deste lado."
                        )
                    else:
                        status = (
                            RuleExecutionStatus.FAILED
                        )
                        severity = (
                            SEVERITY_BLOCKING_ERROR
                        )
                        message = (
                            "Há conta interna informada, "
                            "mas a conta COSIF correspondente "
                            "não foi preenchida."
                        )

                    evidences.append(
                        PreProcessingEvidence(
                            status=status,
                            severity=severity,
                            source_stage=(
                                "Validação local e "
                                "dependência COSIF"
                            ),
                            message=message,
                            row_numbers=(
                                accounting.row_number,
                            ),
                            columns=(
                                internal_field,
                                cosif_field,
                            ),
                            id_evento=event.id_evento,
                            values=(
                                (
                                    internal_field,
                                    internal_code,
                                ),
                                (
                                    cosif_field,
                                    cosif_code,
                                ),
                            ),
                        )
                    )
                    continue

                evidences.append(
                    PreProcessingEvidence(
                        status=(
                            RuleExecutionStatus
                            .NOT_EXECUTED
                        ),
                        severity=SEVERITY_NOT_EXECUTED,
                        source_stage=(
                            "Dependência externa COSIF"
                        ),
                        message=(
                            "O formato da conta COSIF foi "
                            "validado localmente conforme o "
                            "XSD, mas sua existência no "
                            "cadastro oficial COSIF não foi "
                            "verificada."
                        ),
                        row_numbers=(
                            accounting.row_number,
                        ),
                        columns=(cosif_field,),
                        id_evento=event.id_evento,
                        values=(
                            (
                                cosif_field,
                                cosif_code,
                            ),
                        ),
                    )
                )

        if evidences:
            return tuple(evidences)

        return (
            PreProcessingEvidence(
                status=(
                    RuleExecutionStatus
                    .NOT_APPLICABLE
                ),
                severity=SEVERITY_INFORMATION,
                source_stage=(
                    "Dependência externa COSIF"
                ),
                message=(
                    "O documento não possui "
                    "contabilizações para esta crítica."
                ),
                columns=(cosif_field,),
            ),
        )

    @staticmethod
    def _adapt_result(
        result: Any,
        *,
        source_stage: str,
    ) -> PreProcessingEvidence:
        row_numbers = getattr(
            result,
            "row_numbers",
            None,
        )

        if row_numbers is None:
            row_number = getattr(
                result,
                "row_number",
                None,
            )
            row_numbers = (
                (row_number,)
                if row_number is not None
                else ()
            )

        values = getattr(
            result,
            "values",
            None,
        )

        if values is None:
            values = (
                *getattr(
                    result,
                    "original_values",
                    (),
                ),
                *getattr(
                    result,
                    "normalized_values",
                    (),
                ),
            )

        return PreProcessingEvidence(
            status=result.status,
            severity=result.severity,
            source_stage=source_stage,
            message=result.message,
            row_numbers=tuple(row_numbers),
            columns=tuple(
                getattr(result, "columns", ())
            ),
            id_evento=getattr(
                result,
                "id_evento",
                None,
            ),
            sheet_name=getattr(
                result,
                "sheet_name",
                None,
            ),
            suggestion=getattr(
                result,
                "suggestion",
                None,
            ),
            values=tuple(values),
        )

    @staticmethod
    def _aggregate_status(
        evidences: tuple[
            PreProcessingEvidence,
            ...,
        ],
    ) -> RuleExecutionStatus:
        statuses = {
            evidence.status
            for evidence in evidences
        }

        if RuleExecutionStatus.FAILED in statuses:
            return RuleExecutionStatus.FAILED

        if (
            RuleExecutionStatus.NOT_EXECUTED
            in statuses
        ):
            return RuleExecutionStatus.NOT_EXECUTED

        if RuleExecutionStatus.PASSED in statuses:
            return RuleExecutionStatus.PASSED

        return RuleExecutionStatus.NOT_APPLICABLE

    @staticmethod
    def _index_by_code(
        results: Iterable[Any],
    ) -> dict[str, list[Any]]:
        indexed: dict[str, list[Any]] = defaultdict(list)

        for result in results:
            indexed[result.code].append(result)

        return dict(indexed)

    def _validate_catalog(self) -> None:
        codes = tuple(
            definition.code
            for definition in self.catalog
        )

        if len(codes) != 34:
            raise ValueError(
                "O catálogo deve possuir exatamente "
                "34 críticas de pré-processamento."
            )

        if len(set(codes)) != len(codes):
            raise ValueError(
                "O catálogo possui códigos duplicados."
            )


def validate_pre_processing(
    *,
    header: DocumentHeader,
    profile: RegulatoryVersion,
    row_validation: BaseRowsValidationResult,
    grouping: EventGroupingResult,
    event_validation: EventsValidationResult,
    references: ReferenceTablesValidationResult,
) -> PreProcessingValidationResult:
    """Atalho funcional para integração das críticas."""

    return PreProcessingValidator().validate(
        header=header,
        profile=profile,
        row_validation=row_validation,
        grouping=grouping,
        event_validation=event_validation,
        references=references,
    )
