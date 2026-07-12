"""Resultados da validação de obrigatoriedades e relações por linha."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


class RuleExecutionStatus(StrEnum):
    """Estado de execução de uma regra local."""

    PASSED = "APROVADA"
    FAILED = "REPROVADA"
    NOT_APPLICABLE = "NÃO APLICÁVEL"
    NOT_EXECUTED = "REGRA NÃO EXECUTADA"
    DEFERRED = "ADIADA"


class BaseRowKind(StrEnum):
    """Tipo lógico da linha no perfil selecionado."""

    INDIVIDUALIZED = "EVENTO INDIVIDUALIZADO"
    EXCLUDED = "EVENTO EXCLUÍDO"


@dataclass(frozen=True, slots=True)
class RowRuleResult:
    """Resultado rastreável de uma regra aplicada a uma linha."""

    code: str
    description: str
    source: str
    severity: str
    status: RuleExecutionStatus
    row_number: int
    id_evento: str | None
    row_kind: BaseRowKind
    columns: tuple[str, ...]
    message: str
    suggestion: str | None = None
    original_values: tuple[tuple[str, Any], ...] = ()
    normalized_values: tuple[tuple[str, Any], ...] = ()

    @property
    def blocks_processing(self) -> bool:
        """Somente falhas locais com gravidade de erro bloqueiam a linha."""

        return (
            self.status == RuleExecutionStatus.FAILED
            and self.severity in {"ERRO IMPEDITIVO", "ERRO"}
        )


@dataclass(frozen=True, slots=True)
class BaseRowValidationResult:
    """Validação local de uma única linha normalizada."""

    row_number: int
    id_evento: str | None
    row_kind: BaseRowKind
    normalization_valid: bool
    rule_results: tuple[RowRuleResult, ...]

    @property
    def failed_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def not_executed_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def deferred_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.DEFERRED
        )

    @property
    def is_locally_valid(self) -> bool:
        return (
            self.normalization_valid
            and not any(
                result.blocks_processing
                for result in self.rule_results
            )
        )

    @property
    def is_fully_verified(self) -> bool:
        return (
            self.is_locally_valid
            and not self.not_executed_rules
        )


@dataclass(frozen=True, slots=True)
class BaseRowsValidationResult:
    """Resultado agregado da validação de todas as linhas."""

    profile_code: str
    rows: tuple[BaseRowValidationResult, ...]
    rule_results: tuple[RowRuleResult, ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def locally_valid_row_count(self) -> int:
        return sum(row.is_locally_valid for row in self.rows)

    @property
    def invalid_row_count(self) -> int:
        return self.row_count - self.locally_valid_row_count

    @property
    def is_locally_valid(self) -> bool:
        return self.invalid_row_count == 0

    @property
    def is_fully_verified(self) -> bool:
        return all(row.is_fully_verified for row in self.rows)

    @property
    def status_counts(self) -> Mapping[RuleExecutionStatus, int]:
        counter: Counter[RuleExecutionStatus] = Counter(
            result.status
            for result in self.rule_results
        )
        return MappingProxyType(dict(counter))

    @property
    def failed_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def not_executed_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def deferred_rules(self) -> tuple[RowRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.DEFERRED
        )
