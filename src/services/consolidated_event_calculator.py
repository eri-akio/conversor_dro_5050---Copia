"""Cálculo dos sete campos consolidados a partir da aba Base."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.document_model import FinalConsolidatedEvent
from src.domain.event_classification import (
    ConsolidatedCalculationResult,
    EventClassificationResult,
)
from src.domain.event_financial import (
    EventFinancialValidationResult,
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventRuleResult,
    GroupedEvent,
)


ZERO = Decimal("0.00")
INTERNAL_SOURCE = "INTERNA"
BLOCKING_SEVERITY = "ERRO IMPEDITIVO"


def resolve_semester_period(data_base: str) -> tuple[date, date]:
    """Resolve o semestre civil encerrado em junho ou dezembro."""

    try:
        year_text, month_text = data_base.split("-", maxsplit=1)
        year = int(year_text)
        month = int(month_text)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("dataBase deve usar o formato AAAA-MM.") from error

    if month == 6:
        return date(year, 1, 1), date(year, 6, 30)
    if month == 12:
        return date(year, 7, 1), date(year, 12, 31)
    raise ValueError("dataBase deve terminar em -06 ou -12.")


class ConsolidatedEventCalculator:
    """Agrupa candidatos por categoria e calcula totais semestrais."""

    def calculate(
        self,
        *,
        data_base: str,
        grouping: EventGroupingResult,
        classification: EventClassificationResult,
        financial_validation: EventsFinancialValidationResult,
    ) -> ConsolidatedCalculationResult:
        semester_start, semester_end = resolve_semester_period(data_base)
        events_by_id = {
            event.id_evento: event for event in grouping.events
        }
        financial_by_id = {
            item.id_evento: item
            for item in financial_validation.events
        }
        decision_by_id = {
            item.event_id: item
            for item in classification.classifications
        }
        grouped: dict[
            str,
            list[tuple[GroupedEvent, EventFinancialValidationResult]],
        ] = defaultdict(list)
        issues: list[EventRuleResult] = []

        for event_id in classification.consolidated_event_ids:
            event = events_by_id[event_id]
            financial = financial_by_id[event_id]
            decision = decision_by_id[event_id]
            if (
                decision.category_level_1 is None
                or decision.first_accounting_date is None
                or financial.summary.undated_accounting_rows
            ):
                issues.append(
                    self._date_issue(
                        event,
                        financial.summary.undated_accounting_rows,
                    )
                )
                continue
            grouped[decision.category_level_1].append(
                (event, financial)
            )

        consolidated: list[FinalConsolidatedEvent] = []
        for category in sorted(grouped, key=int):
            entries = grouped[category]
            consolidated.append(
                self._calculate_group(
                    category=category,
                    entries=entries,
                    semester_start=semester_start,
                    semester_end=semester_end,
                    decision_by_id=decision_by_id,
                )
            )

        return ConsolidatedCalculationResult(
            profile_code=grouping.profile_code,
            data_base=data_base,
            events=tuple(consolidated),
            issues=tuple(issues),
        )

    @staticmethod
    def _calculate_group(
        *,
        category: str,
        entries: list[
            tuple[GroupedEvent, EventFinancialValidationResult]
        ],
        semester_start: date,
        semester_end: date,
        decision_by_id: dict,
    ) -> FinalConsolidatedEvent:
        event_ids = tuple(event.id_evento for event, _ in entries)
        source_rows = tuple(
            row
            for event, _ in entries
            for row in event.row_numbers
        )
        semester_event_count = sum(
            1
            for event, _ in entries
            if semester_start
            <= decision_by_id[event.id_evento].first_accounting_date
            <= semester_end
        )
        total_loss = sum(
            (
                financial.summary.declared_total_loss
                for _, financial in entries
            ),
            ZERO,
        )
        total_provision = sum(
            (
                financial.summary.declared_total_provision
                for _, financial in entries
            ),
            ZERO,
        )
        semester_loss = ZERO
        semester_provision = ZERO

        for event, _ in entries:
            for accounting in event.accountings:
                accounting_date = accounting.get_value(
                    "dataContabilizacao"
                )
                if not (
                    isinstance(accounting_date, date)
                    and semester_start <= accounting_date <= semester_end
                ):
                    continue
                loss = accounting.get_value("valorPerdaEfetiva")
                provision = accounting.get_value("valorProvisao")
                if isinstance(loss, Decimal):
                    semester_loss += loss
                if isinstance(provision, Decimal):
                    semester_provision += provision

        return FinalConsolidatedEvent(
            category_level_1=category,
            total_event_count=len(event_ids),
            semester_event_count=semester_event_count,
            total_loss=total_loss,
            semester_loss=semester_loss,
            total_provision=total_provision,
            semester_provision=semester_provision,
            source_event_ids=event_ids,
            source_rows=source_rows,
        )

    @staticmethod
    def _date_issue(
        event: GroupedEvent,
        undated_rows: tuple[int, ...],
    ) -> EventRuleResult:
        return EventRuleResult(
            code="CONS-CALC-001",
            description=(
                "Calcular o vínculo semestral do evento consolidado."
            ),
            source=INTERNAL_SOURCE,
            severity=BLOCKING_SEVERITY,
            status=RuleExecutionStatus.FAILED,
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            columns=("dataContabilizacao",),
            message=(
                "O evento candidato a consolidado não possui todas as "
                "datas de contabilização válidas."
            ),
            suggestion="Corrigir as datas antes de gerar o bloco.",
            values=(("linhasSemData", undated_rows),),
        )


def calculate_consolidated_events(
    *,
    data_base: str,
    grouping: EventGroupingResult,
    classification: EventClassificationResult,
    financial_validation: EventsFinancialValidationResult,
) -> ConsolidatedCalculationResult:
    """Atalho funcional do calculador padrão."""

    return ConsolidatedEventCalculator().calculate(
        data_base=data_base,
        grouping=grouping,
        classification=classification,
        financial_validation=financial_validation,
    )
