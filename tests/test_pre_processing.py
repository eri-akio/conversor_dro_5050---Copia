"""Testes da integração das críticas de pré-processamento."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.domain.base_row_validation import (
    RuleExecutionStatus,
)
from src.mappers import group_base_rows
from src.normalizers.header_normalizer import (
    normalize_header,
)
from src.readers import (
    read_and_normalize_base,
    read_excel,
    read_header,
    read_reference_tables,
)
from src.services import resolve_version
from src.validators import (
    PRE_PROCESSING_CODES,
    PRE_PROCESSING_RULES,
    validate_base_rows,
    validate_grouped_events,
    validate_pre_processing,
    validate_reference_tables,
)


SAMPLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "DRO_5050_planilha_testes.xlsx"
)


def prepare_context():
    excel = read_excel(SAMPLE_PATH)
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
    references = validate_reference_tables(
        read_reference_tables(excel),
        grouping,
    )

    result = validate_pre_processing(
        header=header,
        profile=profile,
        row_validation=row_validation,
        grouping=grouping,
        event_validation=event_validation,
        references=references,
    )

    return result, {
        "header": header,
        "profile": profile,
        "row_validation": row_validation,
        "grouping": grouping,
        "event_validation": event_validation,
        "references": references,
    }


def test_catalog_has_exactly_34_unique_rules() -> None:
    assert len(PRE_PROCESSING_RULES) == 34
    assert len(PRE_PROCESSING_CODES) == 34
    assert len(set(PRE_PROCESSING_CODES)) == 34
    assert PRE_PROCESSING_CODES[0] == "DRO001001"
    assert PRE_PROCESSING_CODES[-1] == "DRO001452"

    assert all(
        rule.document_code == "5050"
        for rule in PRE_PROCESSING_RULES
    )
    assert all(
        rule.official_type == "E"
        for rule in PRE_PROCESSING_RULES
    )
    assert all(
        rule.start_label == "jun/21"
        for rule in PRE_PROCESSING_RULES
    )
    assert all(
        rule.source_path.is_file()
        for rule in PRE_PROCESSING_RULES
    )


def test_rules_are_not_applicable_before_june_2021() -> None:
    assert all(
        not rule.applies_to("2020-12")
        for rule in PRE_PROCESSING_RULES
    )
    assert all(
        rule.applies_to("2021-06")
        for rule in PRE_PROCESSING_RULES
    )


def test_sample_executes_all_catalog_entries() -> None:
    result, _ = prepare_context()

    assert result.rule_count == 34
    assert tuple(
        item.code
        for item in result.rule_results
    ) == PRE_PROCESSING_CODES
    assert result.is_locally_valid
    assert not result.is_fully_verified
    assert result.blocks_apt


def test_external_rules_are_not_executed() -> None:
    result, context = prepare_context()

    conglomerate = result.get_rule("DRO001001")
    bacen_id = result.get_rule("DRO001002")

    assert conglomerate.status == (
        RuleExecutionStatus.NOT_EXECUTED
    )
    assert bacen_id.status == (
        RuleExecutionStatus.NOT_EXECUTED
    )
    assert len(conglomerate.evidences) == 1
    assert len(bacen_id.evidences) == (
        context["grouping"].event_count
    )
    assert len(bacen_id.event_ids) == (
        context["grouping"].event_count
    )


def test_cosif_rules_keep_external_dependency() -> None:
    result, context = prepare_context()

    debit = result.get_rule("DRO001431")
    credit = result.get_rule("DRO001432")

    assert debit.status == (
        RuleExecutionStatus.NOT_EXECUTED
    )
    assert credit.status == (
        RuleExecutionStatus.NOT_EXECUTED
    )

    accounting_count = sum(
        len(event.accountings)
        for event in context["grouping"].events
    )

    assert len(debit.evidences) == accounting_count
    assert len(credit.evidences) == accounting_count
    assert all(
        evidence.status
        == RuleExecutionStatus.NOT_EXECUTED
        for evidence in debit.evidences
    )


def test_document_conflict_rule_is_not_executed() -> None:
    result, _ = prepare_context()
    rule = result.get_rule("DRO001241")

    assert rule.status == (
        RuleExecutionStatus.NOT_EXECUTED
    )
    assert rule.definition.dependency == "CONF-022"


def test_local_results_are_reused() -> None:
    result, _ = prepare_context()

    assert result.get_rule(
        "DRO001103"
    ).status == RuleExecutionStatus.PASSED
    assert result.get_rule(
        "DRO001311"
    ).status == RuleExecutionStatus.PASSED
    assert result.get_rule(
        "DRO001321"
    ).status == RuleExecutionStatus.PASSED
    assert result.get_rule(
        "DRO001451"
    ).status == RuleExecutionStatus.PASSED


def test_failed_evidence_has_precedence() -> None:
    result, context = prepare_context()
    original = context["row_validation"]

    target_index = next(
        index
        for index, item in enumerate(
            original.rule_results
        )
        if item.code == "DRO001201"
    )
    target = original.rule_results[target_index]
    failed = replace(
        target,
        status=RuleExecutionStatus.FAILED,
        severity="ERRO IMPEDITIVO",
        message="Falha simulada para testar consolidação.",
    )
    modified_results = list(
        original.rule_results
    )
    modified_results[target_index] = failed

    modified_row_validation = replace(
        original,
        rule_results=tuple(modified_results),
    )

    integrated = validate_pre_processing(
        header=context["header"],
        profile=context["profile"],
        row_validation=modified_row_validation,
        grouping=context["grouping"],
        event_validation=context[
            "event_validation"
        ],
        references=context["references"],
    )

    assert integrated.get_rule(
        "DRO001201"
    ).status == RuleExecutionStatus.FAILED
    assert not integrated.is_locally_valid


def test_sample_has_expected_unverified_codes() -> None:
    result, _ = prepare_context()

    assert {
        item.code
        for item in result.not_executed_rules
    } == {
        "DRO001001",
        "DRO001002",
        "DRO001241",
        "DRO001431",
        "DRO001432",
    }
