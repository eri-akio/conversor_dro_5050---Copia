"""Validação dos códigos usados contra as tabelas auxiliares."""

from __future__ import annotations

from src.config import (
    INTERNAL_ACCOUNT_CODE_COLUMN,
    SHEET_BASE,
    SOURCE_SYSTEM_CODE_COLUMN,
)
from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.grouped_event import (
    EventGroupingResult,
    GroupedEvent,
)
from src.domain.reference_tables import (
    ReferenceTableData,
    ReferenceTableRuleResult,
    ReferenceTablesReadResult,
    ReferenceTablesValidationResult,
)


SEVERITY_ERROR = "ERRO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"


class ReferenceTablesValidator:
    """Valida referências da Base aos sistemas e contas cadastrados."""

    def validate(
        self,
        read_result: ReferenceTablesReadResult,
        grouping: EventGroupingResult,
    ) -> ReferenceTablesValidationResult:
        usage_results: list[ReferenceTableRuleResult] = []
        used_system_codes: set[str] = set()
        used_account_codes: set[str] = set()

        for event in grouping.events:
            system_result, system_code = self._validate_system_usage(
                event,
                read_result.systems,
            )
            usage_results.append(system_result)
            if system_code is not None:
                used_system_codes.add(system_code)

            for accounting in event.accountings:
                for field_name, rule_code in (
                    (
                        "contaBalAnaliticoDebito",
                        "DRO001401",
                    ),
                    (
                        "contaBalAnaliticoCredito",
                        "DRO001402",
                    ),
                ):
                    result, account_code = self._validate_account_usage(
                        event=event,
                        accounting_row=accounting.row_number,
                        account_code=accounting.get_serialized_value(
                            field_name
                        ),
                        field_name=field_name,
                        rule_code=rule_code,
                        table=read_result.accounts,
                    )
                    usage_results.append(result)
                    if account_code is not None:
                        used_account_codes.add(account_code)

        available_system_codes = set(
            read_result.systems.unique_valid_records
        )
        available_account_codes = set(
            read_result.accounts.unique_valid_records
        )

        unused_system_codes = tuple(
            sorted(available_system_codes - used_system_codes)
        )
        unused_account_codes = tuple(
            sorted(available_account_codes - used_account_codes)
        )

        usage_results.extend(
            (
                self._unused_codes_result(
                    table=read_result.systems,
                    code="TBL-SIS-INFO-001",
                    unused_codes=unused_system_codes,
                ),
                self._unused_codes_result(
                    table=read_result.accounts,
                    code="TBL-CONTA-INFO-001",
                    unused_codes=unused_account_codes,
                ),
            )
        )

        return ReferenceTablesValidationResult(
            read_result=read_result,
            usage_rule_results=tuple(usage_results),
            unused_system_codes=unused_system_codes,
            unused_account_codes=unused_account_codes,
        )

    def _validate_system_usage(
        self,
        event: GroupedEvent,
        table: ReferenceTableData,
    ) -> tuple[ReferenceTableRuleResult, str | None]:
        code = "DRO001321"
        description = (
            "Verificar se o sistema de origem do evento consta na tabela."
        )
        field = event.get_field("codSistemaOrigem")

        if (
            field.has_conflict
            or field.invalid_rows
            or field.serialized_value is None
        ):
            return (
                self._not_executed(
                    code=code,
                    description=description,
                    source="Crítica de pré-processamento",
                    sheet_name=SHEET_BASE,
                    row_numbers=event.row_numbers,
                    columns=("codSistemaOrigem",),
                    id_evento=event.id_evento,
                    message=(
                        "O código do sistema não foi resolvido de forma "
                        "única e válida no evento."
                    ),
                ),
                None,
            )

        system_code = field.serialized_value
        result = self._validate_code_reference(
            code=code,
            description=description,
            base_column="codSistemaOrigem",
            reference_column=SOURCE_SYSTEM_CODE_COLUMN,
            value=system_code,
            table=table,
            row_numbers=event.row_numbers,
            id_evento=event.id_evento,
            accounting_row_number=None,
        )
        return result, system_code

    def _validate_account_usage(
        self,
        *,
        event: GroupedEvent,
        accounting_row: int,
        account_code: str | None,
        field_name: str,
        rule_code: str,
        table: ReferenceTableData,
    ) -> tuple[ReferenceTableRuleResult, str | None]:
        description = (
            "Verificar se a conta interna da contabilização consta na "
            "tabela de subtítulos internos."
        )

        if account_code is None:
            return (
                ReferenceTableRuleResult(
                    code=rule_code,
                    description=description,
                    source="Crítica de pré-processamento",
                    severity=SEVERITY_INFORMATION,
                    status=RuleExecutionStatus.NOT_APPLICABLE,
                    sheet_name=SHEET_BASE,
                    row_numbers=(accounting_row,),
                    columns=(field_name,),
                    message=(
                        f"{field_name} não foi informado nesta "
                        "contabilização."
                    ),
                    id_evento=event.id_evento,
                    accounting_row_number=accounting_row,
                ),
                None,
            )

        result = self._validate_code_reference(
            code=rule_code,
            description=description,
            base_column=field_name,
            reference_column=INTERNAL_ACCOUNT_CODE_COLUMN,
            value=account_code,
            table=table,
            row_numbers=(accounting_row,),
            id_evento=event.id_evento,
            accounting_row_number=accounting_row,
        )
        return result, account_code

    def _validate_code_reference(
        self,
        *,
        code: str,
        description: str,
        base_column: str,
        reference_column: str,
        value: str,
        table: ReferenceTableData,
        row_numbers: tuple[int, ...],
        id_evento: str,
        accounting_row_number: int | None,
    ) -> ReferenceTableRuleResult:
        if table.missing_columns or table.row_count == 0:
            return self._not_executed(
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                sheet_name=SHEET_BASE,
                row_numbers=row_numbers,
                columns=(base_column, reference_column),
                id_evento=id_evento,
                accounting_row_number=accounting_row_number,
                message=(
                    f"A tabela {table.sheet_name!r} não está disponível "
                    "com estrutura suficiente para a conferência."
                ),
                values=(("codigoUtilizado", value),),
            )

        matching_records = table.code_index.get(value, ())

        if not matching_records:
            return ReferenceTableRuleResult(
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                severity=SEVERITY_ERROR,
                status=RuleExecutionStatus.FAILED,
                sheet_name=SHEET_BASE,
                row_numbers=row_numbers,
                columns=(base_column, reference_column),
                message=(
                    f"O código {value!r} não foi encontrado em "
                    f"{table.sheet_name}.{reference_column}."
                ),
                suggestion=(
                    "Cadastrar o código real na tabela ou corrigir a "
                    "referência da Base."
                ),
                id_evento=id_evento,
                accounting_row_number=accounting_row_number,
                values=(("codigoUtilizado", value),),
            )

        if (
            len(matching_records) != 1
            or not matching_records[0].is_valid
        ):
            return self._not_executed(
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                sheet_name=SHEET_BASE,
                row_numbers=row_numbers,
                columns=(base_column, reference_column),
                id_evento=id_evento,
                accounting_row_number=accounting_row_number,
                message=(
                    f"O código {value!r} existe na tabela, mas seu cadastro "
                    "é duplicado ou possui campo inválido."
                ),
                values=(
                    ("codigoUtilizado", value),
                    (
                        "linhasCadastro",
                        tuple(
                            record.row_number
                            for record in matching_records
                        ),
                    ),
                ),
            )

        record = matching_records[0]
        return ReferenceTableRuleResult(
            code=code,
            description=description,
            source="Crítica de pré-processamento",
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.PASSED,
            sheet_name=SHEET_BASE,
            row_numbers=row_numbers,
            columns=(base_column, reference_column),
            message=(
                f"O código {value!r} foi encontrado em "
                f"{table.sheet_name}, linha {record.row_number}."
            ),
            id_evento=id_evento,
            accounting_row_number=accounting_row_number,
            values=(
                ("codigoUtilizado", value),
                ("nomeCadastrado", record.name),
                ("linhaCadastro", record.row_number),
            ),
        )

    @staticmethod
    def _unused_codes_result(
        *,
        table: ReferenceTableData,
        code: str,
        unused_codes: tuple[str, ...],
    ) -> ReferenceTableRuleResult:
        if unused_codes:
            message = (
                "A tabela possui códigos válidos não utilizados pelos "
                "eventos deste arquivo. Isso é apenas informativo."
            )
        else:
            message = (
                "Todos os códigos válidos e únicos da tabela são utilizados "
                "neste arquivo."
            )

        return ReferenceTableRuleResult(
            code=code,
            description=(
                "Identificar cadastros não utilizados no documento atual."
            ),
            source="Informação diagnóstica",
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.PASSED,
            sheet_name=table.sheet_name,
            row_numbers=(),
            columns=(table.code_column,),
            message=message,
            values=(("codigosNaoUtilizados", unused_codes),),
        )

    @staticmethod
    def _not_executed(
        *,
        code: str,
        description: str,
        source: str,
        sheet_name: str,
        row_numbers: tuple[int, ...],
        columns: tuple[str, ...],
        id_evento: str | None,
        message: str,
        accounting_row_number: int | None = None,
        values: tuple[tuple[str, object], ...] = (),
    ) -> ReferenceTableRuleResult:
        return ReferenceTableRuleResult(
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_NOT_EXECUTED,
            status=RuleExecutionStatus.NOT_EXECUTED,
            sheet_name=sheet_name,
            row_numbers=row_numbers,
            columns=columns,
            message=message,
            id_evento=id_evento,
            accounting_row_number=accounting_row_number,
            values=values,
        )


def validate_reference_tables(
    read_result: ReferenceTablesReadResult,
    grouping: EventGroupingResult,
) -> ReferenceTablesValidationResult:
    """Atalho funcional para a validação das referências."""

    return ReferenceTablesValidator().validate(
        read_result,
        grouping,
    )
