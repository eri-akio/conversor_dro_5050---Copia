"""Testes da integração das críticas de pós-processamento."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.builders import build_final_document
from src.domain.base_row_validation import (
    RuleExecutionStatus,
)
from src.domain.document_model import (
    FinalConsolidatedEvent,
)
from src.mappers import group_base_rows
from src.normalizers.header_normalizer import (
    normalize_header,
)
from src.readers import (
    read_and_normalize_base,
    read_excel,
    read_header,
)
from src.services import resolve_version
from src.validators import (
    POST_PROCESSING_CODES,
    POST_PROCESSING_RULES,
    validate_base_rows,
    validate_event_financials,
    validate_grouped_events,
    validate_post_processing,
)
from tests.test_document_builder import (
    consolidated_event,
    prepare_sample,
)
from tests.test_event_grouping import (
    base_values,
    create_workbook,
)


SAMPLE_PATH = Path(
    "/mnt/data/DRO_5050_planilha_testes(1).xlsx"
)


HISTORICAL_CODES = {
    "DRO000016",
    "DRO000017",
    "DRO000022",
    "DRO000026",
    "DRO000027",
    "DRO000028",
    "DRO000029",
    "DRO000030",
}

CONSOLIDATED_CODES = {
    "DRO000001",
    "DRO000002",
    "DRO000018",
    "DRO000019",
}


def validate_sample(
    consolidated_events=(),
):
    context = prepare_sample()
    result = validate_post_processing(
        header=context["header"],
        profile=context["profile"],
        grouping=context["grouping"],
        row_validation=context["row_validation"],
        financial_validation=(
            context["financial_validation"]
        ),
        consolidated_events=consolidated_events,
    )
    return result, context


def validate_rows(
    tmp_path: Path,
    rows: list[dict[str, object]],
):
    path = tmp_path / "entrada_pos.xlsx"
    create_workbook(path, rows)

    excel = read_excel(path)
    header_result = normalize_header(
        read_header(excel)
    )
    assert header_result.header is not None
    header = header_result.header

    profile = resolve_version(header).profile
    assert profile is not None

    normalization = read_and_normalize_base(
        excel,
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
    event_validation = validate_grouped_events(
        grouping,
        profile,
    )
    financial = validate_event_financials(
        grouping,
        profile,
    )
    post = validate_post_processing(
        header=header,
        profile=profile,
        grouping=grouping,
        row_validation=row_validation,
        financial_validation=financial,
    )

    return post, {
        "header": header,
        "profile": profile,
        "row_validation": row_validation,
        "grouping": grouping,
        "event_validation": event_validation,
        "financial_validation": financial,
    }


def test_catalog_has_exactly_26_unique_rules() -> None:
    assert len(POST_PROCESSING_RULES) == 26
    assert len(POST_PROCESSING_CODES) == 26
    assert len(set(POST_PROCESSING_CODES)) == 26
    assert POST_PROCESSING_CODES[0] == "DRO000001"
    assert POST_PROCESSING_CODES[-1] == "DRO000032"

    assert all(
        rule.official_type
        in {"Inconsistência", "Esclarecimento"}
        for rule in POST_PROCESSING_RULES
    )
    assert all(
        rule.source_path.is_file()
        for rule in POST_PROCESSING_RULES
    )


def test_sample_executes_all_catalog_entries() -> None:
    result, _ = validate_sample()

    assert result.rule_count == 26
    assert result.evidence_count == 252
    assert tuple(
        item.code
        for item in result.rule_results
    ) == POST_PROCESSING_CODES
    assert result.status_counts == {
        RuleExecutionStatus.NOT_EXECUTED: 12,
        RuleExecutionStatus.PASSED: 14,
    }
    assert result.is_locally_valid
    assert not result.is_fully_verified
    assert result.blocks_apt


def test_historical_rules_are_not_executed() -> None:
    result, _ = validate_sample()

    assert {
        item.code
        for item in result.not_executed_rules
        if item.code in HISTORICAL_CODES
    } == HISTORICAL_CODES

    for code in HISTORICAL_CODES:
        rule = result.get_rule(code)
        assert rule.status == (
            RuleExecutionStatus.NOT_EXECUTED
        )
        assert rule.definition.dependency is not None


def test_consolidated_rules_are_not_executed_without_block() -> None:
    result, _ = validate_sample()

    assert {
        item.code
        for item in result.not_executed_rules
        if item.code in CONSOLIDATED_CODES
    } == CONSOLIDATED_CODES


def test_existing_local_results_are_reused() -> None:
    result, _ = validate_sample()

    for code in (
        "DRO000010",
        "DRO000011",
        "DRO000012",
        "DRO000013",
        "DRO000014",
        "DRO000015",
        "DRO000021",
        "DRO000023",
        "DRO000024",
    ):
        assert result.get_rule(
            code
        ).status == RuleExecutionStatus.PASSED


def test_consolidated_average_and_sign_rules_execute() -> None:
    high_average = FinalConsolidatedEvent(
        category_level_1="1",
        total_event_count=1,
        semester_event_count=1,
        total_loss=Decimal("1500.00"),
        semester_loss=Decimal("1500.00"),
        total_provision=Decimal("0.00"),
        semester_provision=Decimal("0.00"),
    )

    result, _ = validate_sample(
        consolidated_events=(high_average,)
    )

    assert result.get_rule(
        "DRO000001"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000002"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000018"
    ).status == RuleExecutionStatus.PASSED
    assert result.get_rule(
        "DRO000019"
    ).status == RuleExecutionStatus.PASSED

    negative = FinalConsolidatedEvent(
        category_level_1="2",
        total_event_count=1,
        semester_event_count=0,
        total_loss=Decimal("-20.00"),
        semester_loss=Decimal("0.00"),
        total_provision=Decimal("-20.00"),
        semester_provision=Decimal("0.00"),
    )

    result, _ = validate_sample(
        consolidated_events=(negative,)
    )

    assert result.get_rule(
        "DRO000018"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000019"
    ).status == RuleExecutionStatus.FAILED


def test_consolidated_zero_counts_do_not_divide_by_zero() -> None:
    zero = FinalConsolidatedEvent(
        category_level_1="1",
        total_event_count=0,
        semester_event_count=0,
        total_loss=Decimal("0.00"),
        semester_loss=Decimal("0.00"),
        total_provision=Decimal("0.00"),
        semester_provision=Decimal("0.00"),
    )

    result, _ = validate_sample(consolidated_events=(zero,))

    assert result.get_rule(
        "DRO000001"
    ).status == RuleExecutionStatus.NOT_APPLICABLE
    assert result.get_rule(
        "DRO000002"
    ).status == RuleExecutionStatus.NOT_APPLICABLE
    assert result.get_rule(
        "DRO000018"
    ).status == RuleExecutionStatus.PASSED
    assert result.get_rule(
        "DRO000019"
    ).status == RuleExecutionStatus.PASSED


def test_custom_local_rules_detect_failures(
    tmp_path: Path,
) -> None:
    probable = base_values()
    probable["idEvento"] = "EVTPR"
    probable["totalProvisao"] = "0,00"
    probable["valorProvisao"] = "0,00"
    probable["valorTotalRisco"] = "10000,00"

    possible = base_values()
    possible["idEvento"] = "EVTPO"
    possible["probabilidadePerda"] = "PO"
    possible["valorRisco"] = "0,00"
    possible["totalProvisao"] = "0,00"
    possible["valorProvisao"] = "0,00"
    possible["valorTotalRisco"] = "0,00"

    fraud = base_values()
    fraud["idEvento"] = "EVTFRAUDE"
    fraud["categoriaNivel1"] = "1"
    fraud["categoriaNivel2"] = "11"
    fraud["tipoAvaliacao"] = "NA"
    fraud["naturezaContingencia"] = "NA"
    fraud["probabilidadePerda"] = None
    fraud["valorRisco"] = None
    fraud["totalProvisao"] = "100,00"
    fraud["valorProvisao"] = "100,00"
    fraud["valorTotalRisco"] = None

    missing_category = base_values()
    missing_category["idEvento"] = "EVTCAT"
    missing_category["categoriaNivel2"] = None

    result, _ = validate_rows(
        tmp_path,
        [
            probable,
            possible,
            fraud,
            missing_category,
        ],
    )

    assert result.get_rule(
        "DRO000004"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000005"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000009"
    ).status == RuleExecutionStatus.FAILED
    assert result.get_rule(
        "DRO000032"
    ).status == RuleExecutionStatus.FAILED


def test_clarification_failure_is_warning_only(
    tmp_path: Path,
) -> None:
    first = base_values()
    first["totalProvisao"] = "50,00"
    first["valorTotalRisco"] = "10050,00"
    first["valorProvisao"] = "100,00"

    second = dict(first)
    second["probabilidadePerda"] = None
    second["valorRisco"] = None
    second["dataContabilizacao"] = "2025-06-20"
    second["valorPerdaEfetiva"] = "0,00"
    second["valorProvisao"] = "-150,00"

    third = dict(first)
    third["probabilidadePerda"] = None
    third["valorRisco"] = None
    third["dataContabilizacao"] = "2025-06-25"
    third["valorPerdaEfetiva"] = "0,00"
    third["valorProvisao"] = "100,00"

    result, _ = validate_rows(
        tmp_path,
        [first, second, third],
    )

    rule = result.get_rule("DRO000024")
    assert rule.status == RuleExecutionStatus.FAILED
    assert rule.has_warning_failure
    assert not rule.blocks_apt
    assert rule in result.warning_failed_rules
    assert result.is_locally_valid


def test_document_builder_receives_post_processing() -> None:
    post, context = validate_sample()

    build_result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
        post_processing_validation=post,
    )

    assert build_result.is_built
    assert build_result.blocks_apt
    assert any(
        issue.code == "DOC-POS-NE-001"
        for issue in build_result.issues
    )
