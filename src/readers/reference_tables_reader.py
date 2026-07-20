"""Leitura e normalização das tabelas auxiliares do Documento 5050."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from src.config import (
    BASE_CREDIT_ACCOUNT_NAME_COLUMN,
    BASE_DEBIT_ACCOUNT_NAME_COLUMN,
    BASE_SOURCE_SYSTEM_NAME_COLUMN,
    INTERNAL_ACCOUNT_CODE_COLUMN,
    INTERNAL_ACCOUNT_NAME_COLUMN,
    REQUIRED_INTERNAL_ACCOUNT_COLUMNS,
    REQUIRED_SOURCE_SYSTEM_COLUMNS,
    SHEET_BASE,
    SHEET_INTERNAL_ACCOUNTS,
    SHEET_SOURCE_SYSTEMS,
    SOURCE_SYSTEM_CODE_COLUMN,
    SOURCE_SYSTEM_NAME_COLUMN,
)
from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
)
from src.domain.reference_tables import (
    ReferenceTableData,
    ReferenceTableKind,
    ReferenceTableRecord,
    ReferenceTableRuleResult,
    ReferenceTablesReadResult,
)
from src.normalizers.identifier_normalizer import (
    normalize_internal_account_code,
    normalize_source_system_code,
)
from src.normalizers.reference_table_normalizer import (
    normalize_reference_name,
)
from src.readers.excel_reader import (
    ExcelReadResult,
    RawCell,
    RawSheet,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_ERROR = "ERRO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"


class ReferenceTablesReader:
    """Lê referências em abas próprias ou embutidas na ``Base``."""

    def read(
        self,
        excel_result: ExcelReadResult,
    ) -> ReferenceTablesReadResult:
        if (
            SHEET_SOURCE_SYSTEMS not in excel_result.sheets
            and SHEET_INTERNAL_ACCOUNTS not in excel_result.sheets
        ):
            return self._read_embedded(
                excel_result.get_sheet(SHEET_BASE)
            )

        return self._read_separate_sheets(excel_result)

    def _read_separate_sheets(
        self,
        excel_result: ExcelReadResult,
    ) -> ReferenceTablesReadResult:
        systems = self._read_table(
            sheet=excel_result.get_sheet(SHEET_SOURCE_SYSTEMS),
            kind=ReferenceTableKind.SOURCE_SYSTEM,
            required_columns=REQUIRED_SOURCE_SYSTEM_COLUMNS,
            code_column=SOURCE_SYSTEM_CODE_COLUMN,
            name_column=SOURCE_SYSTEM_NAME_COLUMN,
            code_normalizer=normalize_source_system_code,
            uniqueness_code="DRO001102",
            empty_code="TBL-SIS-EST-002",
            missing_column_code="TBL-SIS-EST-001",
            code_field_rule="TBL-SIS-COD-001",
            name_field_rule="TBL-SIS-NOME-001",
        )
        accounts = self._read_table(
            sheet=excel_result.get_sheet(SHEET_INTERNAL_ACCOUNTS),
            kind=ReferenceTableKind.INTERNAL_ACCOUNT,
            required_columns=REQUIRED_INTERNAL_ACCOUNT_COLUMNS,
            code_column=INTERNAL_ACCOUNT_CODE_COLUMN,
            name_column=INTERNAL_ACCOUNT_NAME_COLUMN,
            code_normalizer=normalize_internal_account_code,
            uniqueness_code="DRO001101",
            empty_code="TBL-CONTA-EST-002",
            missing_column_code="TBL-CONTA-EST-001",
            code_field_rule="TBL-CONTA-COD-001",
            name_field_rule="TBL-CONTA-NOME-001",
        )

        return ReferenceTablesReadResult(
            systems=systems,
            accounts=accounts,
        )

    def _read_embedded(
        self,
        sheet: RawSheet,
    ) -> ReferenceTablesReadResult:
        systems = self._read_embedded_table(
            sheet=sheet,
            kind=ReferenceTableKind.SOURCE_SYSTEM,
            field_pairs=((
                "codSistemaOrigem",
                BASE_SOURCE_SYSTEM_NAME_COLUMN,
            ),),
            code_normalizer=normalize_source_system_code,
            uniqueness_code="DRO001102",
            empty_code="TBL-SIS-EST-002",
            missing_column_code="TBL-SIS-EST-001",
            code_field_rule="TBL-SIS-COD-001",
            name_field_rule="TBL-SIS-NOME-001",
            skip_empty_pairs=False,
        )
        accounts = self._read_embedded_table(
            sheet=sheet,
            kind=ReferenceTableKind.INTERNAL_ACCOUNT,
            field_pairs=(
                (
                    "contaBalAnaliticoDebito",
                    BASE_DEBIT_ACCOUNT_NAME_COLUMN,
                ),
                (
                    "contaBalAnaliticoCredito",
                    BASE_CREDIT_ACCOUNT_NAME_COLUMN,
                ),
            ),
            code_normalizer=normalize_internal_account_code,
            uniqueness_code="DRO001101",
            empty_code="TBL-CONTA-EST-002",
            missing_column_code="TBL-CONTA-EST-001",
            code_field_rule="TBL-CONTA-COD-001",
            name_field_rule="TBL-CONTA-NOME-001",
            skip_empty_pairs=True,
        )
        return ReferenceTablesReadResult(
            systems=systems,
            accounts=accounts,
        )

    def _read_embedded_table(
        self,
        *,
        sheet: RawSheet,
        kind: ReferenceTableKind,
        field_pairs: tuple[tuple[str, str], ...],
        code_normalizer: Callable[
            [object],
            NormalizationResult[str],
        ],
        uniqueness_code: str,
        empty_code: str,
        missing_column_code: str,
        code_field_rule: str,
        name_field_rule: str,
        skip_empty_pairs: bool,
    ) -> ReferenceTableData:
        required_columns = tuple(
            column
            for pair in field_pairs
            for column in pair
        )
        missing_columns = tuple(
            column
            for column in required_columns
            if column not in sheet.headers
        )
        results: list[ReferenceTableRuleResult] = []

        for column in missing_columns:
            results.append(
                self._failed(
                    code=missing_column_code,
                    description=(
                        "Exigir as colunas das referências embutidas."
                    ),
                    source="Contrato da aba Base",
                    severity=SEVERITY_BLOCKING_ERROR,
                    sheet_name=sheet.name,
                    row_numbers=(1,),
                    columns=(column,),
                    message=(
                        f"A coluna obrigatória {column!r} não foi "
                        "encontrada na aba Base."
                    ),
                    suggestion=(
                        f"Criar a coluna {column!r} com o nome exato."
                    ),
                )
            )

        records: list[ReferenceTableRecord] = []
        record_keys: set[tuple[object, ...]] = set()

        for row in sheet.rows:
            for code_column, name_column in field_pairs:
                code_result = self._normalize_cell(
                    cell=self._cell_or_none(
                        row.cells,
                        code_column,
                    ),
                    missing_column=(
                        code_column in missing_columns
                    ),
                    normalizer=code_normalizer,
                    field_label=code_column,
                )
                name_result = self._normalize_cell(
                    cell=self._cell_or_none(
                        row.cells,
                        name_column,
                    ),
                    missing_column=(
                        name_column in missing_columns
                    ),
                    normalizer=lambda value, column=name_column: (
                        normalize_reference_name(
                            value,
                            field_label=column,
                        )
                    ),
                    field_label=name_column,
                )

                if (
                    skip_empty_pairs
                    and code_result.is_absent
                    and name_result.is_absent
                ):
                    continue

                record_key: tuple[object, ...] = (
                    code_result.status,
                    code_result.serialized_value,
                    name_result.status,
                    name_result.serialized_value,
                )
                if not (
                    code_result.is_valid
                    and name_result.is_valid
                ):
                    record_key += (
                        repr(code_result.original_value),
                        repr(name_result.original_value),
                    )
                if record_key in record_keys:
                    continue
                record_keys.add(record_key)

                record = ReferenceTableRecord(
                    kind=kind,
                    sheet_name=sheet.name,
                    row_number=row.row_number,
                    code_column=code_column,
                    name_column=name_column,
                    code_result=code_result,
                    name_result=name_result,
                )
                records.append(record)

                if not code_result.is_valid:
                    results.append(
                        self._field_failure(
                            code=code_field_rule,
                            sheet_name=sheet.name,
                            row_number=row.row_number,
                            column=code_column,
                            result=code_result,
                        )
                    )
                if not name_result.is_valid:
                    results.append(
                        self._field_failure(
                            code=name_field_rule,
                            sheet_name=sheet.name,
                            row_number=row.row_number,
                            column=name_column,
                            result=name_result,
                        )
                    )

        if not records:
            results.append(
                self._failed(
                    code=empty_code,
                    description=(
                        "Exigir ao menos uma referência utilizada."
                    ),
                    source="XSD",
                    severity=SEVERITY_BLOCKING_ERROR,
                    sheet_name=sheet.name,
                    row_numbers=(),
                    columns=required_columns,
                    message=(
                        "A aba Base não contém referências válidas "
                        f"de {kind.value.lower()}."
                    ),
                )
            )

        conceptual_code_column = (
            SOURCE_SYSTEM_CODE_COLUMN
            if kind == ReferenceTableKind.SOURCE_SYSTEM
            else INTERNAL_ACCOUNT_CODE_COLUMN
        )
        conceptual_name_column = (
            SOURCE_SYSTEM_NAME_COLUMN
            if kind == ReferenceTableKind.SOURCE_SYSTEM
            else INTERNAL_ACCOUNT_NAME_COLUMN
        )
        results.append(
            self._validate_uniqueness(
                kind=kind,
                sheet_name=sheet.name,
                records=tuple(records),
                code_column=conceptual_code_column,
                uniqueness_code=uniqueness_code,
                columns=tuple(
                    code_column
                    for code_column, _ in field_pairs
                ),
            )
        )

        return ReferenceTableData(
            kind=kind,
            sheet_name=sheet.name,
            code_column=conceptual_code_column,
            name_column=conceptual_name_column,
            actual_columns=required_columns,
            missing_columns=missing_columns,
            extra_columns=(),
            records=tuple(records),
            rule_results=tuple(results),
        )

    def _read_table(
        self,
        *,
        sheet: RawSheet,
        kind: ReferenceTableKind,
        required_columns: tuple[str, ...],
        code_column: str,
        name_column: str,
        code_normalizer: Callable[
            [object],
            NormalizationResult[str],
        ],
        uniqueness_code: str,
        empty_code: str,
        missing_column_code: str,
        code_field_rule: str,
        name_field_rule: str,
    ) -> ReferenceTableData:
        missing_columns = tuple(
            column
            for column in required_columns
            if column not in sheet.headers
        )
        extra_columns = tuple(
            column
            for column in sheet.headers
            if column not in required_columns
        )
        results: list[ReferenceTableRuleResult] = []

        for column in missing_columns:
            results.append(
                self._failed(
                    code=missing_column_code,
                    description=(
                        "Exigir as colunas estruturais da tabela auxiliar."
                    ),
                    source="XSD e contrato da planilha",
                    severity=SEVERITY_BLOCKING_ERROR,
                    sheet_name=sheet.name,
                    row_numbers=(1,),
                    columns=(column,),
                    message=(
                        f"A coluna obrigatória {column!r} não foi encontrada."
                    ),
                    suggestion=(
                        f"Criar a coluna {column!r} com o nome exato."
                    ),
                )
            )

        if extra_columns:
            results.append(
                self._passed_or_warning(
                    code="TBL-EST-EXTRA-001",
                    description=(
                        "Identificar colunas adicionais sem mapeamento."
                    ),
                    source="Contrato da planilha",
                    severity=SEVERITY_WARNING,
                    status=RuleExecutionStatus.FAILED,
                    sheet_name=sheet.name,
                    row_numbers=(1,),
                    columns=extra_columns,
                    message=(
                        "A tabela possui colunas adicionais. Elas não serão "
                        "enviadas ao XML."
                    ),
                    values=(("colunasExtras", extra_columns),),
                )
            )

        if sheet.row_count == 0:
            results.append(
                self._failed(
                    code=empty_code,
                    description=(
                        "Exigir ao menos um registro na tabela auxiliar."
                    ),
                    source="XSD",
                    severity=SEVERITY_BLOCKING_ERROR,
                    sheet_name=sheet.name,
                    row_numbers=(),
                    columns=required_columns,
                    message=(
                        "A tabela não possui registros. O XSD exige ao "
                        "menos um elemento."
                    ),
                )
            )

        records: list[ReferenceTableRecord] = []

        for row in sheet.rows:
            code_cell = self._cell_or_none(row.cells, code_column)
            name_cell = self._cell_or_none(row.cells, name_column)

            code_result = self._normalize_cell(
                cell=code_cell,
                missing_column=code_column in missing_columns,
                normalizer=code_normalizer,
                field_label=code_column,
            )
            name_result = self._normalize_cell(
                cell=name_cell,
                missing_column=name_column in missing_columns,
                normalizer=lambda value: normalize_reference_name(
                    value,
                    field_label=name_column,
                ),
                field_label=name_column,
            )

            record = ReferenceTableRecord(
                kind=kind,
                sheet_name=sheet.name,
                row_number=row.row_number,
                code_column=code_column,
                name_column=name_column,
                code_result=code_result,
                name_result=name_result,
            )
            records.append(record)

            if not code_result.is_valid:
                results.append(
                    self._field_failure(
                        code=code_field_rule,
                        sheet_name=sheet.name,
                        row_number=row.row_number,
                        column=code_column,
                        result=code_result,
                    )
                )

            if not name_result.is_valid:
                results.append(
                    self._field_failure(
                        code=name_field_rule,
                        sheet_name=sheet.name,
                        row_number=row.row_number,
                        column=name_column,
                        result=name_result,
                    )
                )

        results.append(
            self._validate_uniqueness(
                kind=kind,
                sheet_name=sheet.name,
                records=tuple(records),
                code_column=code_column,
                uniqueness_code=uniqueness_code,
            )
        )

        return ReferenceTableData(
            kind=kind,
            sheet_name=sheet.name,
            code_column=code_column,
            name_column=name_column,
            actual_columns=sheet.headers,
            missing_columns=missing_columns,
            extra_columns=extra_columns,
            records=tuple(records),
            rule_results=tuple(results),
        )

    @staticmethod
    def _cell_or_none(
        cells: object,
        column_name: str,
    ) -> RawCell | None:
        if hasattr(cells, "get"):
            return cells.get(column_name)  # type: ignore[no-any-return]
        return None

    @staticmethod
    def _normalize_cell(
        *,
        cell: RawCell | None,
        missing_column: bool,
        normalizer: Callable[
            [object],
            NormalizationResult[str],
        ],
        field_label: str,
    ) -> NormalizationResult[str]:
        if missing_column or cell is None:
            return absent_result(
                original_value=None,
                rule_code="NORM-TABELA-COLUNA-AUSENTE-001",
                issue_code="TBL-COLUNA-AUSENTE-001",
                issue_message=(
                    f"A coluna {field_label!r} não está disponível."
                ),
            )

        if cell.is_formula:
            return invalid_result(
                original_value=cell.value,
                rule_code="NORM-FORMULA-001",
                issue_code="TBL-FORMULA-001",
                issue_message=(
                    "Fórmula encontrada. O openpyxl não calcula o valor "
                    "com segurança."
                ),
            )

        return normalizer(cell.value)

    def _validate_uniqueness(
        self,
        *,
        kind: ReferenceTableKind,
        sheet_name: str,
        records: tuple[ReferenceTableRecord, ...],
        code_column: str,
        uniqueness_code: str,
        columns: tuple[str, ...] | None = None,
    ) -> ReferenceTableRuleResult:
        description = (
            "Verificar a unicidade dos códigos da tabela auxiliar."
        )
        result_columns = columns or (code_column,)
        valid_codes: dict[str, list[ReferenceTableRecord]] = defaultdict(list)
        invalid_code_rows: list[int] = []

        for record in records:
            if record.code_result.is_valid and record.code is not None:
                valid_codes[record.code].append(record)
            else:
                invalid_code_rows.append(record.row_number)

        duplicates = {
            code: tuple(item.row_number for item in code_records)
            for code, code_records in valid_codes.items()
            if len(code_records) > 1
        }

        if duplicates:
            duplicate_rows = tuple(
                sorted(
                    row
                    for rows in duplicates.values()
                    for row in rows
                )
            )
            return self._failed(
                code=uniqueness_code,
                description=description,
                source="Crítica de pré-processamento",
                severity=SEVERITY_ERROR,
                sheet_name=sheet_name,
                row_numbers=duplicate_rows,
                columns=result_columns,
                message=(
                    "Foram encontrados códigos repetidos. A aplicação não "
                    "escolherá um registro arbitrariamente."
                ),
                suggestion=(
                    "Manter somente um registro para cada código e revisar "
                    "o nome correspondente."
                ),
                values=tuple(duplicates.items()),
            )

        if invalid_code_rows or not records:
            return self._passed_or_warning(
                code=uniqueness_code,
                description=description,
                source="Crítica de pré-processamento",
                severity=SEVERITY_NOT_EXECUTED,
                status=RuleExecutionStatus.NOT_EXECUTED,
                sheet_name=sheet_name,
                row_numbers=tuple(invalid_code_rows),
                columns=result_columns,
                message=(
                    "A unicidade não pôde ser concluída porque há códigos "
                    "inválidos, ausentes ou nenhum registro."
                ),
            )

        return self._passed_or_warning(
            code=uniqueness_code,
            description=description,
            source="Crítica de pré-processamento",
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.PASSED,
            sheet_name=sheet_name,
            row_numbers=tuple(record.row_number for record in records),
            columns=result_columns,
            message=(
                f"Os {len(valid_codes)} códigos de {kind.value.lower()} "
                "são únicos."
            ),
        )

    def _field_failure(
        self,
        *,
        code: str,
        sheet_name: str,
        row_number: int,
        column: str,
        result: NormalizationResult[str],
    ) -> ReferenceTableRuleResult:
        return self._failed(
            code=code,
            description=(
                "Validar obrigatoriedade, tipo, formato e tamanho do campo."
            ),
            source="XSD e instruções de preenchimento",
            severity=SEVERITY_ERROR,
            sheet_name=sheet_name,
            row_numbers=(row_number,),
            columns=(column,),
            message=(
                result.issue_message
                or "O campo não pôde ser normalizado."
            ),
            suggestion=(
                "Corrigir o valor sem preencher dados fictícios."
            ),
            values=(
                ("valorOriginal", result.original_value),
                ("valorNormalizado", result.serialized_value),
                ("regraNormalizacao", result.rule_code),
            ),
        )

    @staticmethod
    def _failed(
        *,
        code: str,
        description: str,
        source: str,
        severity: str,
        sheet_name: str,
        row_numbers: tuple[int, ...],
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
        values: tuple[tuple[str, object], ...] = (),
    ) -> ReferenceTableRuleResult:
        return ReferenceTableRuleResult(
            code=code,
            description=description,
            source=source,
            severity=severity,
            status=RuleExecutionStatus.FAILED,
            sheet_name=sheet_name,
            row_numbers=row_numbers,
            columns=columns,
            message=message,
            suggestion=suggestion,
            values=values,
        )

    @staticmethod
    def _passed_or_warning(
        *,
        code: str,
        description: str,
        source: str,
        severity: str,
        status: RuleExecutionStatus,
        sheet_name: str,
        row_numbers: tuple[int, ...],
        columns: tuple[str, ...],
        message: str,
        values: tuple[tuple[str, object], ...] = (),
    ) -> ReferenceTableRuleResult:
        return ReferenceTableRuleResult(
            code=code,
            description=description,
            source=source,
            severity=severity,
            status=status,
            sheet_name=sheet_name,
            row_numbers=row_numbers,
            columns=columns,
            message=message,
            values=values,
        )


def read_reference_tables(
    excel_result: ExcelReadResult,
) -> ReferenceTablesReadResult:
    """Atalho funcional para o leitor das tabelas auxiliares."""

    return ReferenceTablesReader().read(excel_result)
