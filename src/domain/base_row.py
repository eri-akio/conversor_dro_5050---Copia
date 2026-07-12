"""Modelos normalizados de uma linha da aba ``Base``."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.normalization import (
    NormalizationResult,
    NormalizationStatus,
)


@dataclass(frozen=True, slots=True)
class NormalizedBaseField:
    """Campo de uma linha após a tentativa de normalização."""

    column_name: str
    coordinate: str | None
    applicable: bool
    result: NormalizationResult[Any]

    @property
    def original_value(self) -> Any:
        return self.result.original_value

    @property
    def normalized_value(self) -> Any:
        return self.result.normalized_value

    @property
    def serialized_value(self) -> str | None:
        return self.result.serialized_value

    @property
    def status(self) -> NormalizationStatus:
        return self.result.status

    @property
    def is_valid(self) -> bool:
        return self.result.is_valid

    @property
    def is_absent(self) -> bool:
        return self.result.is_absent

    @property
    def is_invalid(self) -> bool:
        return self.result.is_invalid


@dataclass(frozen=True, slots=True)
class BaseRowIssue:
    """Ocorrência rastreável produzida para uma linha."""

    code: str
    severity: str
    message: str
    row_number: int
    column_name: str | None = None
    coordinate: str | None = None
    original_value: Any = None
    normalized_value: str | None = None
    rule_code: str | None = None

    @property
    def blocks_row(self) -> bool:
        """Erros de normalização impedem o uso da linha."""

        return self.severity in {
            "ERRO IMPEDITIVO",
            "ERRO",
        }


@dataclass(frozen=True, slots=True)
class NormalizedBaseRow:
    """Linha normalizada, ainda sem agrupamento por evento."""

    row_number: int
    profile_code: str
    fields: Mapping[str, NormalizedBaseField]
    issues: tuple[BaseRowIssue, ...]

    def get_field(
        self,
        column_name: str,
    ) -> NormalizedBaseField:
        try:
            return self.fields[column_name]
        except KeyError as error:
            raise KeyError(
                f"Campo não normalizado: {column_name}"
            ) from error

    def get_value(
        self,
        column_name: str,
        default: Any = None,
    ) -> Any:
        field = self.fields.get(column_name)
        if field is None:
            return default
        return field.normalized_value

    def get_serialized_value(
        self,
        column_name: str,
        default: str | None = None,
    ) -> str | None:
        field = self.fields.get(column_name)
        if field is None:
            return default
        return field.serialized_value

    @property
    def id_evento(self) -> str | None:
        return self.get_serialized_value("idEvento")

    @property
    def is_valid(self) -> bool:
        """Ignora campos não aplicáveis ao perfil da linha."""

        return not any(
            field.applicable and field.is_invalid
            for field in self.fields.values()
        )

    @property
    def invalid_fields(
        self,
    ) -> tuple[NormalizedBaseField, ...]:
        return tuple(
            field
            for field in self.fields.values()
            if field.applicable and field.is_invalid
        )


@dataclass(frozen=True, slots=True)
class BaseRowsNormalizationResult:
    """Resultado da normalização de todas as linhas da Base."""

    sheet_name: str
    profile_code: str
    rows: tuple[NormalizedBaseRow, ...]
    issues: tuple[BaseRowIssue, ...]
    ignored_extra_columns: tuple[str, ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def valid_row_count(self) -> int:
        return sum(row.is_valid for row in self.rows)

    @property
    def invalid_row_count(self) -> int:
        return self.row_count - self.valid_row_count

    @property
    def is_valid(self) -> bool:
        return self.invalid_row_count == 0

    @property
    def field_status_counts(
        self,
    ) -> Mapping[NormalizationStatus, int]:
        counter: Counter[NormalizationStatus] = Counter(
            field.status
            for row in self.rows
            for field in row.fields.values()
            if field.applicable
        )
        return MappingProxyType(dict(counter))

    @property
    def changed_field_count(self) -> int:
        return sum(
            field.result.changed
            for row in self.rows
            for field in row.fields.values()
            if field.applicable
        )

    @property
    def blocking_issues(
        self,
    ) -> tuple[BaseRowIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_row
        )
