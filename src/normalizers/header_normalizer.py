"""Normalização e validação local dos campos da aba ``Cabecalho``.

Regras implementadas:

- ``codigoDocumento`` deve resultar em ``5050``;
- ``dataBase`` deve resultar em ``AAAA-06`` ou ``AAAA-12``;
- ``dataBase`` não pode ser anterior a ``2020-12``;
- ``codigoConglomerado`` deve seguir ``C`` + 7 dígitos;
- ``cnpj`` aceita a raiz de 8 dígitos ou o CNPJ completo de 14
  dígitos, do qual extrai a raiz;
- ``tipoRemessa`` deve ser ``I`` ou ``S``;
- ``opcaoPorProvisaoAcumulada`` deve ser ``S`` ou ``N``.

As verificações externas de existência no UNICAD não fazem parte desta
etapa e não são simuladas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping

from src.config import (
    DOCUMENT_CODE,
    HEADER_ACCUMULATED_PROVISION_OPTION_COLUMN,
    HEADER_CNPJ_COLUMN,
    HEADER_CONGLOMERATE_CODE_COLUMN,
    HEADER_DATA_BASE_COLUMN,
    HEADER_DOCUMENT_CODE_COLUMN,
    HEADER_SUBMISSION_TYPE_COLUMN,
)
from src.domain.document_header import DocumentHeader
from src.normalizers.null_normalizer import is_null_candidate
from src.readers.header_reader import HeaderData


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_INFORMATION = "INFORMAÇÃO"

MINIMUM_DATA_BASE = (2020, 12)
SEMESTER_MONTHS = frozenset({6, 12})

_CONGLOMERATE_PATTERN = re.compile(r"^C[0-9]{7}$")
_CNPJ_PATTERN = re.compile(r"^[0-9]{8}$")
_FULL_CNPJ_PATTERN = re.compile(r"^[0-9]{14}$")
_YEAR_MONTH_PATTERN = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})$"
)
_MONTH_YEAR_PATTERN = re.compile(
    r"^(?P<month>[0-9]{2})/(?P<year>[0-9]{4})$"
)


@dataclass(frozen=True, slots=True)
class HeaderFieldTransformation:
    """Rastreabilidade de valor original e valor normalizado."""

    field_name: str
    coordinate: str | None
    original_value: Any
    normalized_value: str | None
    rule_code: str
    rule_description: str
    changed: bool


@dataclass(frozen=True, slots=True)
class HeaderNormalizationIssue:
    """Erro ou informação produzido durante a normalização."""

    code: str
    severity: str
    message: str
    field_name: str
    coordinate: str | None
    original_value: Any
    normalized_value: str | None = None

    @property
    def blocks_processing(self) -> bool:
        """Indica se a ocorrência impede criar o cabeçalho normalizado."""

        return self.severity == SEVERITY_BLOCKING_ERROR


@dataclass(frozen=True, slots=True)
class HeaderNormalizationResult:
    """Resultado da normalização completa do cabeçalho."""

    header: DocumentHeader | None
    normalized_values: Mapping[str, str | None]
    transformations: tuple[HeaderFieldTransformation, ...]
    issues: tuple[HeaderNormalizationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Verdadeiro quando o modelo normalizado foi criado."""

        return (
            self.header is not None
            and not any(
                issue.blocks_processing
                for issue in self.issues
            )
        )

    @property
    def blocking_errors(
        self,
    ) -> tuple[HeaderNormalizationIssue, ...]:
        """Retorna somente erros impeditivos."""

        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_processing
        )

    @property
    def information(
        self,
    ) -> tuple[HeaderNormalizationIssue, ...]:
        """Retorna somente ocorrências informativas."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == SEVERITY_INFORMATION
        )


@dataclass(frozen=True, slots=True)
class _FieldNormalization:
    """Resultado interno da normalização de um único campo."""

    normalized_value: str | None
    rule_code: str
    rule_description: str
    issue_code: str | None = None
    issue_message: str | None = None


class HeaderNormalizer:
    """Normaliza e valida os campos conhecidos do cabeçalho."""

    def normalize(
        self,
        header_data: HeaderData,
    ) -> HeaderNormalizationResult:
        """Executa todas as regras locais da etapa 3.3."""

        normalized_values: dict[str, str | None] = {}
        transformations: list[HeaderFieldTransformation] = []
        issues: list[HeaderNormalizationIssue] = []

        rules: tuple[
            tuple[
                str,
                Callable[[Any], _FieldNormalization],
            ],
            ...,
        ] = (
            (
                HEADER_DOCUMENT_CODE_COLUMN,
                self._normalize_document_code,
            ),
            (
                HEADER_DATA_BASE_COLUMN,
                self._normalize_data_base,
            ),
            (
                HEADER_CONGLOMERATE_CODE_COLUMN,
                self._normalize_conglomerate_code,
            ),
            (
                HEADER_CNPJ_COLUMN,
                self._normalize_cnpj,
            ),
            (
                HEADER_SUBMISSION_TYPE_COLUMN,
                self._normalize_submission_type,
            ),
            (
                HEADER_ACCUMULATED_PROVISION_OPTION_COLUMN,
                self._normalize_accumulated_provision_option,
            ),
        )

        for field_name, normalizer in rules:
            field = header_data.get_field(field_name)

            if field.is_formula:
                normalized_values[field_name] = None
                issues.append(
                    HeaderNormalizationIssue(
                        code="CAB-NORM-002",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Não é possível normalizar uma fórmula "
                            "sem resultado calculado confiável."
                        ),
                        field_name=field_name,
                        coordinate=field.coordinate,
                        original_value=field.raw_value,
                    )
                )
                transformations.append(
                    HeaderFieldTransformation(
                        field_name=field_name,
                        coordinate=field.coordinate,
                        original_value=field.raw_value,
                        normalized_value=None,
                        rule_code="NORM-CAB-FORMULA-001",
                        rule_description=(
                            "Fórmula preservada e não calculada."
                        ),
                        changed=False,
                    )
                )
                continue

            source_value = field.resolved_value

            if is_null_candidate(source_value):
                normalized_values[field_name] = None
                issues.append(
                    HeaderNormalizationIssue(
                        code="CAB-NULO-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Campo obrigatório contém valor "
                            "candidato a ausência."
                        ),
                        field_name=field_name,
                        coordinate=field.coordinate,
                        original_value=field.raw_value,
                    )
                )
                transformations.append(
                    HeaderFieldTransformation(
                        field_name=field_name,
                        coordinate=field.coordinate,
                        original_value=field.raw_value,
                        normalized_value=None,
                        rule_code="NORM-NULO-001",
                        rule_description=(
                            "Identificação de candidato a ausência."
                        ),
                        changed=True,
                    )
                )
                continue

            result = normalizer(source_value)
            normalized_values[field_name] = (
                result.normalized_value
            )

            transformations.append(
                HeaderFieldTransformation(
                    field_name=field_name,
                    coordinate=field.coordinate,
                    original_value=field.raw_value,
                    normalized_value=result.normalized_value,
                    rule_code=result.rule_code,
                    rule_description=(
                        result.rule_description
                    ),
                    changed=self._was_changed(
                        original_value=field.raw_value,
                        resolved_value=source_value,
                        normalized_value=(
                            result.normalized_value
                        ),
                        fixed_source=(
                            field.was_filled_by_fixed_rule
                        ),
                    ),
                )
            )

            if result.issue_code is not None:
                issues.append(
                    HeaderNormalizationIssue(
                        code=result.issue_code,
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            result.issue_message
                            or "Valor inválido."
                        ),
                        field_name=field_name,
                        coordinate=field.coordinate,
                        original_value=field.raw_value,
                        normalized_value=(
                            result.normalized_value
                        ),
                    )
                )

        normalized_mapping = MappingProxyType(
            normalized_values
        )

        if any(
            issue.blocks_processing
            for issue in issues
        ):
            normalized_header = None
        else:
            normalized_header = DocumentHeader(
                codigo_documento=self._required_value(
                    normalized_values,
                    HEADER_DOCUMENT_CODE_COLUMN,
                ),
                data_base=self._required_value(
                    normalized_values,
                    HEADER_DATA_BASE_COLUMN,
                ),
                codigo_conglomerado=self._required_value(
                    normalized_values,
                    HEADER_CONGLOMERATE_CODE_COLUMN,
                ),
                cnpj=self._required_value(
                    normalized_values,
                    HEADER_CNPJ_COLUMN,
                ),
                tipo_remessa=self._required_value(
                    normalized_values,
                    HEADER_SUBMISSION_TYPE_COLUMN,
                ),
                opcao_por_provisao_acumulada=(
                    self._required_value(
                        normalized_values,
                        HEADER_ACCUMULATED_PROVISION_OPTION_COLUMN,
                    )
                ),
            )

        return HeaderNormalizationResult(
            header=normalized_header,
            normalized_values=normalized_mapping,
            transformations=tuple(transformations),
            issues=tuple(issues),
        )

    @staticmethod
    def _normalize_document_code(
        value: Any,
    ) -> _FieldNormalization:
        normalized = _scalar_to_text(value)

        if normalized != DOCUMENT_CODE:
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-DOC-001",
                rule_description=(
                    "Conversão textual do código do documento."
                ),
                issue_code="CAB-DOC-001",
                issue_message=(
                    "codigoDocumento deve ser exatamente 5050."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-DOC-001",
            rule_description=(
                "Conversão textual e confirmação do código 5050."
            ),
        )

    @staticmethod
    def _normalize_data_base(
        value: Any,
    ) -> _FieldNormalization:
        parsed = _parse_year_month(value)

        if parsed is None:
            return _FieldNormalization(
                normalized_value=None,
                rule_code="NORM-CAB-DATA-001",
                rule_description=(
                    "Conversão de dataBase para AAAA-MM."
                ),
                issue_code="CAB-DATA-001",
                issue_message=(
                    "dataBase possui formato ou data inválida."
                ),
            )

        year, month = parsed
        normalized = f"{year:04d}-{month:02d}"

        if month not in SEMESTER_MONTHS:
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-DATA-001",
                rule_description=(
                    "Conversão de dataBase para AAAA-MM."
                ),
                issue_code="CAB-DATA-002",
                issue_message=(
                    "O mês da dataBase deve ser 06 ou 12."
                ),
            )

        if (year, month) < MINIMUM_DATA_BASE:
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-DATA-001",
                rule_description=(
                    "Conversão de dataBase para AAAA-MM."
                ),
                issue_code="CAB-DATA-003",
                issue_message=(
                    "dataBase é anterior ao mínimo 2020-12 "
                    "definido no XSD fornecido."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-DATA-001",
            rule_description=(
                "Conversão de dataBase para AAAA-MM e "
                "validação semestral."
            ),
        )

    @staticmethod
    def _normalize_conglomerate_code(
        value: Any,
    ) -> _FieldNormalization:
        normalized = _scalar_to_text(value).upper()

        if not _CONGLOMERATE_PATTERN.fullmatch(
            normalized
        ):
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-CONG-001",
                rule_description=(
                    "Remoção de espaços externos e conversão "
                    "do código para maiúsculas."
                ),
                issue_code="CAB-CONG-001",
                issue_message=(
                    "codigoConglomerado deve conter C seguido "
                    "de 7 dígitos."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-CONG-001",
            rule_description=(
                "Remoção de espaços externos, conversão para "
                "maiúsculas e validação de C seguido de 7 dígitos."
            ),
        )

    @staticmethod
    def _normalize_cnpj(
        value: Any,
    ) -> _FieldNormalization:
        text = _scalar_to_text(value)
        digits = re.sub(r"[./-]", "", text)
        normalized = (
            digits[:8]
            if _FULL_CNPJ_PATTERN.fullmatch(digits)
            else digits
        )

        if not _CNPJ_PATTERN.fullmatch(normalized):
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-CNPJ-001",
                rule_description=(
                    "Remoção controlada de '.', '/' e '-' e "
                    "extração da raiz quando aplicável."
                ),
                issue_code="CAB-CNPJ-001",
                issue_message=(
                    "cnpj deve conter somente a raiz de "
                    "8 dígitos."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-CNPJ-001",
            rule_description=(
                "Remoção controlada de pontuação, extração "
                "da raiz de CNPJ completo e validação dos 8 dígitos."
            ),
        )

    @staticmethod
    def _normalize_submission_type(
        value: Any,
    ) -> _FieldNormalization:
        normalized = _scalar_to_text(value).upper()

        if normalized not in {"I", "S"}:
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-REM-001",
                rule_description=(
                    "Remoção de espaços externos e conversão "
                    "para maiúsculas."
                ),
                issue_code="CAB-REM-001",
                issue_message=(
                    "tipoRemessa deve ser I ou S."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-REM-001",
            rule_description=(
                "Remoção de espaços externos, conversão para "
                "maiúsculas e validação do domínio I/S."
            ),
        )

    @staticmethod
    def _normalize_accumulated_provision_option(
        value: Any,
    ) -> _FieldNormalization:
        normalized = _scalar_to_text(value).upper()

        if normalized not in {"S", "N"}:
            return _FieldNormalization(
                normalized_value=normalized,
                rule_code="NORM-CAB-PROV-001",
                rule_description=(
                    "Remoção de espaços externos e conversão "
                    "para maiúsculas."
                ),
                issue_code="CAB-PROV-001",
                issue_message=(
                    "opcaoPorProvisaoAcumulada deve ser S ou N."
                ),
            )

        return _FieldNormalization(
            normalized_value=normalized,
            rule_code="NORM-CAB-PROV-001",
            rule_description=(
                "Remoção de espaços externos, conversão para "
                "maiúsculas e validação do domínio S/N."
            ),
        )

    @staticmethod
    def _required_value(
        values: Mapping[str, str | None],
        field_name: str,
    ) -> str:
        value = values.get(field_name)

        if value is None:
            raise ValueError(
                f"Campo normalizado ausente: {field_name}"
            )

        return value

    @staticmethod
    def _was_changed(
        *,
        original_value: Any,
        resolved_value: Any,
        normalized_value: str | None,
        fixed_source: bool,
    ) -> bool:
        if fixed_source:
            return True

        if normalized_value is None:
            return True

        if isinstance(resolved_value, str):
            return resolved_value != normalized_value

        return str(resolved_value) != normalized_value


def _scalar_to_text(value: Any) -> str:
    """Converte códigos simples sem preencher zeros inexistentes."""

    if isinstance(value, bool):
        return str(value).strip()

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()

    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return str(value.quantize(Decimal("1")))
        return format(value, "f").strip()

    return str(value).strip()


def _parse_year_month(
    value: Any,
) -> tuple[int, int] | None:
    """Converte formatos documentados para ano e mês."""

    if isinstance(value, datetime):
        return value.year, value.month

    if isinstance(value, date):
        return value.year, value.month

    if not isinstance(value, str):
        return None

    text = value.strip()

    direct_match = _YEAR_MONTH_PATTERN.fullmatch(text)
    if direct_match:
        year = int(direct_match.group("year"))
        month = int(direct_match.group("month"))

        if 1 <= month <= 12:
            return year, month

        return None

    month_year_match = _MONTH_YEAR_PATTERN.fullmatch(text)
    if month_year_match:
        year = int(month_year_match.group("year"))
        month = int(month_year_match.group("month"))

        if 1 <= month <= 12:
            return year, month

        return None

    for pattern in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue

        return parsed.year, parsed.month

    try:
        parsed_iso = datetime.fromisoformat(text)
    except ValueError:
        return None

    return parsed_iso.year, parsed_iso.month


def normalize_header(
    header_data: HeaderData,
) -> HeaderNormalizationResult:
    """Atalho funcional para o normalizador padrão."""

    return HeaderNormalizer().normalize(header_data)
