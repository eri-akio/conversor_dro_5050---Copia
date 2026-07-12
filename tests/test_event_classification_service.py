"""Testes dos limiares e da exclusividade dos blocos."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from src.domain.base_row_validation import BaseRowKind
from src.domain.event_classification import EventDestination
from src.domain.event_financial import (
    EventFinancialSummary,
    EventFinancialValidationResult,
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventValidationResult,
    EventsValidationResult,
    GroupedAccounting,
    GroupedEvent,
    GroupedProbability,
    ResolvedEventField,
)
from src.services.event_classification_service import classify_events


PROFILE = "DRO_2025_06"
ZERO = Decimal("0.00")


def resolved(name: str, value, row: int = 2) -> ResolvedEventField:
    serialized = None if value is None else str(value)
    return ResolvedEventField(
        column_name=name,
        normalized_value=value,
        serialized_value=serialized,
        source_rows=(row,),
        absent_rows=(() if value is not None else (row,)),
        invalid_rows=(),
        distinct_serialized_values=(
            () if serialized is None else (serialized,)
        ),
    )


def accounting(
    row: int,
    accounting_date: date | None,
    *,
    loss: str = "0.00",
    provision: str = "0.00",
) -> GroupedAccounting:
    values = {
        "dataContabilizacao": accounting_date,
        "valorPerdaEfetiva": Decimal(loss),
        "valorProvisao": Decimal(provision),
        "valorRecuperacao": ZERO,
    }
    return GroupedAccounting(
        row_number=row,
        normalized_values=MappingProxyType(values),
        serialized_values=MappingProxyType(
            {
                key: (
                    value.isoformat()
                    if isinstance(value, date)
                    else str(value)
                    if value is not None
                    else None
                )
                for key, value in values.items()
            }
        ),
    )


def event_bundle(
    event_id: str,
    *,
    category: str | None = "1",
    loss: str = "999.99",
    provision: str = "0.00",
    risk: str | None = None,
    accountings: tuple[GroupedAccounting, ...] | None = None,
) -> tuple[
    GroupedEvent,
    EventValidationResult,
    EventFinancialValidationResult,
]:
    total_loss = Decimal(loss)
    total_provision = Decimal(provision)
    risk_value = Decimal(risk) if risk is not None else None
    total_risk = (
        total_provision + risk_value
        if risk_value is not None
        else None
    )
    rows = accountings or (
        accounting(2, date(2026, 1, 1), loss=loss, provision=provision),
    )
    row_numbers = tuple(item.row_number for item in rows)
    fields = {
        "categoriaNivel1": resolved("categoriaNivel1", category),
        "totalPerdaEfetiva": resolved(
            "totalPerdaEfetiva", total_loss
        ),
        "totalProvisao": resolved("totalProvisao", total_provision),
        "valorTotalRisco": resolved("valorTotalRisco", total_risk),
    }
    probabilities = (
        (
            GroupedProbability(
                probability_code="PR",
                value_risk=risk_value,
                source_rows=(2,),
                distinct_values=(risk_value,),
            ),
        )
        if risk_value is not None
        else ()
    )
    event = GroupedEvent(
        id_evento=event_id,
        profile_code=PROFILE,
        row_kind=BaseRowKind.INDIVIDUALIZED,
        row_numbers=row_numbers,
        source_names=("teste.xlsx",),
        event_fields=MappingProxyType(fields),
        probabilities=probabilities,
        accountings=rows,
        grouping_results=(),
    )
    consistency = EventValidationResult(
        id_evento=event_id,
        row_numbers=row_numbers,
        grouping_valid=True,
        rule_results=(),
    )
    summary = EventFinancialSummary(
        id_evento=event_id,
        row_numbers=row_numbers,
        accounting_row_numbers=row_numbers,
        declared_total_loss=total_loss,
        declared_total_provision=total_provision,
        declared_total_recovery=ZERO,
        accounting_loss_sum=sum(
            (item.get_value("valorPerdaEfetiva") for item in rows), ZERO
        ),
        accounting_provision_sum=sum(
            (item.get_value("valorProvisao") for item in rows), ZERO
        ),
        accounting_recovery_sum=ZERO,
        daily_balances=(),
        undated_accounting_rows=tuple(
            item.row_number
            for item in rows
            if not isinstance(item.get_value("dataContabilizacao"), date)
        ),
    )
    financial = EventFinancialValidationResult(
        id_evento=event_id,
        row_numbers=row_numbers,
        summary=summary,
        rule_results=(),
    )
    return event, consistency, financial


def classify_bundles(*bundles):
    events = tuple(bundle[0] for bundle in bundles)
    return classify_events(
        grouping=EventGroupingResult(PROFILE, events, (), ()),
        event_validation=EventsValidationResult(
            PROFILE,
            tuple(bundle[1] for bundle in bundles),
            (),
        ),
        financial_validation=EventsFinancialValidationResult(
            PROFILE,
            tuple(bundle[2] for bundle in bundles),
            (),
        ),
    )


class EventClassificationServiceTests(unittest.TestCase):
    def assert_destination(self, bundle, expected) -> None:
        result = classify_bundles(bundle)
        self.assertEqual(result.classifications[0].destination, expected)

    def test_loss_below_limit_is_consolidated(self) -> None:
        self.assert_destination(
            event_bundle("E1", loss="999.99"),
            EventDestination.CONSOLIDATED,
        )

    def test_exact_loss_limit_is_individualized(self) -> None:
        self.assert_destination(
            event_bundle("E1", loss="1000.00"),
            EventDestination.INDIVIDUALIZED,
        )

    def test_loss_plus_provision_uses_gross_amount(self) -> None:
        self.assert_destination(
            event_bundle("E1", loss="600.00", provision="400.00"),
            EventDestination.INDIVIDUALIZED,
        )

    def test_risk_below_limit_is_consolidated(self) -> None:
        self.assert_destination(
            event_bundle("E1", loss="500.00", risk="9999999.99"),
            EventDestination.CONSOLIDATED,
        )

    def test_exact_risk_limit_is_individualized(self) -> None:
        self.assert_destination(
            event_bundle("E1", loss="500.00", risk="10000000.00"),
            EventDestination.INDIVIDUALIZED,
        )

    def test_missing_category_is_not_chosen(self) -> None:
        result = classify_bundles(event_bundle("E1", category=None))
        self.assertEqual(
            result.classifications[0].destination,
            EventDestination.UNRESOLVED,
        )
        self.assertEqual(result.issues[0].code, "CONS-CALC-001")

    def test_destinations_are_exclusive(self) -> None:
        result = classify_bundles(
            event_bundle("C1", loss="999.99"),
            event_bundle("I1", loss="1000.00"),
        )
        self.assertEqual(result.consolidated_event_ids, ("C1",))
        self.assertEqual(result.individualized_event_ids, ("I1",))
        self.assertFalse(
            set(result.consolidated_event_ids)
            & set(result.individualized_event_ids)
        )

    def test_conflicting_category_is_not_selected(self) -> None:
        event, consistency, financial = event_bundle("E1")
        fields = dict(event.event_fields)
        fields["categoriaNivel1"] = ResolvedEventField(
            column_name="categoriaNivel1",
            normalized_value=None,
            serialized_value=None,
            source_rows=(2, 3),
            absent_rows=(),
            invalid_rows=(),
            distinct_serialized_values=("1", "2"),
        )
        conflicted = replace(
            event,
            row_numbers=(2, 3),
            event_fields=MappingProxyType(fields),
        )
        result = classify_bundles((conflicted, consistency, financial))
        self.assertEqual(
            result.classifications[0].destination,
            EventDestination.UNRESOLVED,
        )

    def test_invalid_monetary_total_is_not_replaced_by_zero(self) -> None:
        event, consistency, financial = event_bundle("E1")
        invalid_financial = replace(
            financial,
            summary=replace(
                financial.summary,
                declared_total_loss=None,
            ),
        )
        result = classify_bundles(
            (event, consistency, invalid_financial)
        )
        decision = result.classifications[0]
        self.assertEqual(decision.destination, EventDestination.UNRESOLVED)
        self.assertIsNone(decision.total_loss)


if __name__ == "__main__":
    unittest.main()
