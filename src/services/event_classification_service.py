"""Classificação determinística dos eventos agrupados da aba Base."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.domain.base_row_validation import (
    BaseRowKind,
    RuleExecutionStatus,
)
from src.domain.event_classification import (
    EventClassification,
    EventClassificationResult,
    EventDestination,
)
from src.domain.event_financial import (
    EventFinancialValidationResult,
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventRuleResult,
    EventsValidationResult,
    GroupedEvent,
)


GROSS_LOSS_LIMIT = Decimal("1000.00")
UNCOVERED_RISK_LIMIT = Decimal("10000000.00")
INTERNAL_SOURCE = "INTERNA"
BLOCKING_SEVERITY = "ERRO IMPEDITIVO"


class EventClassificationService:
    """Aplica os limiares depois de agrupamento e validações."""

    def classify(
        self,
        *,
        grouping: EventGroupingResult,
        event_validation: EventsValidationResult,
        financial_validation: EventsFinancialValidationResult,
    ) -> EventClassificationResult:
        consistency_by_id = {
            item.id_evento: item
            for item in event_validation.events
        }
        financial_by_id = {
            item.id_evento: item
            for item in financial_validation.events
        }
        classifications: list[EventClassification] = []
        issues: list[EventRuleResult] = []

        for event in grouping.events:
            consistency = consistency_by_id.get(event.id_evento)
            financial = financial_by_id.get(event.id_evento)
            classification, issue = self._classify_event(
                event,
                consistency_is_valid=(
                    consistency is not None and consistency.is_valid
                ),
                financial=financial,
            )
            classifications.append(classification)
            if issue is not None:
                issues.append(issue)

        return EventClassificationResult(
            profile_code=grouping.profile_code,
            classifications=tuple(classifications),
            issues=tuple(issues),
        )

    def _classify_event(
        self,
        event: GroupedEvent,
        *,
        consistency_is_valid: bool,
        financial: EventFinancialValidationResult | None,
    ) -> tuple[EventClassification, EventRuleResult | None]:
        category = event.get_serialized_value("categoriaNivel1")
        first_date = self._first_accounting_date(event)
        summary = financial.summary if financial is not None else None
        total_loss = summary.declared_total_loss if summary else None
        total_provision = (
            summary.declared_total_provision if summary else None
        )

        unresolved: list[str] = []
        if event.row_kind == BaseRowKind.EXCLUDED:
            unresolved.append("evento excluído")
        if not event.is_grouping_valid:
            unresolved.append("conflito no agrupamento")
        if not consistency_is_valid:
            unresolved.append("consistência do evento inválida")
        if financial is None or not financial.is_valid:
            unresolved.append("validação financeira inválida")
        if category not in tuple(str(value) for value in range(1, 9)):
            unresolved.append("categoriaNivel1 não resolvida")
        if not isinstance(total_loss, Decimal):
            unresolved.append("totalPerdaEfetiva não resolvido")
        if not isinstance(total_provision, Decimal):
            unresolved.append("totalProvisao não resolvido")

        uncovered_risk, risk_error = self._uncovered_risk(
            event,
            total_provision,
        )
        if risk_error is not None:
            unresolved.append(risk_error)

        if unresolved:
            message = (
                "Não foi possível classificar o evento: "
                + "; ".join(dict.fromkeys(unresolved))
                + "."
            )
            return (
                self._classification(
                    event=event,
                    category=category,
                    total_loss=total_loss,
                    total_provision=total_provision,
                    uncovered_risk=uncovered_risk,
                    first_date=first_date,
                    destination=EventDestination.UNRESOLVED,
                    rule_code="CONS-CALC-001",
                    message=message,
                ),
                self._issue(event, message),
            )

        assert total_loss is not None
        assert total_provision is not None
        assert uncovered_risk is not None
        gross_loss = total_loss + total_provision
        individual = (
            gross_loss >= GROSS_LOSS_LIMIT
            or uncovered_risk >= UNCOVERED_RISK_LIMIT
        )
        destination = (
            EventDestination.INDIVIDUALIZED
            if individual
            else EventDestination.CONSOLIDATED
        )
        reason = (
            "perda bruta acumulada atingiu o limite de R$ 1.000,00"
            if gross_loss >= GROSS_LOSS_LIMIT
            else (
                "risco não coberto atingiu o limite de "
                "R$ 10.000.000,00"
                if uncovered_risk >= UNCOVERED_RISK_LIMIT
                else "os dois valores ficaram abaixo dos limiares"
            )
        )
        message = (
            f"Evento {event.id_evento} classificado como "
            f"{destination.value.lower()} porque {reason}."
        )
        return (
            self._classification(
                event=event,
                category=category,
                total_loss=total_loss,
                total_provision=total_provision,
                uncovered_risk=uncovered_risk,
                first_date=first_date,
                destination=destination,
                rule_code="CONS-CLASS-001",
                message=message,
            ),
            None,
        )

    @staticmethod
    def _uncovered_risk(
        event: GroupedEvent,
        total_provision: Decimal | None,
    ) -> tuple[Decimal | None, str | None]:
        total_risk = event.get_value("valorTotalRisco")
        if total_risk is None and not event.probabilities:
            return Decimal("0.00"), None

        if any(not item.is_resolved for item in event.probabilities):
            return None, "valorRisco ausente ou conflitante"

        probability_sum = event.probability_sum
        if probability_sum is None:
            return None, "soma de valorRisco não resolvida"

        if total_risk is None:
            if probability_sum == 0:
                return Decimal("0.00"), None
            return None, "valorTotalRisco ausente com risco informado"

        if (
            not isinstance(total_risk, Decimal)
            or not isinstance(total_provision, Decimal)
        ):
            return None, "composição do risco não resolvida"

        if total_risk != total_provision + probability_sum:
            return None, "valorTotalRisco diverge da composição validada"
        return probability_sum, None

    @staticmethod
    def _first_accounting_date(event: GroupedEvent) -> date | None:
        dates = tuple(
            value
            for accounting in event.accountings
            if isinstance(
                value := accounting.get_value("dataContabilizacao"),
                date,
            )
        )
        return min(dates) if dates else None

    @staticmethod
    def _classification(
        *,
        event: GroupedEvent,
        category: str | None,
        total_loss: Decimal | None,
        total_provision: Decimal | None,
        uncovered_risk: Decimal | None,
        first_date: date | None,
        destination: EventDestination,
        rule_code: str,
        message: str,
    ) -> EventClassification:
        gross_loss = (
            total_loss + total_provision
            if isinstance(total_loss, Decimal)
            and isinstance(total_provision, Decimal)
            else None
        )
        return EventClassification(
            event_id=event.id_evento,
            row_numbers=event.row_numbers,
            category_level_1=category,
            total_loss=total_loss,
            total_provision=total_provision,
            gross_accumulated_loss=gross_loss,
            uncovered_risk=uncovered_risk,
            first_accounting_date=first_date,
            destination=destination,
            rule_code=rule_code,
            message=message,
        )

    @staticmethod
    def _issue(event: GroupedEvent, message: str) -> EventRuleResult:
        return EventRuleResult(
            code="CONS-CALC-001",
            description="Classificar o evento entre os blocos do XML.",
            source=INTERNAL_SOURCE,
            severity=BLOCKING_SEVERITY,
            status=RuleExecutionStatus.FAILED,
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            columns=(
                "categoriaNivel1",
                "totalPerdaEfetiva",
                "totalProvisao",
                "valorTotalRisco",
                "valorRisco",
            ),
            message=message,
            suggestion="Revisar os valores e conflitos do evento.",
        )


def classify_events(
    *,
    grouping: EventGroupingResult,
    event_validation: EventsValidationResult,
    financial_validation: EventsFinancialValidationResult,
) -> EventClassificationResult:
    """Atalho funcional do classificador padrão."""

    return EventClassificationService().classify(
        grouping=grouping,
        event_validation=event_validation,
        financial_validation=financial_validation,
    )
