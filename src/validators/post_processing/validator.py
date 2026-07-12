"""Integração e execução das críticas de pós-processamento."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from src.domain.base_row_validation import (
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.document_header import DocumentHeader
from src.domain.document_model import (
    FinalConsolidatedEvent,
)
from src.domain.event_financial import (
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    GroupedEvent,
)
from src.domain.post_processing import (
    PostProcessingEvidence,
    PostProcessingProvider,
    PostProcessingRuleDefinition,
    PostProcessingRuleResult,
    PostProcessingValidationResult,
)
from src.domain.regulatory_version import (
    RegulatoryVersion,
)
from src.validators.post_processing.catalog import (
    POST_PROCESSING_RULES,
)


SEVERITY_ERROR = "ERRO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"

DATE_2021_01_01 = date(2021, 1, 1)
LIMIT_ONE_THOUSAND = Decimal("1000.00")
NEGATIVE_LIMIT = Decimal("-10.00")


class PostProcessingValidator:
    """Produz exatamente um resultado para cada crítica oficial."""

    def __init__(
        self,
        catalog: tuple[
            PostProcessingRuleDefinition,
            ...,
        ] = POST_PROCESSING_RULES,
    ) -> None:
        self.catalog = catalog
        self._validate_catalog()

    def validate(
        self,
        *,
        header: DocumentHeader,
        profile: RegulatoryVersion,
        grouping: EventGroupingResult,
        row_validation: BaseRowsValidationResult,
        financial_validation: (
            EventsFinancialValidationResult
        ),
        consolidated_events: Iterable[
            FinalConsolidatedEvent
        ] = (),
    ) -> PostProcessingValidationResult:
        row_results = self._index_by_code(
            row_validation.rule_results
        )
        financial_results = self._index_by_code(
            financial_validation.rule_results
        )
        consolidated = tuple(consolidated_events)

        results: list[PostProcessingRuleResult] = []

        for definition in self.catalog:
            evidences = self._resolve_evidences(
                definition=definition,
                header=header,
                grouping=grouping,
                row_results=row_results,
                financial_results=financial_results,
                consolidated_events=consolidated,
            )
            results.append(
                PostProcessingRuleResult(
                    definition=definition,
                    status=self._aggregate_status(
                        evidences
                    ),
                    evidences=evidences,
                )
            )

        return PostProcessingValidationResult(
            profile_code=profile.code,
            data_base=header.data_base,
            source_path=self.catalog[0].source_path,
            rule_results=tuple(results),
        )

    def _resolve_evidences(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        header: DocumentHeader,
        grouping: EventGroupingResult,
        row_results: dict[str, list[Any]],
        financial_results: dict[str, list[Any]],
        consolidated_events: tuple[
            FinalConsolidatedEvent,
            ...,
        ],
    ) -> tuple[PostProcessingEvidence, ...]:
        provider = definition.provider

        if provider == PostProcessingProvider.HISTORICAL:
            return (
                self._not_executed(
                    definition=definition,
                    source_stage=(
                        "Dependência histórica"
                    ),
                    message=(
                        "A crítica exige o Documento 5050 "
                        "da data-base imediatamente anterior, "
                        "que não foi fornecido à execução."
                    ),
                    values=(
                        ("dataBaseAtual", header.data_base),
                        (
                            "dependencia",
                            definition.dependency,
                        ),
                    ),
                ),
            )

        if provider == PostProcessingProvider.CONSOLIDATED:
            return self._consolidated_evidences(
                definition,
                consolidated_events,
            )

        if provider == PostProcessingProvider.CUSTOM_EVENT:
            return self._custom_event_evidences(
                definition,
                grouping,
            )

        if provider == PostProcessingProvider.ROW_VALIDATION:
            source_code = definition.source_rule_code
            raw_results = row_results.get(
                source_code or "",
                [],
            )
            return self._adapt_results(
                definition,
                raw_results,
                source_stage="Validação local por linha",
            )

        if provider == PostProcessingProvider.EVENT_FINANCIAL:
            source_code = definition.source_rule_code
            raw_results = financial_results.get(
                source_code or "",
                [],
            )
            return self._adapt_results(
                definition,
                raw_results,
                source_stage="Validação financeira do evento",
            )

        return (
            self._not_executed(
                definition=definition,
                source_stage=(
                    "Integração de pós-processamento"
                ),
                message=(
                    "O provedor técnico da crítica "
                    "não foi reconhecido."
                ),
            ),
        )

    def _adapt_results(
        self,
        definition: PostProcessingRuleDefinition,
        raw_results: list[Any],
        *,
        source_stage: str,
    ) -> tuple[PostProcessingEvidence, ...]:
        if not raw_results:
            return (
                self._not_executed(
                    definition=definition,
                    source_stage=source_stage,
                    message=(
                        "Nenhuma evidência técnica foi "
                        "produzida para a crítica."
                    ),
                    values=(
                        (
                            "codigoFonte",
                            definition.source_rule_code,
                        ),
                    ),
                ),
            )

        return tuple(
            self._adapt_result(
                result,
                source_stage=source_stage,
            )
            for result in raw_results
        )

    def _custom_event_evidences(
        self,
        definition: PostProcessingRuleDefinition,
        grouping: EventGroupingResult,
    ) -> tuple[PostProcessingEvidence, ...]:
        handlers = {
            "DRO000003": self._dro000003,
            "DRO000004": self._dro000004,
            "DRO000005": self._dro000005,
            "DRO000009": self._dro000009,
            "DRO000032": self._dro000032,
        }
        handler = handlers.get(definition.code)

        if handler is None:
            return (
                self._not_executed(
                    definition=definition,
                    source_stage=(
                        "Validação local do evento"
                    ),
                    message=(
                        "A função local da crítica "
                        "não foi implementada."
                    ),
                ),
            )

        if not grouping.events:
            return (
                self._evidence(
                    definition=definition,
                    status=(
                        RuleExecutionStatus
                        .NOT_APPLICABLE
                    ),
                    source_stage=(
                        "Validação local do evento"
                    ),
                    message=(
                        "O documento não possui eventos "
                        "individualizados para esta crítica."
                    ),
                ),
            )

        return tuple(
            handler(definition, event)
            for event in grouping.events
        )

    def _dro000003(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
    ) -> PostProcessingEvidence:
        occurrence = event.get_value(
            "dataOcorrencia"
        )
        assessment = event.get_serialized_value(
            "tipoAvaliacao"
        )

        if not isinstance(occurrence, date):
            return self._event_not_executed(
                definition,
                event,
                "A data de ocorrência não está resolvida.",
                columns=(
                    "dataOcorrencia",
                    "tipoAvaliacao",
                    "probabilidadePerda",
                    "valorRisco",
                ),
            )

        if (
            occurrence <= DATE_2021_01_01
            or assessment != "I"
        ):
            return self._event_not_applicable(
                definition,
                event,
                "O evento não está no contexto da crítica.",
                columns=(
                    "dataOcorrencia",
                    "tipoAvaliacao",
                ),
            )

        if any(
            probability.has_conflict
            for probability in event.probabilities
        ):
            return self._event_not_executed(
                definition,
                event,
                "Há conflito no detalhamento de probabilidade.",
                columns=(
                    "probabilidadePerda",
                    "valorRisco",
                ),
            )

        if any(
            probability.is_resolved
            for probability in event.probabilities
        ):
            return self._event_passed(
                definition,
                event,
                "O evento possui detalhamento de probabilidade de perda.",
                columns=(
                    "tipoAvaliacao",
                    "probabilidadePerda",
                    "valorRisco",
                    "dataOcorrencia",
                ),
            )

        return self._event_failed(
            definition,
            event,
            "Evento individual posterior a 01/01/2021 sem detalhamento de probabilidade.",
            columns=(
                "tipoAvaliacao",
                "probabilidadePerda",
                "valorRisco",
                "dataOcorrencia",
            ),
            suggestion=(
                "Informar o detalhamento de probabilidade "
                "conforme a regra oficial."
            ),
        )

    def _dro000004(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
    ) -> PostProcessingEvidence:
        if event.get_serialized_value(
            "tipoAvaliacao"
        ) != "I":
            return self._event_not_applicable(
                definition,
                event,
                "O evento não possui avaliação individual.",
                columns=("tipoAvaliacao",),
            )

        probable = tuple(
            probability
            for probability in event.probabilities
            if probability.probability_code == "PR"
        )

        if not probable:
            return self._event_not_applicable(
                definition,
                event,
                "O evento não possui probabilidade PR.",
                columns=("probabilidadePerda",),
            )

        if any(
            item.has_conflict
            for item in probable
        ):
            return self._event_not_executed(
                definition,
                event,
                "A probabilidade PR possui valor conflitante.",
                columns=(
                    "probabilidadePerda",
                    "valorRisco",
                ),
            )

        provision = event.get_value(
            "totalProvisao"
        )
        if not isinstance(provision, Decimal):
            return self._event_not_executed(
                definition,
                event,
                "O total de provisão não está resolvido.",
                columns=("totalProvisao",),
            )

        values = (
            ("tipoAvaliacao", "I"),
            ("probabilidadePerda", "PR"),
            ("totalProvisao", provision),
        )

        if provision == Decimal("0"):
            return self._event_failed(
                definition,
                event,
                "Evento com perda provável e totalProvisao igual a zero.",
                columns=(
                    "tipoAvaliacao",
                    "probabilidadePerda",
                    "totalProvisao",
                ),
                values=values,
                suggestion=(
                    "Revisar a provisão da contingência "
                    "classificada como perda provável."
                ),
            )

        return self._event_passed(
            definition,
            event,
            "A perda provável possui provisão diferente de zero.",
            columns=(
                "tipoAvaliacao",
                "probabilidadePerda",
                "totalProvisao",
            ),
            values=values,
        )

    def _dro000005(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
    ) -> PostProcessingEvidence:
        if event.get_serialized_value(
            "tipoAvaliacao"
        ) != "I":
            return self._event_not_applicable(
                definition,
                event,
                "O evento não possui avaliação individual.",
                columns=("tipoAvaliacao",),
            )

        applicable = tuple(
            probability
            for probability in event.probabilities
            if probability.probability_code
            in {"PO", "RE"}
        )

        if not applicable:
            return self._event_not_applicable(
                definition,
                event,
                "O evento não possui probabilidade PO ou RE.",
                columns=("probabilidadePerda",),
            )

        unresolved = tuple(
            item.probability_code
            for item in applicable
            if (
                item.has_conflict
                or item.value_risk is None
            )
        )

        if unresolved:
            return self._event_not_executed(
                definition,
                event,
                "Há probabilidade PO ou RE sem valor de risco resolvido.",
                columns=(
                    "probabilidadePerda",
                    "valorRisco",
                ),
                values=(
                    ("probabilidades", unresolved),
                ),
            )

        zero_codes = tuple(
            item.probability_code
            for item in applicable
            if item.value_risk == Decimal("0")
        )

        if zero_codes:
            return self._event_failed(
                definition,
                event,
                "Probabilidade possível ou remota com valorRisco igual a zero.",
                columns=(
                    "tipoAvaliacao",
                    "probabilidadePerda",
                    "valorRisco",
                ),
                values=(
                    ("probabilidadesComZero", zero_codes),
                ),
                suggestion=(
                    "Informar o valor em risco da "
                    "contingência."
                ),
            )

        return self._event_passed(
            definition,
            event,
            "As probabilidades PO e RE possuem valor de risco.",
            columns=(
                "tipoAvaliacao",
                "probabilidadePerda",
                "valorRisco",
            ),
        )

    def _dro000009(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
    ) -> PostProcessingEvidence:
        if not event.accountings:
            return self._event_not_applicable(
                definition,
                event,
                "O evento não possui contabilizações.",
                columns=(
                    "dataContabilizacao",
                    "categoriaNivel2",
                ),
            )

        dates = tuple(
            accounting.get_value(
                "dataContabilizacao"
            )
            for accounting in event.accountings
        )

        if any(
            not isinstance(value, date)
            for value in dates
        ):
            return self._event_not_executed(
                definition,
                event,
                "Há contabilização sem data válida.",
                columns=(
                    "dataContabilizacao",
                    "categoriaNivel2",
                ),
            )

        minimum = min(dates)
        if minimum <= DATE_2021_01_01:
            return self._event_not_applicable(
                definition,
                event,
                "A primeira contabilização não é posterior a 01/01/2021.",
                columns=("dataContabilizacao",),
                values=(
                    (
                        "minDataContabilizacao",
                        minimum,
                    ),
                ),
            )

        category_level_2 = (
            event.get_serialized_value(
                "categoriaNivel2"
            )
        )

        values = (
            (
                "minDataContabilizacao",
                minimum,
            ),
            (
                "categoriaNivel2",
                category_level_2,
            ),
        )

        if category_level_2 is None:
            return self._event_failed(
                definition,
                event,
                "Evento posterior a 01/01/2021 sem categoriaNivel2.",
                columns=(
                    "dataContabilizacao",
                    "categoriaNivel2",
                ),
                values=values,
                suggestion=(
                    "Informar o segundo nível de "
                    "classificação Basileia II."
                ),
            )

        return self._event_passed(
            definition,
            event,
            "O evento possui categoriaNivel2.",
            columns=(
                "dataContabilizacao",
                "categoriaNivel2",
            ),
            values=values,
        )

    def _dro000032(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
    ) -> PostProcessingEvidence:
        category = event.get_serialized_value(
            "categoriaNivel1"
        )

        if category is None:
            return self._event_not_executed(
                definition,
                event,
                "A categoria de nível 1 não está resolvida.",
                columns=("categoriaNivel1",),
            )

        if category not in {"1", "2"}:
            return self._event_not_applicable(
                definition,
                event,
                "O evento não pertence às categorias 1 ou 2.",
                columns=("categoriaNivel1",),
                values=(
                    ("categoriaNivel1", category),
                ),
            )

        provision = event.get_value(
            "totalProvisao"
        )
        if not isinstance(provision, Decimal):
            return self._event_not_executed(
                definition,
                event,
                "O total de provisão não está resolvido.",
                columns=(
                    "categoriaNivel1",
                    "totalProvisao",
                ),
            )

        values = (
            ("categoriaNivel1", category),
            ("totalProvisao", provision),
        )

        if provision > Decimal("0"):
            return self._event_failed(
                definition,
                event,
                "Evento de fraude com totalProvisao maior que zero.",
                columns=(
                    "categoriaNivel1",
                    "totalProvisao",
                ),
                values=values,
                suggestion=(
                    "Revisar a provisão atribuída ao "
                    "evento de fraude."
                ),
            )

        return self._event_passed(
            definition,
            event,
            "O evento de fraude não possui provisão positiva.",
            columns=(
                "categoriaNivel1",
                "totalProvisao",
            ),
            values=values,
        )

    def _consolidated_evidences(
        self,
        definition: PostProcessingRuleDefinition,
        events: tuple[
            FinalConsolidatedEvent,
            ...,
        ],
    ) -> tuple[PostProcessingEvidence, ...]:
        if not events:
            return (
                self._not_executed(
                    definition=definition,
                    source_stage=(
                        "Eventos consolidados"
                    ),
                    message=(
                        "O bloco consolidado não foi "
                        "calculado de forma determinística."
                    ),
                    columns=self._consolidated_columns(
                        definition.code
                    ),
                    values=(
                        (
                            "quantidadeEventosConsolidados",
                            0,
                        ),
                    ),
                ),
            )

        handler = {
            "DRO000001": self._consolidated_average_semester,
            "DRO000002": self._consolidated_average_total,
            "DRO000018": self._consolidated_loss_sign,
            "DRO000019": self._consolidated_provision_sign,
        }[definition.code]

        return tuple(
            handler(definition, event)
            for event in events
        )

    def _consolidated_average_semester(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
    ) -> PostProcessingEvidence:
        return self._consolidated_average(
            definition=definition,
            event=event,
            count=event.semester_event_count,
            loss=event.semester_loss,
            provision=event.semester_provision,
            period="semestre",
            columns=(
                "perdaEfetivaSemestreConsol",
                "provisaoSemestreConsol",
                "numEventosSemestreConsol",
            ),
        )

    def _consolidated_average_total(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
    ) -> PostProcessingEvidence:
        return self._consolidated_average(
            definition=definition,
            event=event,
            count=event.total_event_count,
            loss=event.total_loss,
            provision=event.total_provision,
            period="acumulado",
            columns=(
                "perdaEfetivaTotalConsol",
                "provisaoTotalConsol",
                "numEventosTotalConsol",
            ),
        )

    def _consolidated_average(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        count: int,
        loss: Decimal,
        provision: Decimal,
        period: str,
        columns: tuple[str, ...],
    ) -> PostProcessingEvidence:
        gross = loss + provision

        if count < 0:
            return self._consolidated_not_executed(
                definition,
                event,
                "A quantidade de eventos é negativa.",
                columns=columns,
            )

        if count == 0:
            if gross == Decimal("0"):
                return self._consolidated_not_applicable(
                    definition,
                    event,
                    "Não há eventos no período para calcular média.",
                    columns=columns,
                )

            return self._consolidated_not_executed(
                definition,
                event,
                "A média é indefinida: quantidade zero com valor acumulado diferente de zero.",
                columns=columns,
                values=(
                    ("perdaBruta", gross),
                    ("quantidade", count),
                ),
            )

        average = gross / Decimal(count)
        values = (
            ("perdaBruta", gross),
            ("quantidade", count),
            ("media", average),
            ("limite", LIMIT_ONE_THOUSAND),
        )

        if average > LIMIT_ONE_THOUSAND:
            return self._consolidated_failed(
                definition,
                event,
                f"A média de perda bruta do {period} é superior a R$ 1.000,00.",
                columns=columns,
                values=values,
            )

        return self._consolidated_passed(
            definition,
            event,
            f"A média de perda bruta do {period} não supera R$ 1.000,00.",
            columns=columns,
            values=values,
        )

    def _consolidated_loss_sign(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
    ) -> PostProcessingEvidence:
        value = event.total_loss
        values = (
            ("perdaEfetivaTotalConsol", value),
            ("limite", NEGATIVE_LIMIT),
        )

        if value < NEGATIVE_LIMIT:
            return self._consolidated_failed(
                definition,
                event,
                "A perda efetiva consolidada é inferior a -10,00.",
                columns=(
                    "perdaEfetivaTotalConsol",
                ),
                values=values,
            )

        return self._consolidated_passed(
            definition,
            event,
            "A perda efetiva consolidada respeita o limite da crítica.",
            columns=(
                "perdaEfetivaTotalConsol",
            ),
            values=values,
        )

    def _consolidated_provision_sign(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
    ) -> PostProcessingEvidence:
        value = event.total_provision
        values = (
            ("provisaoTotalConsol", value),
            ("limite", NEGATIVE_LIMIT),
        )

        if value < NEGATIVE_LIMIT:
            return self._consolidated_failed(
                definition,
                event,
                "A provisão consolidada é inferior a -10,00.",
                columns=("provisaoTotalConsol",),
                values=values,
            )

        return self._consolidated_passed(
            definition,
            event,
            "A provisão consolidada respeita o limite da crítica.",
            columns=("provisaoTotalConsol",),
            values=values,
        )

    @staticmethod
    def _consolidated_columns(
        code: str,
    ) -> tuple[str, ...]:
        return {
            "DRO000001": (
                "perdaEfetivaSemestreConsol",
                "provisaoSemestreConsol",
                "numEventosSemestreConsol",
            ),
            "DRO000002": (
                "perdaEfetivaTotalConsol",
                "provisaoTotalConsol",
                "numEventosTotalConsol",
            ),
            "DRO000018": (
                "perdaEfetivaTotalConsol",
            ),
            "DRO000019": (
                "provisaoTotalConsol",
            ),
        }[code]

    def _consolidated_passed(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._consolidated_evidence(
            definition=definition,
            event=event,
            status=RuleExecutionStatus.PASSED,
            message=message,
            columns=columns,
            values=values,
        )

    def _consolidated_failed(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._consolidated_evidence(
            definition=definition,
            event=event,
            status=RuleExecutionStatus.FAILED,
            message=message,
            columns=columns,
            values=values,
            suggestion=definition.observations,
        )

    def _consolidated_not_applicable(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
    ) -> PostProcessingEvidence:
        return self._consolidated_evidence(
            definition=definition,
            event=event,
            status=(
                RuleExecutionStatus.NOT_APPLICABLE
            ),
            message=message,
            columns=columns,
        )

    def _consolidated_not_executed(
        self,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._consolidated_evidence(
            definition=definition,
            event=event,
            status=(
                RuleExecutionStatus.NOT_EXECUTED
            ),
            message=message,
            columns=columns,
            values=values,
        )

    def _consolidated_evidence(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        event: FinalConsolidatedEvent,
        status: RuleExecutionStatus,
        message: str,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
        suggestion: str | None = None,
    ) -> PostProcessingEvidence:
        return self._evidence(
            definition=definition,
            status=status,
            source_stage="Eventos consolidados",
            message=message,
            sheet_name="Base",
            row_numbers=event.source_rows,
            columns=columns,
            category_level_1=(
                event.category_level_1
            ),
            values=(
                (
                    "categoriaNivel1Consol",
                    event.category_level_1,
                ),
                *values,
            ),
            original_values=tuple(
                (column, original)
                for column, original in event.source_original_values
                if column in {"categoriaNivel1Consol", *columns}
            ),
            suggestion=suggestion,
        )

    def _event_passed(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._event_evidence(
            definition=definition,
            event=event,
            status=RuleExecutionStatus.PASSED,
            message=message,
            columns=columns,
            values=values,
        )

    def _event_failed(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
        suggestion: str | None = None,
    ) -> PostProcessingEvidence:
        return self._event_evidence(
            definition=definition,
            event=event,
            status=RuleExecutionStatus.FAILED,
            message=message,
            columns=columns,
            values=values,
            suggestion=suggestion,
        )

    def _event_not_applicable(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._event_evidence(
            definition=definition,
            event=event,
            status=(
                RuleExecutionStatus.NOT_APPLICABLE
            ),
            message=message,
            columns=columns,
            values=values,
        )

    def _event_not_executed(
        self,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
        message: str,
        *,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._event_evidence(
            definition=definition,
            event=event,
            status=(
                RuleExecutionStatus.NOT_EXECUTED
            ),
            message=message,
            columns=columns,
            values=values,
        )

    def _event_evidence(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        event: GroupedEvent,
        status: RuleExecutionStatus,
        message: str,
        columns: tuple[str, ...],
        values: tuple[tuple[str, Any], ...] = (),
        suggestion: str | None = None,
    ) -> PostProcessingEvidence:
        return self._evidence(
            definition=definition,
            status=status,
            source_stage=(
                "Validação local de pós-processamento"
            ),
            message=message,
            row_numbers=event.row_numbers,
            columns=columns,
            id_evento=event.id_evento,
            suggestion=suggestion,
            values=values,
        )

    def _not_executed(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        source_stage: str,
        message: str,
        columns: tuple[str, ...] = (),
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return self._evidence(
            definition=definition,
            status=(
                RuleExecutionStatus.NOT_EXECUTED
            ),
            source_stage=source_stage,
            message=message,
            columns=columns,
            values=values,
        )

    def _evidence(
        self,
        *,
        definition: PostProcessingRuleDefinition,
        status: RuleExecutionStatus,
        source_stage: str,
        message: str,
        sheet_name: str | None = None,
        row_numbers: tuple[int, ...] = (),
        columns: tuple[str, ...] = (),
        id_evento: str | None = None,
        category_level_1: str | None = None,
        suggestion: str | None = None,
        original_values: tuple[tuple[str, Any], ...] = (),
        values: tuple[tuple[str, Any], ...] = (),
    ) -> PostProcessingEvidence:
        return PostProcessingEvidence(
            status=status,
            severity=self._severity(
                definition,
                status,
            ),
            source_stage=source_stage,
            message=message,
            sheet_name=sheet_name,
            row_numbers=row_numbers,
            columns=columns,
            id_evento=id_evento,
            category_level_1=category_level_1,
            suggestion=suggestion,
            original_values=original_values,
            values=values,
        )

    @staticmethod
    def _severity(
        definition: PostProcessingRuleDefinition,
        status: RuleExecutionStatus,
    ) -> str:
        if status == RuleExecutionStatus.NOT_EXECUTED:
            return SEVERITY_NOT_EXECUTED

        if status == RuleExecutionStatus.FAILED:
            return (
                SEVERITY_WARNING
                if definition.is_clarification
                else SEVERITY_ERROR
            )

        return SEVERITY_INFORMATION

    @staticmethod
    def _adapt_result(
        result: Any,
        *,
        source_stage: str,
    ) -> PostProcessingEvidence:
        row_numbers = getattr(
            result,
            "row_numbers",
            None,
        )

        if row_numbers is None:
            row_number = getattr(
                result,
                "row_number",
                None,
            )
            row_numbers = (
                (row_number,)
                if row_number is not None
                else ()
            )

        values = getattr(
            result,
            "values",
            None,
        )
        if values is None:
            values = (
                *getattr(
                    result,
                    "original_values",
                    (),
                ),
                *getattr(
                    result,
                    "normalized_values",
                    (),
                ),
            )

        return PostProcessingEvidence(
            status=result.status,
            severity=result.severity,
            source_stage=source_stage,
            message=result.message,
            row_numbers=tuple(row_numbers),
            columns=tuple(
                getattr(result, "columns", ())
            ),
            id_evento=getattr(
                result,
                "id_evento",
                None,
            ),
            suggestion=getattr(
                result,
                "suggestion",
                None,
            ),
            values=tuple(values),
        )

    @staticmethod
    def _aggregate_status(
        evidences: tuple[
            PostProcessingEvidence,
            ...,
        ],
    ) -> RuleExecutionStatus:
        statuses = {
            evidence.status
            for evidence in evidences
        }

        if RuleExecutionStatus.FAILED in statuses:
            return RuleExecutionStatus.FAILED

        if (
            RuleExecutionStatus.NOT_EXECUTED
            in statuses
        ):
            return RuleExecutionStatus.NOT_EXECUTED

        if RuleExecutionStatus.PASSED in statuses:
            return RuleExecutionStatus.PASSED

        return RuleExecutionStatus.NOT_APPLICABLE

    @staticmethod
    def _index_by_code(
        results: Iterable[Any],
    ) -> dict[str, list[Any]]:
        indexed: dict[str, list[Any]] = defaultdict(list)

        for result in results:
            indexed[result.code].append(result)

        return dict(indexed)

    def _validate_catalog(self) -> None:
        codes = tuple(
            definition.code
            for definition in self.catalog
        )

        if len(codes) != 26:
            raise ValueError(
                "O catálogo deve possuir exatamente "
                "26 críticas de pós-processamento."
            )

        if len(set(codes)) != len(codes):
            raise ValueError(
                "O catálogo possui códigos duplicados."
            )


def validate_post_processing(
    *,
    header: DocumentHeader,
    profile: RegulatoryVersion,
    grouping: EventGroupingResult,
    row_validation: BaseRowsValidationResult,
    financial_validation: (
        EventsFinancialValidationResult
    ),
    consolidated_events: Iterable[
        FinalConsolidatedEvent
    ] = (),
) -> PostProcessingValidationResult:
    """Atalho funcional para as críticas oficiais."""

    return PostProcessingValidator().validate(
        header=header,
        profile=profile,
        grouping=grouping,
        row_validation=row_validation,
        financial_validation=financial_validation,
        consolidated_events=consolidated_events,
    )
