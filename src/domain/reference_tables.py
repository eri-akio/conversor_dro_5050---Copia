"""Modelos das tabelas de sistemas e contas internas."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.base_row_validation import RuleExecutionStatus
from src.domain.normalization import NormalizationResult


class ReferenceTableKind(StrEnum):
    """Tipo de tabela auxiliar do Documento 5050."""

    SOURCE_SYSTEM = "SISTEMA DE ORIGEM"
    INTERNAL_ACCOUNT = "CONTA INTERNA"


@dataclass(frozen=True, slots=True)
class ReferenceTableRecord:
    """Registro normalizado de uma tabela auxiliar."""

    kind: ReferenceTableKind
    sheet_name: str
    row_number: int
    code_column: str
    name_column: str
    code_result: NormalizationResult[str]
    name_result: NormalizationResult[str]

    @property
    def code(self) -> str | None:
        return self.code_result.serialized_value

    @property
    def name(self) -> str | None:
        return self.name_result.serialized_value

    @property
    def is_valid(self) -> bool:
        return (
            self.code_result.is_valid
            and self.name_result.is_valid
        )


@dataclass(frozen=True, slots=True)
class ReferenceTableRuleResult:
    """Resultado rastreável de uma regra das tabelas auxiliares."""

    code: str
    description: str
    source: str
    severity: str
    status: RuleExecutionStatus
    sheet_name: str
    row_numbers: tuple[int, ...]
    columns: tuple[str, ...]
    message: str
    suggestion: str | None = None
    id_evento: str | None = None
    accounting_row_number: int | None = None
    values: tuple[tuple[str, Any], ...] = ()

    @property
    def blocks_processing(self) -> bool:
        return (
            self.status == RuleExecutionStatus.FAILED
            and self.severity in {
                "ERRO IMPEDITIVO",
                "ERRO",
            }
        )


@dataclass(frozen=True, slots=True)
class ReferenceTableData:
    """Leitura normalizada e validada de uma tabela auxiliar."""

    kind: ReferenceTableKind
    sheet_name: str
    code_column: str
    name_column: str
    actual_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]
    records: tuple[ReferenceTableRecord, ...]
    rule_results: tuple[ReferenceTableRuleResult, ...]

    @property
    def row_count(self) -> int:
        return len(self.records)

    @property
    def valid_record_count(self) -> int:
        return sum(record.is_valid for record in self.records)

    @property
    def invalid_record_count(self) -> int:
        return self.row_count - self.valid_record_count

    @property
    def code_index(
        self,
    ) -> Mapping[str, tuple[ReferenceTableRecord, ...]]:
        by_code: dict[str, list[ReferenceTableRecord]] = {}

        for record in self.records:
            if not record.code_result.is_valid or record.code is None:
                continue

            by_code.setdefault(record.code, []).append(record)

        frozen = {
            code: tuple(records)
            for code, records in by_code.items()
        }
        return MappingProxyType(frozen)

    @property
    def unique_valid_records(
        self,
    ) -> Mapping[str, ReferenceTableRecord]:
        unique: dict[str, ReferenceTableRecord] = {}

        for code, records in self.code_index.items():
            if len(records) == 1 and records[0].is_valid:
                unique[code] = records[0]

        return MappingProxyType(unique)

    @property
    def is_valid(self) -> bool:
        return not any(
            result.blocks_processing
            for result in self.rule_results
        )


@dataclass(frozen=True, slots=True)
class ReferenceTablesReadResult:
    """Resultado da leitura das duas tabelas auxiliares."""

    systems: ReferenceTableData
    accounts: ReferenceTableData

    @property
    def rule_results(
        self,
    ) -> tuple[ReferenceTableRuleResult, ...]:
        return (
            *self.systems.rule_results,
            *self.accounts.rule_results,
        )

    @property
    def is_valid(self) -> bool:
        return self.systems.is_valid and self.accounts.is_valid


@dataclass(frozen=True, slots=True)
class ReferenceTablesValidationResult:
    """Leitura das tabelas mais validação dos códigos utilizados."""

    read_result: ReferenceTablesReadResult
    usage_rule_results: tuple[ReferenceTableRuleResult, ...]
    unused_system_codes: tuple[str, ...]
    unused_account_codes: tuple[str, ...]

    @property
    def systems(self) -> ReferenceTableData:
        return self.read_result.systems

    @property
    def accounts(self) -> ReferenceTableData:
        return self.read_result.accounts

    @property
    def rule_results(
        self,
    ) -> tuple[ReferenceTableRuleResult, ...]:
        return (
            *self.read_result.rule_results,
            *self.usage_rule_results,
        )

    @property
    def failed_rules(
        self,
    ) -> tuple[ReferenceTableRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.FAILED
        )

    @property
    def not_executed_rules(
        self,
    ) -> tuple[ReferenceTableRuleResult, ...]:
        return tuple(
            result
            for result in self.rule_results
            if result.status == RuleExecutionStatus.NOT_EXECUTED
        )

    @property
    def is_valid(self) -> bool:
        return not any(
            result.blocks_processing
            for result in self.rule_results
        )

    @property
    def is_fully_verified(self) -> bool:
        return self.is_valid and not self.not_executed_rules

    @property
    def status_counts(
        self,
    ) -> Mapping[RuleExecutionStatus, int]:
        counter: Counter[RuleExecutionStatus] = Counter(
            result.status
            for result in self.rule_results
        )
        return MappingProxyType(dict(counter))
