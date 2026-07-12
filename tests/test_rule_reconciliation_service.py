"""Testes da reconciliação de regras adiadas."""

from __future__ import annotations

from types import SimpleNamespace

from src.domain.base_row_validation import RuleExecutionStatus
from src.services.rule_reconciliation_service import (
    reconcile_deferred_rules,
)


def deferred_rule(
    code: str = "DRO001312",
    event_id: str = "EVT-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        code=code,
        source="Crítica de pré-processamento",
        status=RuleExecutionStatus.DEFERRED,
        id_evento=event_id,
        row_number=7,
        message="Depende do conjunto completo de linhas.",
    )


def event_rule(
    status: RuleExecutionStatus,
    code: str = "DRO001312",
    event_id: str = "EVT-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        code=code,
        status=status,
        id_evento=event_id,
        message=f"Resultado por evento: {status.value}.",
    )


def reconcile(
    deferred: tuple[SimpleNamespace, ...],
    definitive: tuple[SimpleNamespace, ...],
):
    return reconcile_deferred_rules(
        row_validation=SimpleNamespace(
            deferred_rules=deferred,
        ),
        event_validation=SimpleNamespace(
            rule_results=definitive,
        ),
    )


def test_deferred_rule_is_reconciled_as_approved() -> None:
    result = reconcile(
        (deferred_rule(),),
        (event_rule(RuleExecutionStatus.PASSED),),
    )

    record = result.records[0]
    assert record.provisional_status == RuleExecutionStatus.DEFERRED
    assert record.definitive_status == RuleExecutionStatus.PASSED
    assert record.scope == "LINHA"
    assert record.event_id == "EVT-1"
    assert record.excel_row == 7
    assert record.execution_stage == "VALIDAÇÃO POR EVENTO"
    assert result.is_fully_reconciled
    assert not result.blocks_apt


def test_deferred_rule_is_reconciled_as_reproved() -> None:
    result = reconcile(
        (deferred_rule("DRO001314"),),
        (
            event_rule(
                RuleExecutionStatus.FAILED,
                "DRO001314",
            ),
        ),
    )

    assert result.records[0].definitive_status == (
        RuleExecutionStatus.FAILED
    )
    assert result.is_fully_reconciled
    assert result.blocks_apt
    assert result.failed_records


def test_deferred_rule_without_event_result_remains_pending() -> None:
    result = reconcile((deferred_rule("DRO001452"),), ())

    record = result.records[0]
    assert record.definitive_status == (
        RuleExecutionStatus.NOT_EXECUTED
    )
    assert not record.is_resolved
    assert not result.is_fully_reconciled
    assert result.blocks_apt


def test_definitive_not_executed_remains_pending() -> None:
    result = reconcile(
        (deferred_rule(),),
        (event_rule(RuleExecutionStatus.NOT_EXECUTED),),
    )

    assert result.unresolved_records
    assert result.blocks_apt


def test_matching_uses_rule_code_and_event_id() -> None:
    result = reconcile(
        (deferred_rule(event_id="EVT-1"),),
        (
            event_rule(
                RuleExecutionStatus.PASSED,
                event_id="EVT-2",
            ),
        ),
    )

    assert result.unresolved_records

