"""Testes dos totais, contabilizações e saldos do evento."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.domain.base_row_validation import RuleExecutionStatus
from src.validators import validate_event_financials
from tests.test_event_grouping import (
    base_values,
    process,
)


def financial_result(
    tmp_path: Path,
    rows: list[dict[str, object]],
    *,
    data_base: str = "2026-06",
):
    grouping, _ = process(
        tmp_path,
        rows,
        data_base=data_base,
    )
    profile_code = grouping.profile_code

    from src.services.version_resolver import resolve_version

    profile = resolve_version(data_base).profile
    assert profile is not None
    assert profile.code == profile_code

    return validate_event_financials(
        grouping,
        profile,
    )


def rule_for(result, code: str):
    matches = [
        item
        for item in result.rule_results
        if item.code == code
    ]
    assert len(matches) == 1
    return matches[0]


def test_matching_totals_and_accountings_pass(
    tmp_path: Path,
) -> None:
    result = financial_result(
        tmp_path,
        [base_values()],
    )
    event = result.events[0]
    summary = event.summary

    assert result.is_valid
    assert summary.declared_total_loss == Decimal("1500.00")
    assert summary.accounting_loss_sum == Decimal("1500.00")
    assert summary.accounting_provision_sum == Decimal("500.00")
    assert summary.accounting_recovery_sum == Decimal("0.00")
    assert summary.loss_difference == Decimal("0.00")
    assert rule_for(
        event,
        "DRO000015",
    ).status == RuleExecutionStatus.PASSED


def test_total_mismatch_fails_dro000015(
    tmp_path: Path,
) -> None:
    values = base_values()
    values["totalPerdaEfetiva"] = "1600,00"

    result = financial_result(
        tmp_path,
        [values],
    )
    event = result.events[0]

    failure = rule_for(event, "DRO000015")
    assert failure.status == RuleExecutionStatus.FAILED
    assert failure.blocks_processing
    assert event.summary.loss_difference == Decimal("100.00")
    assert not result.is_valid


def test_official_negative_total_thresholds(
    tmp_path: Path,
) -> None:
    accepted = base_values()
    accepted["totalPerdaEfetiva"] = "-10,00"
    accepted["valorPerdaEfetiva"] = "-10,00"
    accepted["totalProvisao"] = "-10,00"
    accepted["valorProvisao"] = "-10,00"
    accepted["valorTotalRisco"] = "9980,00"

    accepted_result = financial_result(
        tmp_path,
        [accepted],
    ).events[0]

    assert rule_for(
        accepted_result,
        "DRO000011",
    ).status == RuleExecutionStatus.PASSED
    assert rule_for(
        accepted_result,
        "DRO000012",
    ).status == RuleExecutionStatus.PASSED

    rejected = base_values()
    rejected["idEvento"] = "EVT0002"
    rejected["totalPerdaEfetiva"] = "-10,01"
    rejected["valorPerdaEfetiva"] = "-10,01"
    rejected["totalProvisao"] = "-10,01"
    rejected["valorProvisao"] = "-10,01"
    rejected["valorTotalRisco"] = "9979,98"

    rejected_result = financial_result(
        tmp_path,
        [rejected],
    ).events[0]

    assert rule_for(
        rejected_result,
        "DRO000011",
    ).status == RuleExecutionStatus.FAILED
    assert rule_for(
        rejected_result,
        "DRO000012",
    ).status == RuleExecutionStatus.FAILED


def test_positive_recovery_and_excess_recovery_fail(
    tmp_path: Path,
) -> None:
    positive = base_values()
    positive["totalRecuperado"] = "100,00"
    positive["valorRecuperacao"] = "100,00"

    positive_event = financial_result(
        tmp_path,
        [positive],
    ).events[0]

    assert rule_for(
        positive_event,
        "DRO000013",
    ).status == RuleExecutionStatus.FAILED

    excessive = base_values()
    excessive["idEvento"] = "EVT0002"
    excessive["totalPerdaEfetiva"] = "100,00"
    excessive["valorPerdaEfetiva"] = "100,00"
    excessive["totalProvisao"] = "0,00"
    excessive["valorProvisao"] = "0,00"
    excessive["totalRecuperado"] = "-150,00"
    excessive["valorRecuperacao"] = "-150,00"
    excessive["valorTotalRisco"] = "10000,00"

    excessive_event = financial_result(
        tmp_path,
        [excessive],
    ).events[0]

    assert rule_for(
        excessive_event,
        "DRO000014",
    ).status == RuleExecutionStatus.FAILED


def test_negative_accumulated_loss_fails(
    tmp_path: Path,
) -> None:
    first = base_values()
    first["totalPerdaEfetiva"] = "-50,00"
    first["totalProvisao"] = "0,00"
    first["totalRecuperado"] = "0,00"
    first["valorTotalRisco"] = "10000,00"
    first["valorPerdaEfetiva"] = "100,00"
    first["valorProvisao"] = "0,00"

    second = dict(first)
    second["probabilidadePerda"] = None
    second["valorRisco"] = None
    second["dataContabilizacao"] = "2025-06-20"
    second["valorPerdaEfetiva"] = "-150,00"

    event = financial_result(
        tmp_path,
        [first, second],
    ).events[0]

    balance_rule = rule_for(
        event,
        "DRO000023",
    )
    assert balance_rule.status == RuleExecutionStatus.FAILED
    assert event.summary.final_loss_balance == Decimal("-50.00")


def test_negative_provision_balance_is_warning(
    tmp_path: Path,
) -> None:
    first = base_values()
    first["totalPerdaEfetiva"] = "1500,00"
    first["totalProvisao"] = "-50,00"
    first["valorTotalRisco"] = "9950,00"
    first["valorProvisao"] = "100,00"

    second = dict(first)
    second["probabilidadePerda"] = None
    second["valorRisco"] = None
    second["dataContabilizacao"] = "2025-06-20"
    second["valorPerdaEfetiva"] = "0,00"
    second["valorProvisao"] = "-150,00"

    result = financial_result(
        tmp_path,
        [first, second],
    )
    event = result.events[0]
    warning = rule_for(event, "DRO000024")

    assert warning.status == RuleExecutionStatus.FAILED
    assert warning.severity == "AVISO"
    assert not warning.blocks_processing
    assert warning in result.warning_failures


def test_same_date_without_intraday_order_is_not_executed(
    tmp_path: Path,
) -> None:
    first = base_values()
    first["totalPerdaEfetiva"] = "50,00"
    first["valorPerdaEfetiva"] = "-100,00"

    second = dict(first)
    second["probabilidadePerda"] = None
    second["valorRisco"] = None
    second["valorPerdaEfetiva"] = "150,00"

    event = financial_result(
        tmp_path,
        [first, second],
    ).events[0]

    rule = rule_for(event, "DRO000023")
    assert rule.status == RuleExecutionStatus.NOT_EXECUTED
    assert event.summary.final_loss_balance == Decimal("50.00")
    assert not event.is_fully_verified


def test_no_accountings_compares_zero_totals_and_skips_balances(
    tmp_path: Path,
) -> None:
    values = base_values()
    values["totalPerdaEfetiva"] = "0,00"
    values["totalProvisao"] = "0,00"
    values["totalRecuperado"] = "0,00"

    for field_name in (
        "dataContabilizacao",
        "contaBalAnaliticoDebito",
        "contaBalAnaliticoCredito",
        "contaCosifDebito",
        "contaCosifCredito",
        "valorPerdaEfetiva",
        "valorProvisao",
        "valorRecuperacao",
        "fonteRecuperacao",
    ):
        values[field_name] = None

    event = financial_result(
        tmp_path,
        [values],
    ).events[0]

    assert event.summary.accounting_count == 0
    assert rule_for(
        event,
        "DRO000015",
    ).status == RuleExecutionStatus.PASSED
    assert rule_for(
        event,
        "DRO000023",
    ).status == RuleExecutionStatus.NOT_APPLICABLE
    assert rule_for(
        event,
        "DRO000024",
    ).status == RuleExecutionStatus.NOT_APPLICABLE


def test_sample_workbook_passes_all_financial_rules() -> None:
    from src.mappers import group_base_rows
    from src.readers import (
        read_and_normalize_base,
        read_excel,
    )
    from src.services.version_resolver import resolve_version
    from src.validators import validate_base_rows

    path = Path(
        "/mnt/data/DRO_5050_planilha_testes(1).xlsx"
    )
    profile = resolve_version("2026-06").profile
    assert profile is not None

    normalization = read_and_normalize_base(
        read_excel(path),
        profile,
    )
    row_validation = validate_base_rows(
        normalization,
        profile,
    )
    grouping = group_base_rows(
        normalization,
        row_validation,
    )
    result = validate_event_financials(
        grouping,
        profile,
    )

    assert result.event_count == 15
    assert result.valid_event_count == 15
    assert result.invalid_event_count == 0
    assert result.is_valid
    assert result.is_fully_verified
    assert len(result.rule_results) == 105
    assert result.status_counts == {
        RuleExecutionStatus.PASSED: 105,
    }
