"""Leitura e validação inicial da aba ``Cabecalho``.

Esta etapa valida somente aspectos estruturais e determinísticos:

- presença das colunas obrigatórias;
- existência de exatamente uma linha de dados;
- presença física dos valores obrigatórios;
- uso do código fixo oficial ``5050``;
- impossibilidade de resolver fórmulas no cabeçalho;
- identificação de colunas adicionais.

Formatos, domínios e regras regulatórias completas serão tratados por
normalizadores e validadores próprios em etapas posteriores.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from src.config import (
    DOCUMENT_CODE,
    HEADER_DOCUMENT_CODE_COLUMN,
    RECOGNIZED_HEADER_COLUMNS,
    REQUIRED_HEADER_COLUMNS,
    SHEET_HEADER,
)
from src.readers.excel_reader import (
    ExcelReadResult,
    RawCell,
    RawRow,
    RawSheet,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"


class HeaderReaderError(Exception):
    """Erro estrutural que impede a leitura do cabeçalho."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def __str__(self) -> str:
        return f"{self.code} — {self.message}"


@dataclass(frozen=True, slots=True)
class HeaderFieldValue:
    """Valor de um campo do cabeçalho antes da normalização."""

    field_name: str
    raw_value: Any
    resolved_value: Any
    coordinate: str | None
    is_formula: bool
    source: str

    @property
    def was_filled_by_fixed_rule(self) -> bool:
        """Indica se o valor veio da regra fixa oficial."""

        return self.source == "FIXED_OFFICIAL"


@dataclass(frozen=True, slots=True)
class HeaderData:
    """Cabeçalho bruto extraído de uma única linha do Excel."""

    sheet_name: str
    row_number: int
    fields: Mapping[str, HeaderFieldValue]
    extra_columns: tuple[str, ...]

    def get_field(self, field_name: str) -> HeaderFieldValue:
        """Retorna os metadados de um campo reconhecido."""

        try:
            return self.fields[field_name]
        except KeyError as error:
            raise KeyError(
                f"Campo de cabeçalho não encontrado: {field_name}"
            ) from error

    def get_value(
        self,
        field_name: str,
        default: Any = None,
    ) -> Any:
        """Retorna o valor resolvido do campo."""

        field = self.fields.get(field_name)
        return default if field is None else field.resolved_value

    @property
    def document_code(self) -> str:
        """Retorna o código fixo ou o valor confirmado no Excel."""

        return str(
            self.get_value(HEADER_DOCUMENT_CODE_COLUMN)
        )


@dataclass(frozen=True, slots=True)
class HeaderValidationIssue:
    """Ocorrência encontrada na validação inicial."""

    code: str
    severity: str
    message: str
    field_name: str | None = None
    coordinate: str | None = None
    raw_value: Any = None

    @property
    def blocks_processing(self) -> bool:
        """Indica se a ocorrência impede a continuidade."""

        return self.severity == SEVERITY_BLOCKING_ERROR


@dataclass(frozen=True, slots=True)
class HeaderValidationResult:
    """Resultado completo da validação inicial."""

    issues: tuple[HeaderValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Verdadeiro quando não existem erros impeditivos."""

        return not any(
            issue.blocks_processing
            for issue in self.issues
        )

    @property
    def blocking_errors(
        self,
    ) -> tuple[HeaderValidationIssue, ...]:
        """Retorna somente os erros impeditivos."""

        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_processing
        )

    @property
    def warnings(
        self,
    ) -> tuple[HeaderValidationIssue, ...]:
        """Retorna somente os avisos."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == SEVERITY_WARNING
        )

    @property
    def information(
        self,
    ) -> tuple[HeaderValidationIssue, ...]:
        """Retorna somente as informações."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == SEVERITY_INFORMATION
        )


class HeaderSheetReader:
    """Extrai uma única linha da aba ``Cabecalho``."""

    def read(
        self,
        excel_result: ExcelReadResult,
    ) -> HeaderData:
        """Lê a aba já carregada pelo leitor principal."""

        sheet = excel_result.get_sheet(SHEET_HEADER)
        self._validate_columns(sheet)
        row = self._get_single_data_row(sheet)

        fields = self._build_fields(
            sheet=sheet,
            row=row,
        )

        extra_columns = tuple(
            header
            for header in sheet.headers
            if header not in RECOGNIZED_HEADER_COLUMNS
        )

        return HeaderData(
            sheet_name=sheet.name,
            row_number=row.row_number,
            fields=MappingProxyType(fields),
            extra_columns=extra_columns,
        )

    @staticmethod
    def _validate_columns(sheet: RawSheet) -> None:
        """Confirma as colunas mínimas do cabeçalho."""

        missing_columns = tuple(
            column
            for column in REQUIRED_HEADER_COLUMNS
            if column not in sheet.headers
        )

        if missing_columns:
            raise HeaderReaderError(
                "XLSX-CAB-001",
                (
                    "A aba Cabecalho não contém todas as "
                    "colunas obrigatórias."
                ),
                details={
                    "aba": sheet.name,
                    "colunas_ausentes": missing_columns,
                    "colunas_encontradas": sheet.headers,
                },
            )

    @staticmethod
    def _get_single_data_row(sheet: RawSheet) -> RawRow:
        """Exige exatamente uma linha não vazia de cabeçalho."""

        if sheet.row_count == 0:
            raise HeaderReaderError(
                "XLSX-CAB-002",
                "A aba Cabecalho não possui linha de dados.",
                details={"aba": sheet.name},
            )

        if sheet.row_count > 1:
            raise HeaderReaderError(
                "XLSX-CAB-003",
                (
                    "A aba Cabecalho possui mais de uma linha "
                    "de dados."
                ),
                details={
                    "aba": sheet.name,
                    "linhas": tuple(
                        row.row_number
                        for row in sheet.rows
                    ),
                },
            )

        return sheet.rows[0]

    @staticmethod
    def _build_fields(
        *,
        sheet: RawSheet,
        row: RawRow,
    ) -> dict[str, HeaderFieldValue]:
        """Cria os campos reconhecidos e aplica o código fixo."""

        fields: dict[str, HeaderFieldValue] = {}

        for field_name in RECOGNIZED_HEADER_COLUMNS:
            if field_name == HEADER_DOCUMENT_CODE_COLUMN:
                fields[field_name] = (
                    HeaderSheetReader
                    ._build_document_code_field(
                        sheet=sheet,
                        row=row,
                    )
                )
                continue

            raw_cell = row.get_cell(field_name)
            fields[field_name] = HeaderFieldValue(
                field_name=field_name,
                raw_value=raw_cell.value,
                resolved_value=raw_cell.value,
                coordinate=raw_cell.coordinate,
                is_formula=raw_cell.is_formula,
                source="EXCEL",
            )

        return fields

    @staticmethod
    def _build_document_code_field(
        *,
        sheet: RawSheet,
        row: RawRow,
    ) -> HeaderFieldValue:
        """Usa o valor fixo quando a coluna ou célula não existe."""

        if (
            HEADER_DOCUMENT_CODE_COLUMN
            not in sheet.headers
        ):
            return HeaderFieldValue(
                field_name=HEADER_DOCUMENT_CODE_COLUMN,
                raw_value=None,
                resolved_value=DOCUMENT_CODE,
                coordinate=None,
                is_formula=False,
                source="FIXED_OFFICIAL",
            )

        raw_cell = row.get_cell(
            HEADER_DOCUMENT_CODE_COLUMN
        )

        if _is_physically_empty(raw_cell.value):
            return HeaderFieldValue(
                field_name=HEADER_DOCUMENT_CODE_COLUMN,
                raw_value=raw_cell.value,
                resolved_value=DOCUMENT_CODE,
                coordinate=raw_cell.coordinate,
                is_formula=raw_cell.is_formula,
                source="FIXED_OFFICIAL",
            )

        return HeaderFieldValue(
            field_name=HEADER_DOCUMENT_CODE_COLUMN,
            raw_value=raw_cell.value,
            resolved_value=raw_cell.value,
            coordinate=raw_cell.coordinate,
            is_formula=raw_cell.is_formula,
            source="EXCEL",
        )


class HeaderInitialValidator:
    """Executa validações iniciais e não regulatórias completas."""

    def validate(
        self,
        header: HeaderData,
    ) -> HeaderValidationResult:
        """Retorna todas as ocorrências iniciais do cabeçalho."""

        issues: list[HeaderValidationIssue] = []

        issues.extend(
            self._validate_required_values(header)
        )
        issues.extend(
            self._validate_formulas(header)
        )
        issues.extend(
            self._validate_document_code(header)
        )
        issues.extend(
            self._describe_extra_columns(header)
        )

        return HeaderValidationResult(
            issues=tuple(issues)
        )

    @staticmethod
    def _validate_required_values(
        header: HeaderData,
    ) -> list[HeaderValidationIssue]:
        """Verifica apenas ausência física nas colunas obrigatórias."""

        issues: list[HeaderValidationIssue] = []

        for field_name in REQUIRED_HEADER_COLUMNS:
            field = header.get_field(field_name)

            if _is_physically_empty(field.raw_value):
                issues.append(
                    HeaderValidationIssue(
                        code="CAB-VAL-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Campo obrigatório do cabeçalho "
                            "sem valor físico."
                        ),
                        field_name=field_name,
                        coordinate=field.coordinate,
                        raw_value=field.raw_value,
                    )
                )

        return issues

    @staticmethod
    def _validate_formulas(
        header: HeaderData,
    ) -> list[HeaderValidationIssue]:
        """Rejeita fórmulas porque o openpyxl não as calcula."""

        issues: list[HeaderValidationIssue] = []

        for field in header.fields.values():
            if not field.is_formula:
                continue

            issues.append(
                HeaderValidationIssue(
                    code="CAB-VAL-002",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O cabeçalho contém fórmula. O leitor "
                        "preserva a fórmula, mas não calcula o "
                        "resultado com segurança."
                    ),
                    field_name=field.field_name,
                    coordinate=field.coordinate,
                    raw_value=field.raw_value,
                )
            )

        return issues

    @staticmethod
    def _validate_document_code(
        header: HeaderData,
    ) -> list[HeaderValidationIssue]:
        """Confirma o código fixo oficial do documento."""

        field = header.get_field(
            HEADER_DOCUMENT_CODE_COLUMN
        )

        if field.was_filled_by_fixed_rule:
            return [
                HeaderValidationIssue(
                    code="CAB-INFO-001",
                    severity=SEVERITY_INFORMATION,
                    message=(
                        "codigoDocumento preenchido pela regra "
                        "fixa oficial com o valor 5050."
                    ),
                    field_name=field.field_name,
                    coordinate=field.coordinate,
                    raw_value=field.raw_value,
                )
            ]

        if field.is_formula:
            return []

        raw_text = str(field.raw_value).strip()

        if raw_text != DOCUMENT_CODE:
            return [
                HeaderValidationIssue(
                    code="CAB-VAL-003",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "codigoDocumento diferente do valor "
                        "fixo oficial 5050."
                    ),
                    field_name=field.field_name,
                    coordinate=field.coordinate,
                    raw_value=field.raw_value,
                )
            ]

        return []

    @staticmethod
    def _describe_extra_columns(
        header: HeaderData,
    ) -> list[HeaderValidationIssue]:
        """Registra colunas extras sem impedir a leitura."""

        if not header.extra_columns:
            return []

        return [
            HeaderValidationIssue(
                code="CAB-INFO-002",
                severity=SEVERITY_INFORMATION,
                message=(
                    "A aba Cabecalho possui colunas adicionais "
                    "que serão preservadas como metadado, mas "
                    "não serão usadas nesta etapa."
                ),
                raw_value=header.extra_columns,
            )
        ]


def _is_physically_empty(value: Any) -> bool:
    """Identifica somente ausência física, sem normalizar nulos."""

    if value is None:
        return True

    return isinstance(value, str) and not value.strip()


def read_header(
    excel_result: ExcelReadResult,
) -> HeaderData:
    """Atalho funcional para leitura da aba Cabecalho."""

    return HeaderSheetReader().read(excel_result)


def validate_header_initial(
    header: HeaderData,
) -> HeaderValidationResult:
    """Atalho funcional para a validação inicial."""

    return HeaderInitialValidator().validate(header)
