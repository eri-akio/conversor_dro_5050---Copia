"""Rastreabilidade da reconciliação de regras adiadas."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.base_row_validation import RuleExecutionStatus


@dataclass(frozen=True, slots=True)
class RuleReconciliationRecord:
    """Liga uma decisão provisória por linha à decisão por evento."""

    rule_code: str
    origin: str
    scope: str
    event_id: str | None
    excel_row: int
    provisional_status: RuleExecutionStatus
    reason: str
    dependency: str
    execution_stage: str
    definitive_status: RuleExecutionStatus
    definitive_message: str

    @property
    def is_resolved(self) -> bool:
        return self.definitive_status in {
            RuleExecutionStatus.PASSED,
            RuleExecutionStatus.FAILED,
            RuleExecutionStatus.NOT_APPLICABLE,
        }

    @property
    def blocks_apt(self) -> bool:
        return self.definitive_status in {
            RuleExecutionStatus.FAILED,
            RuleExecutionStatus.NOT_EXECUTED,
        }


@dataclass(frozen=True, slots=True)
class RuleReconciliationResult:
    """Resultado agregado das decisões transferidas para o evento."""

    records: tuple[RuleReconciliationRecord, ...]

    @property
    def unresolved_records(self) -> tuple[RuleReconciliationRecord, ...]:
        return tuple(
            record for record in self.records
            if not record.is_resolved
        )

    @property
    def failed_records(self) -> tuple[RuleReconciliationRecord, ...]:
        return tuple(
            record for record in self.records
            if record.definitive_status == RuleExecutionStatus.FAILED
        )

    @property
    def is_fully_reconciled(self) -> bool:
        return not self.unresolved_records

    @property
    def blocks_apt(self) -> bool:
        return any(record.blocks_apt for record in self.records)

