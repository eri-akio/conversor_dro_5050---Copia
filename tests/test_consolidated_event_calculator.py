"""Testes do semestre e dos sete campos consolidados."""

from __future__ import annotations

import unittest
from datetime import date

from src.domain.event_financial import EventsFinancialValidationResult
from src.domain.grouped_event import EventGroupingResult, EventsValidationResult
from src.services.consolidated_event_calculator import (
    calculate_consolidated_events,
    resolve_semester_period,
)
from src.services.event_classification_service import classify_events
from tests.test_event_classification_service import (
    PROFILE,
    accounting,
    event_bundle,
)


def calculate(*bundles, data_base: str = "2026-06"):
    grouping = EventGroupingResult(
        PROFILE, tuple(item[0] for item in bundles), (), ()
    )
    validation = EventsValidationResult(
        PROFILE, tuple(item[1] for item in bundles), ()
    )
    financial = EventsFinancialValidationResult(
        PROFILE, tuple(item[2] for item in bundles), ()
    )
    classification = classify_events(
        grouping=grouping,
        event_validation=validation,
        financial_validation=financial,
    )
    result = calculate_consolidated_events(
        data_base=data_base,
        grouping=grouping,
        classification=classification,
        financial_validation=financial,
    )
    return result, classification


class ConsolidatedEventCalculatorTests(unittest.TestCase):
    def test_resolves_fixed_semesters(self) -> None:
        self.assertEqual(
            resolve_semester_period("2026-06"),
            (date(2026, 1, 1), date(2026, 6, 30)),
        )
        self.assertEqual(
            resolve_semester_period("2026-12"),
            (date(2026, 7, 1), date(2026, 12, 31)),
        )

    def test_two_rows_count_one_event_and_sum_movements(self) -> None:
        rows = (
            accounting(2, date(2026, 1, 1), loss="400.00"),
            accounting(3, date(2026, 6, 30), loss="599.99"),
        )
        result, _ = calculate(
            event_bundle("E1", loss="999.99", accountings=rows)
        )
        event = result.events[0]
        self.assertEqual(event.total_event_count, 1)
        self.assertEqual(event.semester_event_count, 1)
        self.assertEqual(str(event.semester_loss), "999.99")

    def test_groups_are_sorted_by_category(self) -> None:
        result, _ = calculate(
            event_bundle("E7", category="7", loss="100.00"),
            event_bundle("E1", category="1", loss="100.00"),
            event_bundle("E2", category="2", loss="100.00"),
        )
        self.assertEqual(
            [item.category_level_1 for item in result.events],
            ["1", "2", "7"],
        )

    def test_june_boundaries_and_outside_movements(self) -> None:
        rows = (
            accounting(2, date(2025, 12, 31), loss="10.00"),
            accounting(3, date(2026, 1, 1), loss="20.00"),
            accounting(4, date(2026, 6, 30), loss="30.00"),
            accounting(5, date(2026, 7, 1), loss="40.00"),
        )
        result, _ = calculate(
            event_bundle("E1", loss="100.00", accountings=rows)
        )
        self.assertEqual(str(result.events[0].semester_loss), "50.00")
        self.assertEqual(result.events[0].semester_event_count, 0)

    def test_december_boundaries_are_included(self) -> None:
        rows = (
            accounting(2, date(2026, 7, 1), loss="20.00"),
            accounting(3, date(2026, 12, 31), loss="30.00"),
        )
        result, _ = calculate(
            event_bundle("E1", loss="50.00", accountings=rows),
            data_base="2026-12",
        )
        self.assertEqual(str(result.events[0].semester_loss), "50.00")
        self.assertEqual(result.events[0].semester_event_count, 1)

    def test_provision_preserves_reversal_sign(self) -> None:
        rows = (
            accounting(2, date(2026, 2, 1), provision="400.00"),
            accounting(3, date(2026, 3, 1), provision="-150.00"),
        )
        result, _ = calculate(
            event_bundle(
                "E1",
                loss="0.00",
                provision="250.00",
                accountings=rows,
            )
        )
        self.assertEqual(str(result.events[0].semester_provision), "250.00")

    def test_missing_accounting_date_blocks_group(self) -> None:
        rows = (accounting(2, None, loss="100.00"),)
        result, _ = calculate(
            event_bundle("E1", loss="100.00", accountings=rows)
        )
        self.assertEqual(result.events, ())
        self.assertEqual(result.issues[0].code, "CONS-CALC-001")


if __name__ == "__main__":
    unittest.main()
