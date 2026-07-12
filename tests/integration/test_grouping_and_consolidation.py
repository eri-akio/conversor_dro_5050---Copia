"""Integração do agrupamento, classificação e cálculo consolidado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.conversion import ConversionStage
from src.domain.event_classification import EventDestination
from src.mappers import group_base_rows
from src.readers import read_and_normalize_base, read_excel
from src.services import convert_excel
from src.services.version_resolver import resolve_version
from src.validators import validate_base_rows

from .workbook_factory import (
    create_conflicting_event_workbook,
    create_workbook,
    make_row,
)


def test_conflicting_event_attributes_are_not_selected_arbitrarily(
    tmp_path: Path,
) -> None:
    path = create_conflicting_event_workbook(tmp_path / "conflict.xlsx")

    profile = resolve_version("2026-06").profile
    assert profile is not None
    normalization = read_and_normalize_base(read_excel(path), profile)
    row_validation = validate_base_rows(normalization, profile)
    grouping = group_base_rows(normalization, row_validation)

    assert not grouping.is_valid
    event = grouping.events[0]
    assert event.get_field("categoriaNivel1").has_conflict
    assert event.get_value("categoriaNivel1") is None
    assert any(
        rule.code == "MAP-EVT-001"
        and rule.status == RuleExecutionStatus.FAILED
        for rule in event.grouping_results
    )


def test_classification_is_exclusive_and_consolidation_is_semester_aware(
    tmp_path: Path,
) -> None:
    path = create_workbook(
        tmp_path / "consolidation.xlsx",
        rows=(
            make_row(event_id="IND0001", total_loss=2300),
            make_row(
                event_id="CON0001",
                total_loss=700,
                accounting_loss=700,
                occurrence_date=date(2026, 3, 15),
            ),
            make_row(
                event_id="CON0002",
                total_loss=450,
                accounting_loss=450,
                occurrence_date=date(2025, 12, 15),
            ),
        ),
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    classification = result.output(ConversionStage.CLASSIFY_EVENTS)
    calculation = result.output(ConversionStage.CALCULATE_CONSOLIDATED)

    destinations = {
        item.event_id: item.destination
        for item in classification.classifications
    }
    assert destinations == {
        "IND0001": EventDestination.INDIVIDUALIZED,
        "CON0001": EventDestination.CONSOLIDATED,
        "CON0002": EventDestination.CONSOLIDATED,
    }
    assert not (
        set(classification.individualized_event_ids)
        & set(classification.consolidated_event_ids)
    )
    assert calculation.event_count == 1
    consolidated = calculation.events[0]
    assert consolidated.source_event_ids == ("CON0001", "CON0002")
    assert consolidated.total_event_count == 2
    assert consolidated.semester_event_count == 1
    assert consolidated.total_loss == Decimal("1150.00")
    assert consolidated.semester_loss == Decimal("700.00")
    assert consolidated.total_provision == Decimal("0.00")


def test_deferred_rules_are_reconciled_before_document_build(
    tmp_path: Path,
) -> None:
    path = create_workbook(
        tmp_path / "reconciliation.xlsx",
        rows=(
            make_row(),
            make_row(
                event_id="CON0001",
                total_loss=700,
                accounting_loss=700,
            ),
        ),
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    reconciliation = result.output(ConversionStage.RECONCILE_RULES)

    assert reconciliation.is_fully_reconciled
    assert not reconciliation.unresolved_records
    assert result.output(ConversionStage.BUILD_DOCUMENT).is_built
