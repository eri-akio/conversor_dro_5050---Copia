"""Regras que dependem do conjunto completo de linhas do evento."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from src.domain.base_row_validation import (
    RuleExecutionStatus,
)
from src.domain.grouped_event import (
    EventRuleResult,
    EventValidationResult,
    EventsValidationResult,
    GroupedEvent,
    EventGroupingResult,
)
from src.domain.regulatory_version import RegulatoryVersion


SEVERITY_ERROR = 'ERRO'
SEVERITY_INFORMATION = 'INFORMAÇÃO'
SEVERITY_NOT_EXECUTED = 'REGRA NÃO EXECUTADA'
CIRCULAR_START_DATE = date(2021, 1, 1)


class EventConsistencyValidator:
    """Executa regras oficiais e internas no nível do idEvento."""

    def validate(
        self,
        grouping: EventGroupingResult,
        profile: RegulatoryVersion,
    ) -> EventsValidationResult:
        events = tuple(
            self._validate_event(event, profile)
            for event in grouping.events
        )
        results = tuple(
            result
            for event in events
            for result in event.rule_results
        )
        return EventsValidationResult(
            profile_code=profile.code,
            events=events,
            rule_results=results,
        )

    def _validate_event(
        self,
        event: GroupedEvent,
        profile: RegulatoryVersion,
    ) -> EventValidationResult:
        functions: tuple[Callable[[], EventRuleResult], ...] = (
            lambda: self._validate_unique_event_element(event),
            lambda: self._validate_total_risk_composition(event),
            lambda: self._validate_probability_required(
                event,
                profile,
            ),
            lambda: self._validate_positive_risk_sum(
                event,
                profile,
            ),
            lambda: self._validate_risk_only_accounting(event),
        )
        return EventValidationResult(
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            grouping_valid=event.is_grouping_valid,
            rule_results=tuple(function() for function in functions),
        )

    def _validate_unique_event_element(
        self,
        event: GroupedEvent,
    ) -> EventRuleResult:
        return self._passed(
            event=event,
            code='DRO001103',
            description=(
                'Garantir a unicidade do idEvento no documento gerado.'
            ),
            source='Crítica de pré-processamento',
            columns=('idEvento',),
            message=(
                'Todas as linhas foram reunidas em um único evento lógico.'
            ),
            values=(('quantidadeLinhas', len(event.row_numbers)),),
        )

    def _validate_total_risk_composition(
        self,
        event: GroupedEvent,
    ) -> EventRuleResult:
        columns = (
            'valorTotalRisco',
            'totalProvisao',
            'probabilidadePerda',
            'valorRisco',
        )
        dependency = self._grouping_dependency(
            event,
            code='DRO001311',
            description=(
                'Verificar a composição do valorTotalRisco.'
            ),
            columns=columns,
            required_event_fields=(
                'valorTotalRisco',
                'totalProvisao',
            ),
            probability_required=False,
        )
        if dependency is not None:
            return dependency

        total_risk_field = event.get_field('valorTotalRisco')
        if total_risk_field.serialized_value is None:
            return self._not_applicable(
                event=event,
                code='DRO001311',
                description=(
                    'Verificar a composição do valorTotalRisco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='valorTotalRisco não foi informado.',
            )

        total_risk = event.get_value('valorTotalRisco')
        provision = event.get_value(
            'totalProvisao',
            Decimal('0'),
        )
        probability_sum = event.probability_sum

        if (
            not isinstance(total_risk, Decimal)
            or not isinstance(provision, Decimal)
            or probability_sum is None
        ):
            return self._not_executed(
                event=event,
                code='DRO001311',
                description=(
                    'Verificar a composição do valorTotalRisco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    'Não foi possível obter todos os valores monetários '
                    'normalizados do evento.'
                ),
            )

        expected = provision + probability_sum
        if total_risk != expected:
            return self._failed(
                event=event,
                code='DRO001311',
                description=(
                    'Verificar a composição do valorTotalRisco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    f'valorTotalRisco={total_risk:.2f}, mas '
                    f'totalProvisao + soma(valorRisco)={expected:.2f}.'
                ),
                suggestion=(
                    'Revisar o total do evento e os valores de cada '
                    'probabilidade.'
                ),
                values=(
                    ('valorTotalRisco', total_risk),
                    ('totalProvisao', provision),
                    ('somaValorRisco', probability_sum),
                ),
            )

        return self._passed(
            event=event,
            code='DRO001311',
            description='Verificar a composição do valorTotalRisco.',
            source='Crítica de pré-processamento',
            columns=columns,
            message=(
                'valorTotalRisco corresponde a totalProvisao mais a soma '
                'dos valores de risco.'
            ),
            values=(('valorCalculado', expected),),
        )

    def _validate_probability_required(
        self,
        event: GroupedEvent,
        profile: RegulatoryVersion,
    ) -> EventRuleResult:
        columns = (
            'dataOcorrencia',
            'tipoAvaliacao',
            'probabilidadePerda',
        )
        dependency = self._grouping_dependency(
            event,
            code='DRO001312',
            description=(
                'Exigir probabilidade para avaliação individual.'
            ),
            columns=columns,
            required_event_fields=(
                'dataOcorrencia',
                'tipoAvaliacao',
            ),
            probability_required=False,
        )
        if dependency is not None:
            return dependency

        occurrence = event.get_value('dataOcorrencia')
        assessment = event.get_serialized_value('tipoAvaliacao')

        if not isinstance(occurrence, date):
            return self._not_executed(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='dataOcorrencia não pôde ser resolvida.',
            )

        if occurrence < CIRCULAR_START_DATE:
            return self._not_applicable(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='A ocorrência é anterior a 01/01/2021.',
            )

        if assessment == 'IE':
            return self._not_executed(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source=(
                    'Crítica de pré-processamento e conflito da versão '
                    '12/2026'
                ),
                columns=columns,
                message=(
                    'O código IE foi introduzido nas instruções 12/2026, '
                    'mas a crítica fornecida trata explicitamente apenas I.'
                ),
            )

        if assessment != 'I':
            return self._not_applicable(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='O tipo de avaliação não é I.',
            )

        if not event.probabilities:
            return self._failed(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    'O evento individual não possui probabilidade completa.'
                ),
                suggestion=(
                    'Informar probabilidadePerda e valorRisco reais em ao '
                    'menos uma linha do evento.'
                ),
            )

        if any(item.has_conflict for item in event.probabilities):
            return self._not_executed(
                event=event,
                code='DRO001312',
                description=(
                    'Exigir probabilidade para avaliação individual.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='As probabilidades possuem conflito de valor.',
            )

        return self._passed(
            event=event,
            code='DRO001312',
            description=(
                'Exigir probabilidade para avaliação individual.'
            ),
            source='Crítica de pré-processamento',
            columns=columns,
            message='O evento individual possui probabilidade informada.',
            values=(
                (
                    'probabilidades',
                    tuple(
                        item.probability_code
                        for item in event.probabilities
                    ),
                ),
            ),
        )

    def _validate_positive_risk_sum(
        self,
        event: GroupedEvent,
        profile: RegulatoryVersion,
    ) -> EventRuleResult:
        columns = (
            'dataOcorrencia',
            'tipoAvaliacao',
            'naturezaContingencia',
            'probabilidadePerda',
            'valorRisco',
        )
        dependency = self._grouping_dependency(
            event,
            code='DRO001314',
            description=(
                'Exigir soma de valorRisco maior que zero no contexto '
                'definido pela crítica.'
            ),
            columns=columns,
            required_event_fields=(
                'dataOcorrencia',
                'tipoAvaliacao',
                'naturezaContingencia',
            ),
            probability_required=False,
        )
        if dependency is not None:
            return dependency

        occurrence = event.get_value('dataOcorrencia')
        assessment = event.get_serialized_value('tipoAvaliacao')
        contingency = event.get_serialized_value(
            'naturezaContingencia'
        )

        if not isinstance(occurrence, date):
            return self._not_executed(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='dataOcorrencia não pôde ser resolvida.',
            )

        if occurrence < CIRCULAR_START_DATE:
            return self._not_applicable(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='A ocorrência é anterior a 01/01/2021.',
            )

        if assessment == 'IE':
            return self._not_executed(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source=(
                    'Crítica de pré-processamento e conflito da versão '
                    '12/2026'
                ),
                columns=columns,
                message=(
                    'A crítica fornecida trata explicitamente I e não '
                    'define a aplicação ao código IE.'
                ),
            )

        if (
            assessment != 'I'
            or contingency == 'NA'
            or not event.probabilities
        ):
            return self._not_applicable(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='O evento não atende a todos os gatilhos da regra.',
            )

        probability_sum = event.probability_sum
        if probability_sum is None:
            return self._not_executed(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='As probabilidades possuem valores conflitantes.',
            )

        if probability_sum <= 0:
            return self._failed(
                event=event,
                code='DRO001314',
                description=(
                    'Exigir soma de valorRisco maior que zero.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    f'A soma dos valores de risco é '
                    f'{probability_sum:.2f}.'
                ),
                suggestion='Revisar os valores de risco das probabilidades.',
                values=(('somaValorRisco', probability_sum),),
            )

        return self._passed(
            event=event,
            code='DRO001314',
            description='Exigir soma de valorRisco maior que zero.',
            source='Crítica de pré-processamento',
            columns=columns,
            message='A soma dos valores de risco é maior que zero.',
            values=(('somaValorRisco', probability_sum),),
        )

    def _validate_risk_only_accounting(
        self,
        event: GroupedEvent,
    ) -> EventRuleResult:
        columns = (
            'valorRisco',
            'dataContabilizacao',
            'valorPerdaEfetiva',
            'valorProvisao',
            'valorRecuperacao',
            'contaBalAnaliticoDebito',
            'contaBalAnaliticoCredito',
            'contaCosifDebito',
            'contaCosifCredito',
        )
        if not event.is_grouping_valid:
            return self._not_executed(
                event=event,
                code='DRO001452',
                description=(
                    'Proibir contabilização quando o evento possuir apenas '
                    'lançamentos de risco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='O evento possui conflito de agrupamento.',
            )

        probability_sum = event.probability_sum
        if probability_sum is None:
            return self._not_executed(
                event=event,
                code='DRO001452',
                description=(
                    'Proibir contabilização quando o evento possuir apenas '
                    'lançamentos de risco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='As probabilidades possuem conflito de valor.',
            )

        if probability_sum == 0:
            return self._not_applicable(
                event=event,
                code='DRO001452',
                description=(
                    'Proibir contabilização quando o evento possuir apenas '
                    'lançamentos de risco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message='O evento não possui valor de risco positivo.',
            )

        has_nonzero_accounting_movement = any(
            any(
                isinstance(record.get_value(field_name), Decimal)
                and record.get_value(field_name) != 0
                for field_name in (
                    'valorPerdaEfetiva',
                    'valorProvisao',
                    'valorRecuperacao',
                )
            )
            for record in event.accountings
        )

        if has_nonzero_accounting_movement:
            return self._not_applicable(
                event=event,
                code='DRO001452',
                description=(
                    'Proibir contabilização quando o evento possuir apenas '
                    'lançamentos de risco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    'O evento também possui movimentação de perda, provisão '
                    'ou recuperação.'
                ),
            )

        if event.accountings:
            return self._failed(
                event=event,
                code='DRO001452',
                description=(
                    'Proibir contabilização quando o evento possuir apenas '
                    'lançamentos de risco.'
                ),
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    'O evento possui somente valores em risco, mas contém '
                    'informações no bloco de contabilizações.'
                ),
                suggestion=(
                    'Remover as informações contábeis indevidas do evento '
                    'exclusivamente de risco.'
                ),
                values=(('quantidadeContabilizacoes', len(event.accountings)),),
            )

        return self._passed(
            event=event,
            code='DRO001452',
            description=(
                'Proibir contabilização quando o evento possuir apenas '
                'lançamentos de risco.'
            ),
            source='Crítica de pré-processamento',
            columns=columns,
            message=(
                'O evento exclusivamente de risco não possui '
                'contabilizações.'
            ),
        )

    def _grouping_dependency(
        self,
        event: GroupedEvent,
        *,
        code: str,
        description: str,
        columns: tuple[str, ...],
        required_event_fields: tuple[str, ...],
        probability_required: bool,
    ) -> EventRuleResult | None:
        if not event.is_grouping_valid:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source='Crítica de pré-processamento',
                columns=columns,
                message='O evento possui conflito de agrupamento.',
            )

        unresolved = tuple(
            field_name
            for field_name in required_event_fields
            if (
                event.get_field(field_name).has_conflict
                or event.get_field(field_name).invalid_rows
            )
        )
        if unresolved:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source='Crítica de pré-processamento',
                columns=columns,
                message=(
                    'Campos do evento não puderam ser resolvidos: '
                    f"{', '.join(unresolved)}."
                ),
            )

        if probability_required and not event.probabilities:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source='Crítica de pré-processamento',
                columns=columns,
                message='O evento não possui probabilidades completas.',
            )

        return None

    def _passed(
        self,
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
        values: tuple[tuple[str, object], ...] = (),
    ) -> EventRuleResult:
        return self._result(
            event=event,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.PASSED,
            columns=columns,
            message=message,
            values=values,
        )

    def _failed(
        self,
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
        values: tuple[tuple[str, object], ...] = (),
    ) -> EventRuleResult:
        return self._result(
            event=event,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_ERROR,
            status=RuleExecutionStatus.FAILED,
            columns=columns,
            message=message,
            suggestion=suggestion,
            values=values,
        )

    def _not_applicable(
        self,
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
    ) -> EventRuleResult:
        return self._result(
            event=event,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.NOT_APPLICABLE,
            columns=columns,
            message=message,
        )

    def _not_executed(
        self,
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
    ) -> EventRuleResult:
        return self._result(
            event=event,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_NOT_EXECUTED,
            status=RuleExecutionStatus.NOT_EXECUTED,
            columns=columns,
            message=message,
        )

    @staticmethod
    def _result(
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        severity: str,
        status: RuleExecutionStatus,
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
        values: tuple[tuple[str, object], ...] = (),
    ) -> EventRuleResult:
        return EventRuleResult(
            code=code,
            description=description,
            source=source,
            severity=severity,
            status=status,
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            columns=columns,
            message=message,
            suggestion=suggestion,
            values=values,
        )


def validate_grouped_events(
    grouping: EventGroupingResult,
    profile: RegulatoryVersion,
) -> EventsValidationResult:
    """Atalho funcional para o validador de eventos."""

    return EventConsistencyValidator().validate(
        grouping,
        profile,
    )
