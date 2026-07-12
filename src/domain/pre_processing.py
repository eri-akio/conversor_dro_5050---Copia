"""Modelos do catálogo e da execução das críticas de pré-processamento."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.base_row_validation import (
    RuleExecutionStatus,
)
from src.domain.regulatory_version import YearMonth


class PreProcessingExecutionClass(StrEnum):
    """Dependência necessária para concluir uma crítica."""

    LOCAL = "LOCAL"
    PARTIAL = "PARCIAL"
    EXTERNAL = "EXTERNA"
    DOCUMENT_CONFLICT = "CONFLITO DOCUMENTAL"


class PreProcessingProvider(StrEnum):
    """Componente responsável pela evidência técnica."""

    ROW_VALIDATION = "VALIDAÇÃO POR LINHA"
    GROUPING = "AGRUPAMENTO"
    EVENT_VALIDATION = "VALIDAÇÃO POR EVENTO"
    REFERENCE_TABLES = "TABELAS DE REFERÊNCIA"
    EXTERNAL_CONGLOMERATE = "UNICAD — CONGLOMERADO"
    EXTERNAL_BACEN_ID = "UNICAD/BACEN — ID"
    COSIF_DEBIT = "CADASTRO COSIF — DÉBITO"
    COSIF_CREDIT = "CADASTRO COSIF — CRÉDITO"


@dataclass(frozen=True, slots=True)
class PreProcessingRuleDefinition:
    """Definição oficial enriquecida com metadados técnicos."""

    code: str
    document_code: str
    official_type: str
    official_description: str
    confronted_base: str
    start_label: str
    start_data_base: YearMonth
    scope: str
    execution_class: PreProcessingExecutionClass
    dependency: str | None
    provider: PreProcessingProvider
    source_path: Path

    def applies_to(self, data_base: str) -> bool:
        """Confirma a vigência sem usar comparação textual."""

        return (
            YearMonth.parse(data_base)
            >= self.start_data_base
        )


@dataclass(frozen=True, slots=True)
class PreProcessingEvidence:
    """Resultado elementar vindo de uma etapa já executada."""

    status: RuleExecutionStatus
    severity: str
    source_stage: str
    message: str
    row_numbers: tuple[int, ...] = ()
    columns: tuple[str, ...] = ()
    id_evento: str | None = None
    sheet_name: str | None = None
    suggestion: str | None = None
    values: tuple[tuple[str, Any], ...] = ()

    @property
    def blocks_processing(self) -> bool:
        return (
            self.status
            == RuleExecutionStatus.FAILED
            and self.severity
            in {"ERRO IMPEDITIVO", "ERRO"}
        )


@dataclass(frozen=True, slots=True)
class PreProcessingRuleResult:
    """Resultado consolidado de uma crítica oficial."""

    definition: PreProcessingRuleDefinition
    status: RuleExecutionStatus
    evidences: tuple[PreProcessingEvidence, ...]

    @property
    def code(self) -> str:
        return self.definition.code

    @property
    def description(self) -> str:
        return self.definition.official_description

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    evidence.id_evento
                    for evidence in self.evidences
                    if evidence.id_evento
                }
            )
        )

    @property
    def row_numbers(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    row_number
                    for evidence in self.evidences
                    for row_number in (
                        evidence.row_numbers
                    )
                }
            )
        )

    @property
    def occurrence_count(self) -> int:
        return sum(
            evidence.status
            in {
                RuleExecutionStatus.FAILED,
                RuleExecutionStatus.NOT_EXECUTED,
            }
            for evidence in self.evidences
        )

    @property
    def blocks_apt(self) -> bool:
        return self.status in {
            RuleExecutionStatus.FAILED,
            RuleExecutionStatus.NOT_EXECUTED,
        }

    @property
    def has_local_failure(self) -> bool:
        return self.status == RuleExecutionStatus.FAILED


@dataclass(frozen=True, slots=True)
class PreProcessingValidationResult:
    """Resultado agregado das 34 críticas oficiais."""

    profile_code: str
    data_base: str
    source_path: Path
    rule_results: tuple[
        PreProcessingRuleResult,
        ...,
    ]

    @property
    def rule_count(self) -> int:
        return len(self.rule_results)

    @property
    def evidence_count(self) -> int:
        return sum(
            len(result.evidences)
            for result in self.rule_results
        )

    @property
    def status_counts(
        self,
    ) -> Mapping[RuleExecutionStatus, int]:
        counter: Counter[RuleExecutionStatus] = Counter(
            result.status
            for result in self.rule_results
        )
        return MappingProxyType(dict(counter))

    @property
    def passed_rules(
        self,
    ) -> tuple[PreProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.PASSED
        )

    @property
    def failed_rules(
        self,
    ) -> tuple[PreProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.FAILED
        )

    @property
    def not_applicable_rules(
        self,
    ) -> tuple[PreProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.NOT_APPLICABLE
        )

    @property
    def not_executed_rules(
        self,
    ) -> tuple[PreProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def is_locally_valid(self) -> bool:
        return not self.failed_rules

    @property
    def is_fully_verified(self) -> bool:
        return (
            self.is_locally_valid
            and not self.not_executed_rules
        )

    @property
    def blocks_apt(self) -> bool:
        return not self.is_fully_verified

    def get_rule(
        self,
        code: str,
    ) -> PreProcessingRuleResult:
        for result in self.rule_results:
            if result.code == code:
                return result

        raise KeyError(
            f"Crítica de pré-processamento não encontrada: {code}"
        )
