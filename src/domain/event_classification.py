"""Decisões de roteamento e cálculo dos eventos da aba Base."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from src.domain.document_model import FinalConsolidatedEvent
from src.domain.grouped_event import EventRuleResult


class EventDestination(StrEnum):
    """Destino exclusivo de um evento depois das validações."""

    INDIVIDUALIZED = "INDIVIDUALIZADO"
    CONSOLIDATED = "CONSOLIDADO"
    UNRESOLVED = "NÃO CLASSIFICADO"


@dataclass(frozen=True, slots=True)
class EventClassification:
    """Evidência completa da decisão tomada para um ``idEvento``."""

    event_id: str
    row_numbers: tuple[int, ...]
    category_level_1: str | None
    total_loss: Decimal | None
    total_provision: Decimal | None
    gross_accumulated_loss: Decimal | None
    uncovered_risk: Decimal | None
    first_accounting_date: date | None
    destination: EventDestination
    rule_code: str
    message: str


@dataclass(frozen=True, slots=True)
class EventClassificationResult:
    """Roteamento agregado, sem sobreposição entre os blocos."""

    profile_code: str
    classifications: tuple[EventClassification, ...]
    issues: tuple[EventRuleResult, ...] = ()

    @property
    def individualized_event_ids(self) -> tuple[str, ...]:
        return tuple(
            item.event_id
            for item in self.classifications
            if item.destination == EventDestination.INDIVIDUALIZED
        )

    @property
    def consolidated_event_ids(self) -> tuple[str, ...]:
        return tuple(
            item.event_id
            for item in self.classifications
            if item.destination == EventDestination.CONSOLIDATED
        )

    @property
    def unresolved_event_ids(self) -> tuple[str, ...]:
        return tuple(
            item.event_id
            for item in self.classifications
            if item.destination == EventDestination.UNRESOLVED
        )

    @property
    def is_valid(self) -> bool:
        return not self.unresolved_event_ids and not any(
            issue.blocks_processing for issue in self.issues
        )


@dataclass(frozen=True, slots=True)
class ConsolidatedCalculationResult:
    """Grupos consolidados calculados exclusivamente a partir da Base."""

    profile_code: str
    data_base: str
    events: tuple[FinalConsolidatedEvent, ...]
    issues: tuple[EventRuleResult, ...] = ()

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def is_valid(self) -> bool:
        return not any(
            issue.blocks_processing for issue in self.issues
        )
