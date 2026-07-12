"""Reconciliação de regras transferidas da linha para o evento."""

from __future__ import annotations

from collections import defaultdict

from src.domain.base_row_validation import (
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.grouped_event import EventsValidationResult
from src.domain.rule_reconciliation import (
    RuleReconciliationRecord,
    RuleReconciliationResult,
)


DEFERRED_EVENT_RULE_CODES = frozenset({
    "DRO001312",
    "DRO001314",
    "DRO001452",
})


class RuleReconciliationService:
    """Resolve decisões adiadas usando código e ``idEvento``."""

    def reconcile(
        self,
        *,
        row_validation: BaseRowsValidationResult,
        event_validation: EventsValidationResult,
    ) -> RuleReconciliationResult:
        event_results: dict[
            tuple[str, str | None],
            list[object],
        ] = defaultdict(list)

        for result in event_validation.rule_results:
            event_results[(
                result.code,
                result.id_evento,
            )].append(result)

        records = tuple(
            self._reconcile_record(
                deferred,
                event_results.get((
                    deferred.code,
                    deferred.id_evento,
                ), []),
            )
            for deferred in row_validation.deferred_rules
            if deferred.code in DEFERRED_EVENT_RULE_CODES
        )

        return RuleReconciliationResult(records=records)

    def _reconcile_record(
        self,
        deferred: object,
        candidates: list[object],
    ) -> RuleReconciliationRecord:
        definitive = self._definitive_result(candidates)

        if definitive is None:
            definitive_status = RuleExecutionStatus.NOT_EXECUTED
            definitive_message = (
                "Nenhum resultado definitivo foi produzido no nível "
                "do evento."
            )
        else:
            definitive_status = definitive.status
            definitive_message = definitive.message

        return RuleReconciliationRecord(
            rule_code=deferred.code,
            origin=deferred.source,
            scope="LINHA",
            event_id=deferred.id_evento,
            excel_row=deferred.row_number,
            provisional_status=RuleExecutionStatus.DEFERRED,
            reason=deferred.message,
            dependency="EVENTO COMPLETO",
            execution_stage="VALIDAÇÃO POR EVENTO",
            definitive_status=definitive_status,
            definitive_message=definitive_message,
        )

    @staticmethod
    def _definitive_result(
        candidates: list[object],
    ) -> object | None:
        priority = (
            RuleExecutionStatus.FAILED,
            RuleExecutionStatus.NOT_EXECUTED,
            RuleExecutionStatus.PASSED,
            RuleExecutionStatus.NOT_APPLICABLE,
        )

        for status in priority:
            for candidate in candidates:
                if candidate.status == status:
                    return candidate

        return None


def reconcile_deferred_rules(
    *,
    row_validation: BaseRowsValidationResult,
    event_validation: EventsValidationResult,
) -> RuleReconciliationResult:
    """Atalho funcional do reconciliador padrão."""

    return RuleReconciliationService().reconcile(
        row_validation=row_validation,
        event_validation=event_validation,
    )

