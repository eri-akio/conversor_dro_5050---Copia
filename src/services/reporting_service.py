"""Coordenação da geração do relatório Excel da execução."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config import (
    OUTPUT_DIR,
    build_report_xlsx_filename,
)
from src.domain.reporting import (
    ExecutionReportData,
    ReportArtifacts,
    ReportGenerationIssue,
    ReportGenerationResult,
)
from src.reporters import XlsxReportWriter


@dataclass(frozen=True, slots=True)
class ReportingServiceError(Exception):
    """Falha técnica impeditiva do serviço de relatórios."""

    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ReportingService:
    """Gera somente o relatório XLSX, sem sobrescrever arquivos."""

    def __init__(
        self,
        *,
        xlsx_writer: XlsxReportWriter | None = None,
    ) -> None:
        self.xlsx_writer = xlsx_writer or XlsxReportWriter()

    def generate(
        self,
        data: ExecutionReportData,
        *,
        output_dir: str | Path = OUTPUT_DIR,
    ) -> ReportGenerationResult:
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        xlsx_path = self._unique_path(
            output_directory / self._build_filename(data)
        )
        issues: list[ReportGenerationIssue] = []

        try:
            self.xlsx_writer.write(data, xlsx_path)
        except Exception as error:
            issues.append(
                ReportGenerationIssue(
                    code="REL-XLSX-001",
                    message=str(error),
                    output_type="XLSX",
                    path=xlsx_path,
                )
            )

        artifacts = (
            ReportArtifacts(xlsx_path=xlsx_path)
            if not issues
            else None
        )
        return ReportGenerationResult(
            data=data,
            artifacts=artifacts,
            issues=tuple(issues),
        )

    @staticmethod
    def _build_filename(data: ExecutionReportData) -> str:
        """Usa ``SEM_DATA_BASE`` sem inventar uma competência."""

        try:
            return build_report_xlsx_filename(data.data_base)
        except ValueError:
            return "Relatorio_DRO_5050_SEM_DATA_BASE.xlsx"

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path

        for index in range(1, 10000):
            candidate = path.with_name(
                f"{path.stem}_{index:03d}{path.suffix}"
            )
            if not candidate.exists():
                return candidate

        raise ReportingServiceError(
            code="REL-NOME-001",
            message=(
                "Não foi encontrado um nome livre "
                f"para {path.name}."
            ),
        )


def generate_reports(
    data: ExecutionReportData,
    *,
    output_dir: str | Path = OUTPUT_DIR,
) -> ReportGenerationResult:
    """Atalho funcional para gerar o relatório Excel."""

    return ReportingService().generate(
        data,
        output_dir=output_dir,
    )
