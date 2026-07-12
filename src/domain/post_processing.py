"""Modelos do catálogo e da execução das críticas de pós-processamento."""

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


class PostProcessingExecutionClass(StrEnum):
    """Dependência necessária para concluir a crítica."""

    LOCAL = "LOCAL"
    CONSOLIDATED = "EVENTOS CONSOLIDADOS"
    HISTORICAL = "HISTÓRICO DA DATA-BASE ANTERIOR"


class PostProcessingProvider(StrEnum):
    """Componente responsável pela evidência técnica."""

    CUSTOM_EVENT = "REGRA LOCAL DO EVENTO"
    ROW_VALIDATION = "VALIDAÇÃO POR LINHA"
    EVENT_FINANCIAL = "VALIDAÇÃO FINANCEIRA"
    CONSOLIDATED = "EVENTOS CONSOLIDADOS"
    HISTORICAL = "HISTÓRICO"


@dataclass(frozen=True, slots=True)
class PostProcessingRuleDefinition:
    """Definição oficial enriquecida com metadados técnicos."""

    code: str
    official_type: str
    official_description: str
    evaluated_fields: str
    observations: str
    scope: str
    execution_class: PostProcessingExecutionClass
    dependency: str | None
    provider: PostProcessingProvider
    source_path: Path
    source_rule_code: str | None = None

    @property
    def is_clarification(self) -> bool:
        return self.official_type == "Esclarecimento"

    @property
    def is_inconsistency(self) -> bool:
        return self.official_type == "Inconsistência"


@dataclass(frozen=True, slots=True)
class PostProcessingEvidence:
    """Evidência individual de uma crítica de pós-processamento."""

    status: RuleExecutionStatus
    severity: str
    source_stage: str
    message: str
    sheet_name: str | None = None
    row_numbers: tuple[int, ...] = ()
    columns: tuple[str, ...] = ()
    id_evento: str | None = None
    category_level_1: str | None = None
    suggestion: str | None = None
    original_values: tuple[tuple[str, Any], ...] = ()
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
class PostProcessingRuleResult:
    """Resultado consolidado de uma crítica oficial."""

    definition: PostProcessingRuleDefinition
    status: RuleExecutionStatus
    evidences: tuple[PostProcessingEvidence, ...]

    @property
    def code(self) -> str:
        return self.definition.code

    @property
    def description(self) -> str:
        return self.definition.official_description

    @property
    def row_numbers(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    row_number
                    for evidence in self.evidences
                    for row_number in evidence.row_numbers
                }
            )
        )

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
    def has_blocking_failure(self) -> bool:
        return any(
            evidence.blocks_processing
            for evidence in self.evidences
        )

    @property
    def has_warning_failure(self) -> bool:
        return (
            self.status == RuleExecutionStatus.FAILED
            and not self.has_blocking_failure
        )

    @property
    def blocks_apt(self) -> bool:
        return (
            self.status
            == RuleExecutionStatus.NOT_EXECUTED
            or self.has_blocking_failure
        )


@dataclass(frozen=True, slots=True)
class PostProcessingValidationResult:
    """Resultado agregado das 26 críticas oficiais."""

    profile_code: str
    data_base: str
    source_path: Path
    rule_results: tuple[
        PostProcessingRuleResult,
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
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.PASSED
        )

    @property
    def failed_rules(
        self,
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.FAILED
        )

    @property
    def blocking_failed_rules(
        self,
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if result.has_blocking_failure
        )

    @property
    def warning_failed_rules(
        self,
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if result.has_warning_failure
        )

    @property
    def not_applicable_rules(
        self,
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.NOT_APPLICABLE
        )

    @property
    def not_executed_rules(
        self,
    ) -> tuple[PostProcessingRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status
            == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def is_locally_valid(self) -> bool:
        return not self.blocking_failed_rules

    @property
    def is_fully_verified(self) -> bool:
        return (
            self.is_locally_valid
            and not self.not_executed_rules
        )

    @property
    def blocks_apt(self) -> bool:
        return (
            not self.is_locally_valid
            or bool(self.not_executed_rules)
        )

    def get_rule(
        self,
        code: str,
    ) -> PostProcessingRuleResult:
        for result in self.rule_results:
            if result.code == code:
                return result

        raise KeyError(
            "Crítica de pós-processamento "
            f"não encontrada: {code}"
        )
