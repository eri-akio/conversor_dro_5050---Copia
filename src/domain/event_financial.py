"""Modelos dos totais, contabilizações e saldos do evento."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.grouped_event import EventRuleResult


ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class AccountingDayBalance:
    """Movimentos e saldos acumulados de uma data contábil.

    Como a fonte contém apenas a data, e não horário ou sequência
    intradiária, o menor saldo possível considera que os lançamentos
    negativos poderiam ocorrer antes dos positivos no mesmo dia.
    """

    accounting_date: date
    row_numbers: tuple[int, ...]
    loss_movements: tuple[Decimal, ...]
    provision_movements: tuple[Decimal, ...]
    recovery_movements: tuple[Decimal, ...]
    opening_loss_balance: Decimal
    closing_loss_balance: Decimal
    minimum_possible_loss_balance: Decimal
    opening_provision_balance: Decimal
    closing_provision_balance: Decimal
    minimum_possible_provision_balance: Decimal
    closing_recovery_balance: Decimal

    @property
    def loss_movement(self) -> Decimal:
        return sum(self.loss_movements, ZERO)

    @property
    def provision_movement(self) -> Decimal:
        return sum(self.provision_movements, ZERO)

    @property
    def recovery_movement(self) -> Decimal:
        return sum(self.recovery_movements, ZERO)

    @property
    def loss_order_is_ambiguous(self) -> bool:
        """Alguma ordem pode negativar, mas o fechamento não."""

        return (
            self.minimum_possible_loss_balance < ZERO
            and self.closing_loss_balance >= ZERO
        )

    @property
    def provision_order_is_ambiguous(self) -> bool:
        """Alguma ordem pode negativar, mas o fechamento não."""

        return (
            self.minimum_possible_provision_balance < ZERO
            and self.closing_provision_balance >= ZERO
        )


@dataclass(frozen=True, slots=True)
class EventFinancialSummary:
    """Valores declarados, somados e acumulados de um evento."""

    id_evento: str
    row_numbers: tuple[int, ...]
    accounting_row_numbers: tuple[int, ...]
    declared_total_loss: Decimal | None
    declared_total_provision: Decimal | None
    declared_total_recovery: Decimal | None
    accounting_loss_sum: Decimal
    accounting_provision_sum: Decimal
    accounting_recovery_sum: Decimal
    daily_balances: tuple[AccountingDayBalance, ...]
    undated_accounting_rows: tuple[int, ...]

    @property
    def accounting_count(self) -> int:
        return len(self.accounting_row_numbers)

    @property
    def loss_difference(self) -> Decimal | None:
        if self.declared_total_loss is None:
            return None
        return self.declared_total_loss - self.accounting_loss_sum

    @property
    def provision_difference(self) -> Decimal | None:
        if self.declared_total_provision is None:
            return None
        return (
            self.declared_total_provision
            - self.accounting_provision_sum
        )

    @property
    def recovery_difference(self) -> Decimal | None:
        if self.declared_total_recovery is None:
            return None
        return (
            self.declared_total_recovery
            - self.accounting_recovery_sum
        )

    @property
    def final_loss_balance(self) -> Decimal:
        if not self.daily_balances:
            return ZERO
        return self.daily_balances[-1].closing_loss_balance

    @property
    def final_provision_balance(self) -> Decimal:
        if not self.daily_balances:
            return ZERO
        return self.daily_balances[-1].closing_provision_balance

    @property
    def final_recovery_balance(self) -> Decimal:
        if not self.daily_balances:
            return ZERO
        return self.daily_balances[-1].closing_recovery_balance


@dataclass(frozen=True, slots=True)
class EventFinancialValidationResult:
    """Validação financeira de um evento agrupado."""

    id_evento: str
    row_numbers: tuple[int, ...]
    summary: EventFinancialSummary
    rule_results: tuple[EventRuleResult, ...]

    @property
    def failed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def blocking_failures(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if result.blocks_processing
        )

    @property
    def warning_failures(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if not result.blocks_processing
        )

    @property
    def not_executed_rules(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def is_valid(self) -> bool:
        return not self.blocking_failures

    @property
    def is_fully_verified(self) -> bool:
        return self.is_valid and not self.not_executed_rules


@dataclass(frozen=True, slots=True)
class EventsFinancialValidationResult:
    """Resultado financeiro agregado de todos os eventos."""

    profile_code: str
    events: tuple[EventFinancialValidationResult, ...]
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
        return all(
            event.is_fully_verified
            for event in self.events
        )

    @property
    def failed_rules(self) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def blocking_failures(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if result.blocks_processing
        )

    @property
    def warning_failures(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.failed_rules
            if not result.blocks_processing
        )

    @property
    def not_executed_rules(
        self,
    ) -> tuple[EventRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
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
