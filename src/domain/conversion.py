"""Modelos do serviço completo de conversão DRO 5050."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.reporting import (
    DependentValidationStatus,
    ExternalValidationStatus,
    FinalExecutionStatus,
    FinalValidationStatus,
    GeneralValidationStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    ReportArtifacts,
    XsdValidationSummaryStatus,
)


class ConversionStage(StrEnum):
    """Etapas executadas pelo serviço de conversão."""

    READ_EXCEL = "LEITURA DO EXCEL"
    READ_HEADER = "LEITURA DO CABEÇALHO"
    VALIDATE_HEADER = "VALIDAÇÃO DO CABEÇALHO"
    NORMALIZE_HEADER = "NORMALIZAÇÃO DO CABEÇALHO"
    SELECT_VERSION = "SELEÇÃO DA VERSÃO"
    VALIDATE_BASE_STRUCTURE = "ESTRUTURA DA BASE"
    NORMALIZE_BASE = "NORMALIZAÇÃO DA BASE"
    VALIDATE_ROWS = "VALIDAÇÃO POR LINHA"
    GROUP_EVENTS = "AGRUPAMENTO DE EVENTOS"
    VALIDATE_EVENTS = "CONSISTÊNCIA DOS EVENTOS"
    RECONCILE_RULES = "RECONCILIAÇÃO DE REGRAS ADIADAS"
    VALIDATE_FINANCIALS = "VALIDAÇÃO FINANCEIRA"
    CLASSIFY_EVENTS = "CLASSIFICAÇÃO DOS EVENTOS"
    CALCULATE_CONSOLIDATED = "CÁLCULO DOS CONSOLIDADOS"
    VALIDATE_REFERENCES = "SISTEMAS E CONTAS"
    PRE_PROCESSING = "PRÉ-PROCESSAMENTO"
    POST_PROCESSING = "PÓS-PROCESSAMENTO"
    BUILD_DOCUMENT = "MONTAGEM DO DOCUMENTO"
    GENERATE_XML = "GERAÇÃO DO XML"
    VALIDATE_XSD = "VALIDAÇÃO XSD"
    CONSOLIDATE_STATUS = "CONSOLIDAÇÃO DO STATUS"
    GENERATE_REPORTS = "GERAÇÃO DO RELATÓRIO EXCEL"


class ConversionStageStatus(StrEnum):
    """Situação de uma etapa do pipeline."""

    COMPLETED = "CONCLUÍDA"
    STOPPED_NOT_APT = "INTERROMPIDA — NÃO APTO"
    TECHNICAL_FAILURE = "FALHA TÉCNICA"
    SKIPPED = "NÃO EXECUTADA"


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """Parâmetros de uma execução completa."""

    input_path: Path
    output_dir: Path

    @classmethod
    def create(
        cls,
        input_path: str | Path,
        *,
        output_dir: str | Path,
    ) -> "ConversionRequest":
        return cls(
            input_path=Path(
                input_path
            ).expanduser().resolve(),
            output_dir=Path(
                output_dir
            ).expanduser().resolve(),
        )


@dataclass(frozen=True, slots=True)
class ConversionIssue:
    """Ocorrência genérica usada em interrupções do pipeline."""

    code: str
    severity: str
    stage: ConversionStage
    message: str
    source: str
    blocks_apt: bool
    sheet_name: str | None = None
    row_numbers: tuple[int, ...] = ()
    id_evento: str | None = None
    columns: tuple[str, ...] = ()
    original_value: Any = None
    normalized_value: Any = None
    suggestion: str | None = None
    dependency: str | None = None
    details: tuple[tuple[str, Any], ...] = ()
    exception_type: str | None = None

    @property
    def is_technical(self) -> bool:
        return self.severity == "FALHA TÉCNICA"


@dataclass(frozen=True, slots=True)
class FinalStatusReason:
    """Razão rastreável usada na decisão final."""

    code: str
    message: str
    source: str
    severity: str
    blocks_apt: bool = True
    details: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class FinalStatusDecision:
    """Decisão única do serviço de consolidação."""

    status: FinalExecutionStatus
    status_local: LocalValidationStatus
    status_xsd: XsdValidationSummaryStatus
    status_externo: ExternalValidationStatus
    status_historico: HistoricalValidationStatus
    status_dependencias: DependentValidationStatus
    general_status: GeneralValidationStatus
    message: str
    reasons: tuple[FinalStatusReason, ...]

    @property
    def is_apt(self) -> bool:
        return self.status == FinalExecutionStatus.APT

    @property
    def is_not_apt(self) -> bool:
        return self.status == FinalExecutionStatus.NOT_APT

    @property
    def has_technical_failure(self) -> bool:
        return (
            self.status
            == FinalExecutionStatus.TECHNICAL_FAILURE
        )

    @property
    def blocking_reasons(
        self,
    ) -> tuple[FinalStatusReason, ...]:
        return tuple(
            reason
            for reason in self.reasons
            if reason.blocks_apt
        )

    @property
    def warnings(
        self,
    ) -> tuple[FinalStatusReason, ...]:
        return tuple(
            reason
            for reason in self.reasons
            if not reason.blocks_apt
        )


@dataclass(frozen=True, slots=True)
class ConversionStageRecord:
    """Tempo e resultado de uma etapa executada."""

    stage: ConversionStage
    status: ConversionStageStatus
    started_at: datetime
    finished_at: datetime
    message: str
    details: tuple[tuple[str, Any], ...] = ()

    @property
    def duration_seconds(self) -> float:
        return (
            self.finished_at - self.started_at
        ).total_seconds()


@dataclass(frozen=True, slots=True)
class ConversionArtifacts:
    """Arquivos efetivamente produzidos."""

    xml_path: Path | None = None
    reports: ReportArtifacts | None = None

    @property
    def xlsx_path(self) -> Path | None:
        if self.reports is None:
            return None
        return self.reports.xlsx_path

@dataclass(frozen=True, slots=True)
class ConversionResult:
    """Resultado completo e imutável da conversão."""

    execution_id: str
    request: ConversionRequest
    started_at: datetime
    finished_at: datetime
    decision: FinalStatusDecision
    stage_records: tuple[ConversionStageRecord, ...]
    issues: tuple[ConversionIssue, ...]
    artifacts: ConversionArtifacts
    stage_outputs: Mapping[ConversionStage, Any]

    @property
    def status(self) -> FinalExecutionStatus:
        return self.decision.status

    @property
    def status_local(self) -> LocalValidationStatus:
        return self.decision.status_local

    @property
    def status_xsd(self) -> XsdValidationSummaryStatus:
        return self.decision.status_xsd

    @property
    def status_externo(self) -> ExternalValidationStatus:
        return self.decision.status_externo

    @property
    def status_historico(self) -> HistoricalValidationStatus:
        return self.decision.status_historico

    @property
    def status_dependencias(self) -> DependentValidationStatus:
        return self.decision.status_dependencias

    @property
    def general_status(self) -> GeneralValidationStatus:
        return self.decision.general_status

    @property
    def status_final(self) -> FinalValidationStatus:
        return FinalValidationStatus.from_execution_status(
            self.decision.status
        )

    @property
    def final_message(self) -> str:
        return self.decision.message

    @property
    def duration_seconds(self) -> float:
        return (
            self.finished_at - self.started_at
        ).total_seconds()

    @property
    def is_apt(self) -> bool:
        return self.decision.is_apt

    @property
    def is_not_apt(self) -> bool:
        return self.decision.is_not_apt

    @property
    def has_technical_failure(self) -> bool:
        return self.decision.has_technical_failure

    @property
    def exit_code(self) -> int:
        """APTO e NÃO APTO são execuções concluídas."""

        return 2 if self.has_technical_failure else 0

    @property
    def completed_stages(
        self,
    ) -> tuple[ConversionStageRecord, ...]:
        return tuple(
            record
            for record in self.stage_records
            if (
                record.status
                == ConversionStageStatus.COMPLETED
            )
        )

    @property
    def failed_stage(
        self,
    ) -> ConversionStageRecord | None:
        for record in reversed(self.stage_records):
            if record.status in {
                ConversionStageStatus.STOPPED_NOT_APT,
                ConversionStageStatus.TECHNICAL_FAILURE,
            }:
                return record
        return None

    def output(
        self,
        stage: ConversionStage,
        default: Any = None,
    ) -> Any:
        return self.stage_outputs.get(stage, default)


def freeze_stage_outputs(
    values: Mapping[ConversionStage, Any],
) -> Mapping[ConversionStage, Any]:
    """Cria uma visão imutável dos resultados intermediários."""

    return MappingProxyType(dict(values))
