"""Modelos do relatório de execução do Conversor DRO 5050."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


class FinalExecutionStatus(StrEnum):
    """Classificação final consolidada da execução."""

    APT = "APTO PARA ENVIO"
    NOT_APT = "NÃO APTO PARA ENVIO"
    TECHNICAL_FAILURE = "FALHA TÉCNICA"


@dataclass(frozen=True, slots=True)
class ReportRecord:
    """Linha rastreável do relatório de ocorrências."""

    execution_id: str
    executed_at: datetime
    final_result: FinalExecutionStatus
    input_file: str
    xml_file: str | None
    stage: str
    sheet_name: str | None
    row_numbers: str | None
    id_evento: str | None
    columns: str | None
    original_value: str | None
    normalized_value: str | None
    rule_code: str
    rule_description: str
    source: str
    version: str
    severity: str
    status: str
    suggestion: str | None
    message: str
    dependency: str | None = None


@dataclass(frozen=True, slots=True)
class ReportRuleSummary:
    """Resumo de uma crítica oficial de pré ou pós-processamento."""

    phase: str
    code: str
    official_type: str
    description: str
    evaluated_fields: str
    source_base: str
    start_label: str
    scope: str
    execution_class: str
    dependency: str | None
    provider: str
    status: str
    evidence_count: int
    failed_evidence_count: int
    not_executed_evidence_count: int


@dataclass(frozen=True, slots=True)
class ExecutionReportData:
    """Dados finais, independentes do formato de saída."""

    execution_id: str
    started_at: datetime
    finished_at: datetime
    input_path: Path
    xml_path: Path | None
    xsd_path: Path | None
    data_base: str
    profile_code: str
    final_status: FinalExecutionStatus
    final_message: str
    records: tuple[ReportRecord, ...]
    pre_rules: tuple[ReportRuleSummary, ...]
    post_rules: tuple[ReportRuleSummary, ...]
    metrics: tuple[tuple[str, str | int], ...]

    @property
    def duration_seconds(self) -> float:
        return (
            self.finished_at - self.started_at
        ).total_seconds()

    @property
    def metric_map(self) -> Mapping[str, str | int]:
        return MappingProxyType(dict(self.metrics))

    @property
    def severity_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}

        for record in self.records:
            counts[record.severity] = (
                counts.get(record.severity, 0) + 1
            )

        return MappingProxyType(counts)

    @property
    def status_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}

        for record in self.records:
            counts[record.status] = (
                counts.get(record.status, 0) + 1
            )

        return MappingProxyType(counts)


@dataclass(frozen=True, slots=True)
class ReportArtifacts:
    """Caminho do relatório Excel gerado."""

    xlsx_path: Path


@dataclass(frozen=True, slots=True)
class ReportGenerationIssue:
    """Falha técnica durante a geração do relatório Excel."""

    code: str
    message: str
    output_type: str
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class ReportGenerationResult:
    """Resultado da geração do relatório Excel."""

    data: ExecutionReportData
    artifacts: ReportArtifacts | None
    issues: tuple[ReportGenerationIssue, ...] = ()

    @property
    def is_generated(self) -> bool:
        return (
            self.artifacts is not None
            and not self.issues
            and self.artifacts.xlsx_path.is_file()
        )
