"""Validação de totais, contabilizações e saldos do evento.

Regras oficiais locais implementadas nesta etapa:

- DRO000011;
- DRO000012;
- DRO000013;
- DRO000014;
- DRO000015;
- DRO000023;
- DRO000024.

Não são utilizados valores aproximados nem tolerância inventada. Os
limites de R$ 10,00 presentes em DRO000011 e DRO000012 são aplicados
exatamente como descritos nas críticas de pós-processamento fornecidas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Callable

from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.event_financial import (
    AccountingDayBalance,
    EventFinancialSummary,
    EventFinancialValidationResult,
    EventsFinancialValidationResult,
    ZERO,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventRuleResult,
    GroupedEvent,
)
from src.domain.regulatory_version import RegulatoryVersion


SEVERITY_ERROR = "ERRO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"

NEGATIVE_TOTAL_THRESHOLD = Decimal("-10.00")

TOTAL_FIELD_MAP = {
    "totalPerdaEfetiva": "valorPerdaEfetiva",
    "totalProvisao": "valorProvisao",
    "totalRecuperado": "valorRecuperacao",
}


class EventFinancialValidator:
    """Executa as regras financeiras no nível do evento."""

    def validate(
        self,
        grouping: EventGroupingResult,
        profile: RegulatoryVersion,
    ) -> EventsFinancialValidationResult:
        events = tuple(
            self._validate_event(event)
            for event in grouping.events
        )
        rule_results = tuple(
            result
            for event in events
            for result in event.rule_results
        )

        return EventsFinancialValidationResult(
            profile_code=profile.code,
            events=events,
            rule_results=rule_results,
        )

    def _validate_event(
        self,
        event: GroupedEvent,
    ) -> EventFinancialValidationResult:
        summary = self._build_summary(event)

        functions: tuple[
            Callable[[], EventRuleResult],
            ...,
        ] = (
            lambda: self._validate_total_loss_sign(
                event,
                summary,
            ),
            lambda: self._validate_total_provision_sign(
                event,
                summary,
            ),
            lambda: self._validate_total_recovery_sign(
                event,
                summary,
            ),
            lambda: self._validate_recovery_limit(
                event,
                summary,
            ),
            lambda: self._validate_totals_against_accountings(
                event,
                summary,
            ),
            lambda: self._validate_accumulated_loss_balance(
                event,
                summary,
            ),
            lambda: self._validate_accumulated_provision_balance(
                event,
                summary,
            ),
        )

        return EventFinancialValidationResult(
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            summary=summary,
            rule_results=tuple(
                function()
                for function in functions
            ),
        )

    def _build_summary(
        self,
        event: GroupedEvent,
    ) -> EventFinancialSummary:
        accounting_loss_sum = ZERO
        accounting_provision_sum = ZERO
        accounting_recovery_sum = ZERO
        undated_rows: list[int] = []

        by_date: dict[
            date,
            list[tuple[int, Decimal, Decimal, Decimal]],
        ] = defaultdict(list)

        for accounting in event.accountings:
            loss = self._decimal_or_zero(
                accounting.get_value(
                    "valorPerdaEfetiva"
                )
            )
            provision = self._decimal_or_zero(
                accounting.get_value(
                    "valorProvisao"
                )
            )
            recovery = self._decimal_or_zero(
                accounting.get_value(
                    "valorRecuperacao"
                )
            )

            accounting_loss_sum += loss
            accounting_provision_sum += provision
            accounting_recovery_sum += recovery

            accounting_date = accounting.get_value(
                "dataContabilizacao"
            )
            if not isinstance(accounting_date, date):
                undated_rows.append(
                    accounting.row_number
                )
                continue

            by_date[accounting_date].append(
                (
                    accounting.row_number,
                    loss,
                    provision,
                    recovery,
                )
            )

        daily_balances: list[AccountingDayBalance] = []
        current_loss = ZERO
        current_provision = ZERO
        current_recovery = ZERO

        for accounting_date in sorted(by_date):
            entries = by_date[accounting_date]
            row_numbers = tuple(
                row_number
                for row_number, *_ in entries
            )
            losses = tuple(
                loss
                for _, loss, _, _ in entries
            )
            provisions = tuple(
                provision
                for _, _, provision, _ in entries
            )
            recoveries = tuple(
                recovery
                for _, _, _, recovery in entries
            )

            loss_movement = sum(losses, ZERO)
            provision_movement = sum(
                provisions,
                ZERO,
            )
            recovery_movement = sum(
                recoveries,
                ZERO,
            )

            minimum_loss = (
                current_loss
                + sum(
                    (
                        value
                        for value in losses
                        if value < ZERO
                    ),
                    ZERO,
                )
            )
            minimum_provision = (
                current_provision
                + sum(
                    (
                        value
                        for value in provisions
                        if value < ZERO
                    ),
                    ZERO,
                )
            )

            closing_loss = (
                current_loss + loss_movement
            )
            closing_provision = (
                current_provision
                + provision_movement
            )
            current_recovery += recovery_movement

            daily_balances.append(
                AccountingDayBalance(
                    accounting_date=accounting_date,
                    row_numbers=row_numbers,
                    loss_movements=losses,
                    provision_movements=provisions,
                    recovery_movements=recoveries,
                    opening_loss_balance=current_loss,
                    closing_loss_balance=closing_loss,
                    minimum_possible_loss_balance=(
                        minimum_loss
                    ),
                    opening_provision_balance=(
                        current_provision
                    ),
                    closing_provision_balance=(
                        closing_provision
                    ),
                    minimum_possible_provision_balance=(
                        minimum_provision
                    ),
                    closing_recovery_balance=(
                        current_recovery
                    ),
                )
            )

            current_loss = closing_loss
            current_provision = closing_provision

        return EventFinancialSummary(
            id_evento=event.id_evento,
            row_numbers=event.row_numbers,
            accounting_row_numbers=tuple(
                accounting.row_number
                for accounting in event.accountings
            ),
            declared_total_loss=self._event_decimal(
                event,
                "totalPerdaEfetiva",
            ),
            declared_total_provision=self._event_decimal(
                event,
                "totalProvisao",
            ),
            declared_total_recovery=self._event_decimal(
                event,
                "totalRecuperado",
            ),
            accounting_loss_sum=accounting_loss_sum,
            accounting_provision_sum=(
                accounting_provision_sum
            ),
            accounting_recovery_sum=(
                accounting_recovery_sum
            ),
            daily_balances=tuple(daily_balances),
            undated_accounting_rows=tuple(
                undated_rows
            ),
        )

    def _validate_total_loss_sign(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        code = "DRO000011"
        description = (
            "Verificar se totalPerdaEfetiva é inferior "
            "a -R$ 10,00."
        )
        value = summary.declared_total_loss

        dependency = self._total_dependency(
            event,
            field_name="totalPerdaEfetiva",
            code=code,
            description=description,
        )
        if dependency is not None:
            return dependency

        assert value is not None

        if value < NEGATIVE_TOTAL_THRESHOLD:
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=SEVERITY_ERROR,
                columns=("totalPerdaEfetiva",),
                message=(
                    "totalPerdaEfetiva é "
                    f"{value:.2f}, inferior a -10,00."
                ),
                suggestion=(
                    "Revisar perdas e estornos do evento."
                ),
                values=(
                    ("totalPerdaEfetiva", value),
                    (
                        "limiteInferior",
                        NEGATIVE_TOTAL_THRESHOLD,
                    ),
                ),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=("totalPerdaEfetiva",),
            message=(
                "totalPerdaEfetiva não ultrapassa o "
                "limite negativo definido pela crítica."
            ),
            values=(
                ("totalPerdaEfetiva", value),
            ),
        )

    def _validate_total_provision_sign(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        code = "DRO000012"
        description = (
            "Verificar se totalProvisao é inferior "
            "a -R$ 10,00."
        )
        value = summary.declared_total_provision

        dependency = self._total_dependency(
            event,
            field_name="totalProvisao",
            code=code,
            description=description,
        )
        if dependency is not None:
            return dependency

        assert value is not None

        if value < NEGATIVE_TOTAL_THRESHOLD:
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=SEVERITY_ERROR,
                columns=("totalProvisao",),
                message=(
                    "totalProvisao é "
                    f"{value:.2f}, inferior a -10,00."
                ),
                suggestion=(
                    "Revisar provisões e estornos do evento."
                ),
                values=(
                    ("totalProvisao", value),
                    (
                        "limiteInferior",
                        NEGATIVE_TOTAL_THRESHOLD,
                    ),
                ),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=("totalProvisao",),
            message=(
                "totalProvisao não ultrapassa o "
                "limite negativo definido pela crítica."
            ),
            values=(("totalProvisao", value),),
        )

    def _validate_total_recovery_sign(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        code = "DRO000013"
        description = (
            "Verificar se totalRecuperado possui "
            "sinal positivo."
        )
        value = summary.declared_total_recovery

        dependency = self._total_dependency(
            event,
            field_name="totalRecuperado",
            code=code,
            description=description,
        )
        if dependency is not None:
            return dependency

        assert value is not None

        if value > ZERO:
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=SEVERITY_ERROR,
                columns=("totalRecuperado",),
                message=(
                    "totalRecuperado foi informado "
                    f"como {value:.2f}, com sinal positivo."
                ),
                suggestion=(
                    "Revisar a convenção de sinal. "
                    "Recuperações usam sinal negativo."
                ),
                values=(("totalRecuperado", value),),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=("totalRecuperado",),
            message=(
                "totalRecuperado respeita a convenção "
                "de sinal não positivo."
            ),
            values=(("totalRecuperado", value),),
        )

    def _validate_recovery_limit(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        code = "DRO000014"
        description = (
            "Verificar se o módulo do total recuperado "
            "não supera a perda bruta."
        )
        fields = (
            "totalRecuperado",
            "totalPerdaEfetiva",
            "totalProvisao",
        )
        dependency = self._totals_dependency(
            event,
            fields=fields,
            code=code,
            description=description,
        )
        if dependency is not None:
            return dependency

        recovery = summary.declared_total_recovery
        loss = summary.declared_total_loss
        provision = summary.declared_total_provision
        assert recovery is not None
        assert loss is not None
        assert provision is not None

        recovery_module = abs(recovery)
        gross_loss = loss + provision

        if recovery_module > gross_loss:
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=SEVERITY_ERROR,
                columns=fields,
                message=(
                    f"|totalRecuperado|={recovery_module:.2f} "
                    f"supera totalPerdaEfetiva + "
                    f"totalProvisao={gross_loss:.2f}."
                ),
                suggestion=(
                    "Revisar o total recuperado e a perda "
                    "bruta declarada."
                ),
                values=(
                    (
                        "moduloTotalRecuperado",
                        recovery_module,
                    ),
                    ("perdaBruta", gross_loss),
                ),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=fields,
            message=(
                "O módulo do total recuperado não "
                "supera a perda bruta."
            ),
            values=(
                (
                    "moduloTotalRecuperado",
                    recovery_module,
                ),
                ("perdaBruta", gross_loss),
            ),
        )

    def _validate_totals_against_accountings(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        code = "DRO000015"
        description = (
            "Conferir os totais do evento contra a "
            "soma das contabilizações."
        )
        fields = (
            "totalPerdaEfetiva",
            "totalProvisao",
            "totalRecuperado",
            "valorPerdaEfetiva",
            "valorProvisao",
            "valorRecuperacao",
        )
        dependency = self._totals_dependency(
            event,
            fields=(
                "totalPerdaEfetiva",
                "totalProvisao",
                "totalRecuperado",
            ),
            code=code,
            description=description,
            columns=fields,
        )
        if dependency is not None:
            return dependency

        differences = {
            "perda": summary.loss_difference,
            "provisao": summary.provision_difference,
            "recuperacao": summary.recovery_difference,
        }
        mismatches = tuple(
            name
            for name, difference in differences.items()
            if difference != ZERO
        )

        if mismatches:
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=SEVERITY_ERROR,
                columns=fields,
                message=(
                    "Os totais não correspondem às "
                    "contabilizações em: "
                    f"{', '.join(mismatches)}."
                ),
                suggestion=(
                    "Revisar os totais declarados e todos "
                    "os lançamentos parciais do evento."
                ),
                values=(
                    (
                        "totalPerdaEfetiva",
                        summary.declared_total_loss,
                    ),
                    (
                        "somaValorPerdaEfetiva",
                        summary.accounting_loss_sum,
                    ),
                    (
                        "diferencaPerda",
                        summary.loss_difference,
                    ),
                    (
                        "totalProvisao",
                        summary.declared_total_provision,
                    ),
                    (
                        "somaValorProvisao",
                        summary.accounting_provision_sum,
                    ),
                    (
                        "diferencaProvisao",
                        summary.provision_difference,
                    ),
                    (
                        "totalRecuperado",
                        summary.declared_total_recovery,
                    ),
                    (
                        "somaValorRecuperacao",
                        summary.accounting_recovery_sum,
                    ),
                    (
                        "diferencaRecuperacao",
                        summary.recovery_difference,
                    ),
                ),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=fields,
            message=(
                "Os três totais correspondem exatamente "
                "à soma das contabilizações."
            ),
            values=(
                (
                    "somaValorPerdaEfetiva",
                    summary.accounting_loss_sum,
                ),
                (
                    "somaValorProvisao",
                    summary.accounting_provision_sum,
                ),
                (
                    "somaValorRecuperacao",
                    summary.accounting_recovery_sum,
                ),
            ),
        )

    def _validate_accumulated_loss_balance(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        return self._validate_accumulated_balance(
            event=event,
            summary=summary,
            code="DRO000023",
            description=(
                "Verificar saldo acumulado negativo "
                "de perda efetiva."
            ),
            movement_name="perda",
            columns=(
                "dataContabilizacao",
                "valorPerdaEfetiva",
            ),
            severity=SEVERITY_ERROR,
        )

    def _validate_accumulated_provision_balance(
        self,
        event: GroupedEvent,
        summary: EventFinancialSummary,
    ) -> EventRuleResult:
        return self._validate_accumulated_balance(
            event=event,
            summary=summary,
            code="DRO000024",
            description=(
                "Verificar saldo acumulado negativo "
                "de provisão."
            ),
            movement_name="provisao",
            columns=(
                "dataContabilizacao",
                "valorProvisao",
            ),
            severity=SEVERITY_WARNING,
        )

    def _validate_accumulated_balance(
        self,
        *,
        event: GroupedEvent,
        summary: EventFinancialSummary,
        code: str,
        description: str,
        movement_name: str,
        columns: tuple[str, ...],
        severity: str,
    ) -> EventRuleResult:
        if not event.is_grouping_valid:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source="Crítica de pós-processamento",
                columns=columns,
                message=(
                    "O evento possui conflito de agrupamento."
                ),
            )

        if not event.accountings:
            return self._not_applicable(
                event=event,
                code=code,
                description=description,
                source="Crítica de pós-processamento",
                columns=columns,
                message=(
                    "O evento não possui contabilizações."
                ),
            )

        if summary.undated_accounting_rows:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source="Crítica de pós-processamento",
                columns=columns,
                message=(
                    "Há contabilizações sem data válida "
                    "nas linhas: "
                    + ", ".join(
                        str(row)
                        for row in (
                            summary
                            .undated_accounting_rows
                        )
                    )
                    + "."
                ),
            )

        if movement_name == "perda":
            definite_negative = tuple(
                day
                for day in summary.daily_balances
                if day.closing_loss_balance < ZERO
            )
            ambiguous = tuple(
                day
                for day in summary.daily_balances
                if day.loss_order_is_ambiguous
            )
            final_balance = (
                summary.final_loss_balance
            )
        else:
            definite_negative = tuple(
                day
                for day in summary.daily_balances
                if day.closing_provision_balance < ZERO
            )
            ambiguous = tuple(
                day
                for day in summary.daily_balances
                if day.provision_order_is_ambiguous
            )
            final_balance = (
                summary.final_provision_balance
            )

        if definite_negative:
            first = definite_negative[0]
            closing = (
                first.closing_loss_balance
                if movement_name == "perda"
                else first.closing_provision_balance
            )
            return self._failed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento"
                ),
                severity=severity,
                columns=columns,
                message=(
                    f"O saldo acumulado de {movement_name} "
                    f"fechou negativo em "
                    f"{first.accounting_date.isoformat()}: "
                    f"{closing:.2f}."
                ),
                suggestion=(
                    "Revisar os lançamentos e estornos "
                    "anteriores a essa data."
                ),
                values=(
                    (
                        "dataPrimeiroSaldoNegativo",
                        first.accounting_date.isoformat(),
                    ),
                    ("saldoNegativo", closing),
                    (
                        "linhasDaData",
                        first.row_numbers,
                    ),
                ),
            )

        if ambiguous:
            first = ambiguous[0]
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source=(
                    "Crítica de pós-processamento "
                    "e limitação da fonte"
                ),
                columns=columns,
                message=(
                    "A ordem intradiária pode alterar o "
                    f"saldo de {movement_name} em "
                    f"{first.accounting_date.isoformat()}. "
                    "A fonte informa somente a data, sem "
                    "horário ou sequência oficial."
                ),
                values=(
                    (
                        "dataAmbigua",
                        first.accounting_date.isoformat(),
                    ),
                    (
                        "linhasDaData",
                        first.row_numbers,
                    ),
                ),
            )

        return self._passed(
            event=event,
            code=code,
            description=description,
            source="Crítica de pós-processamento",
            columns=columns,
            message=(
                f"O saldo acumulado de {movement_name} "
                "não ficou negativo nas datas avaliadas."
            ),
            values=(
                ("saldoFinal", final_balance),
            ),
        )

    def _total_dependency(
        self,
        event: GroupedEvent,
        *,
        field_name: str,
        code: str,
        description: str,
    ) -> EventRuleResult | None:
        return self._totals_dependency(
            event,
            fields=(field_name,),
            code=code,
            description=description,
        )

    def _totals_dependency(
        self,
        event: GroupedEvent,
        *,
        fields: tuple[str, ...],
        code: str,
        description: str,
        columns: tuple[str, ...] | None = None,
    ) -> EventRuleResult | None:
        result_columns = columns or fields

        if not event.is_grouping_valid:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source="Crítica de pós-processamento",
                columns=result_columns,
                message=(
                    "O evento possui conflito de agrupamento."
                ),
            )

        unresolved = tuple(
            field_name
            for field_name in fields
            if (
                event.get_field(
                    field_name
                ).has_conflict
                or event.get_field(
                    field_name
                ).invalid_rows
                or event.get_field(
                    field_name
                ).serialized_value is None
                or not isinstance(
                    event.get_value(field_name),
                    Decimal,
                )
            )
        )

        if unresolved:
            return self._not_executed(
                event=event,
                code=code,
                description=description,
                source="Crítica de pós-processamento",
                columns=result_columns,
                message=(
                    "Totais não resolvidos para execução: "
                    f"{', '.join(unresolved)}."
                ),
            )

        return None

    @staticmethod
    def _event_decimal(
        event: GroupedEvent,
        field_name: str,
    ) -> Decimal | None:
        value = event.get_value(field_name)
        return (
            value
            if isinstance(value, Decimal)
            else None
        )

    @staticmethod
    def _decimal_or_zero(
        value: object,
    ) -> Decimal:
        return (
            value
            if isinstance(value, Decimal)
            else ZERO
        )

    def _passed(
        self,
        *,
        event: GroupedEvent,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
        values: tuple[
            tuple[str, object],
            ...,
        ] = (),
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
        severity: str,
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
        values: tuple[
            tuple[str, object],
            ...,
        ] = (),
    ) -> EventRuleResult:
        return self._result(
            event=event,
            code=code,
            description=description,
            source=source,
            severity=severity,
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
        values: tuple[
            tuple[str, object],
            ...,
        ] = (),
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
            values=values,
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
        values: tuple[
            tuple[str, object],
            ...,
        ] = (),
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


def validate_event_financials(
    grouping: EventGroupingResult,
    profile: RegulatoryVersion,
) -> EventsFinancialValidationResult:
    """Atalho funcional para o validador financeiro."""

    return EventFinancialValidator().validate(
        grouping,
        profile,
    )
