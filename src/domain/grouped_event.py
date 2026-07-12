"""Modelos do agrupamento das linhas por ``idEvento``."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.base_row_validation import (
    BaseRowKind,
    RuleExecutionStatus,
)


@dataclass(frozen=True, slots=True)
class ResolvedEventField:
    """Valor de evento resolvido a partir de uma ou mais linhas."""

    column_name: str
    normalized_value: Any
    serialized_value: str | None
    source_rows: tuple[int, ...]
    absent_rows: tuple[int, ...]
    invalid_rows: tuple[int, ...]
    distinct_serialized_values: tuple[str, ...]

    @property
    def has_conflict(self) -> bool:
        return len(self.distinct_serialized_values) > 1

    @property
    def is_resolved(self) -> bool:
        return (
            not self.has_conflict
            and not self.invalid_rows
            and self.serialized_value is not None
        )


@dataclass(frozen=True, slots=True)
class GroupedProbability:
    """Probabilidade única do evento após a deduplicação controlada."""

    probability_code: str
    value_risk: Decimal | None
    source_rows: tuple[int, ...]
    distinct_values: tuple[Decimal, ...]

    @property
    def has_conflict(self) -> bool:
        return len(self.distinct_values) > 1

    @property
    def is_resolved(self) -> bool:
        return not self.has_conflict and self.value_risk is not None


@dataclass(frozen=True, slots=True)
class GroupedAccounting:
    """Lançamento contábil preservado na linha original."""

    row_number: int
    normalized_values: Mapping[str, Any]
    serialized_values: Mapping[str, str | None]

    def get_value(
        self,
        field_name: str,
        default: Any = None,
    ) -> Any:
        return self.normalized_values.get(field_name, default)

    def get_serialized_value(
        self,
        field_name: str,
        default: str | None = None,
    ) -> str | None:
        return self.serialized_values.get(field_name, default)

    @property
    def movement_total(self) -> Decimal:
        total = Decimal('0')
        for field_name in (
            'valorPerdaEfetiva',
            'valorProvisao',
            'valorRecuperacao',
        ):
            value = self.get_value(field_name)
            if isinstance(value, Decimal):
                total += value
        return total


@dataclass(frozen=True, slots=True)
class EventRuleResult:
    """Resultado de regra estrutural ou regulatória no nível do evento."""

    code: str
    description: str
    source: str
    severity: str
    status: RuleExecutionStatus
    id_evento: str | None
    row_numbers: tuple[int, ...]
    columns: tuple[str, ...]
    message: str
    suggestion: str | None = None
    values: tuple[tuple[str, Any], ...] = ()

    @property
    def blocks_processing(self) -> bool:
        return (
            self.status == RuleExecutionStatus.FAILED
            and self.severity in {'ERRO IMPEDITIVO', 'ERRO'}
        )


@dataclass(frozen=True, slots=True)
class GroupedEvent:
    """Evento único construído a partir de todas as linhas do mesmo ID."""

    id_evento: str
    profile_code: str
    row_kind: BaseRowKind | None
    row_numbers: tuple[int, ...]
    source_names: tuple[str, ...]
    event_fields: Mapping[str, ResolvedEventField]
    probabilities: tuple[GroupedProbability, ...]
    accountings: tuple[GroupedAccounting, ...]
    grouping_results: tuple[EventRuleResult, ...]

    def get_field(self, column_name: str) -> ResolvedEventField:
        try:
            return self.event_fields[column_name]
        except KeyError as error:
            raise KeyError(
                f'Campo de evento não agrupado: {column_name}'
            ) from error

    def get_value(
        self,
        column_name: str,
        default: Any = None,
    ) -> Any:
        field = self.event_fields.get(column_name)
        if field is None or field.has_conflict:
            return default
        return (
            default
            if field.serialized_value is None
            else field.normalized_value
        )

    def get_serialized_value(
        self,
        column_name: str,
        default: str | None = None,
    ) -> str | None:
        field = self.event_fields.get(column_name)
        if field is None or field.has_conflict:
            return default
        return field.serialized_value or default

    @property
    def is_grouping_valid(self) -> bool:
        return not any(
            result.blocks_processing
            for result in self.grouping_results
        )

    @property
    def probability_sum(self) -> Decimal | None:
        if any(item.has_conflict for item in self.probabilities):
            return None
        return sum(
            (
                item.value_risk or Decimal('0')
                for item in self.probabilities
            ),
            Decimal('0'),
        )


@dataclass(frozen=True, slots=True)
class EventGroupingResult:
    """Resultado do agrupamento de toda a aba Base."""

    profile_code: str
    events: tuple[GroupedEvent, ...]
    ungrouped_row_numbers: tuple[int, ...]
    rule_results: tuple[EventRuleResult, ...]

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def valid_event_count(self) -> int:
        return sum(event.is_grouping_valid for event in self.events)

    @property
    def invalid_event_count(self) -> int:
        return self.event_count - self.valid_event_count

    @property
    def is_valid(self) -> bool:
        return (
            not self.ungrouped_row_numbers
            and self.invalid_event_count == 0
            and not any(
                result.blocks_processing
                for result in self.rule_results
            )
        )

    @property
    def status_counts(self) -> Mapping[RuleExecutionStatus, int]:
        counter: Counter[RuleExecutionStatus] = Counter(
            result.status
            for result in self.rule_results
        )
        return MappingProxyType(dict(counter))


@dataclass(frozen=True, slots=True)
class EventValidationResult:
    """Validação das regras aplicáveis a um evento agrupado."""

    id_evento: str
    row_numbers: tuple[int, ...]
    grouping_valid: bool
    rule_results: tuple[EventRuleResult, ...]

    @property
    def failed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def not_executed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def is_valid(self) -> bool:
        return (
            self.grouping_valid
            and not any(
                result.blocks_processing
                for result in self.rule_results
            )
        )

    @property
    def is_fully_verified(self) -> bool:
        return self.is_valid and not self.not_executed_rules


@dataclass(frozen=True, slots=True)
class EventsValidationResult:
    """Resultado agregado das regras executadas no nível de evento."""

    profile_code: str
    events: tuple[EventValidationResult, ...]
    rule_results: tuple[EventRuleResult, ...]

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def valid_event_count(self) -> int:
        return sum(event.is_valid for event in self.events)

    @property
    def invalid_event_count(self) -> int:
        return self.event_count - self.valid_event_count

    @property
    def is_valid(self) -> bool:
        return self.invalid_event_count == 0

    @property
    def is_fully_verified(self) -> bool:
        return all(event.is_fully_verified for event in self.events)

    @property
    def failed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def not_executed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def status_counts(self) -> Mapping[RuleExecutionStatus, int]:
        counter: Counter[RuleExecutionStatus] = Counter(
            result.status
            for result in self.rule_results
        )
        return MappingProxyType(dict(counter))
