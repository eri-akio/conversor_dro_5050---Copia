"""Testes do serviço completo de conversão."""

from __future__ import annotations

from pathlib import Path

from src.domain.conversion import (
    ConversionStage,
    ConversionStageStatus,
)
from src.domain.reporting import (
    ExternalValidationStatus,
    FinalExecutionStatus,
    FinalValidationStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    XsdValidationSummaryStatus,
)
from src.domain.xsd_validation import (
    XsdValidationStatus,
)
from src.services import convert_excel


SAMPLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "DRO_5050_planilha_testes.xlsx"
)


def test_complete_service_returns_single_result(
    tmp_path: Path,
) -> None:
    result = convert_excel(
        SAMPLE_PATH,
        output_dir=tmp_path / "saida",
    )

    assert result.status == FinalExecutionStatus.NOT_APT
    assert result.status_local == LocalValidationStatus.REPROVED
    assert result.status_xsd == (
        XsdValidationSummaryStatus.REPROVED
    )
    assert result.status_externo == (
        ExternalValidationStatus.NOT_EXECUTED
    )
    assert result.status_historico == (
        HistoricalValidationStatus.NOT_EXECUTED
    )
    assert result.status_final == (
        FinalValidationStatus.NOT_APT_FOR_SUBMISSION
    )
    assert result.exit_code == 0
    assert result.execution_id.startswith("DRO5050-")
    assert result.artifacts.xml_path is not None
    assert result.artifacts.xml_path.is_file()
    assert result.artifacts.xlsx_path is not None
    assert result.artifacts.xlsx_path.is_file()
    assert not (tmp_path / "logs").exists()
    assert result.artifacts.xml_path.parent == tmp_path / "saida"
    assert result.artifacts.xlsx_path.parent == tmp_path / "saida"
    assert not (tmp_path / "saida" / "xml").exists()
    assert not (tmp_path / "saida" / "relatorios").exists()

    xsd_result = result.output(
        ConversionStage.VALIDATE_XSD
    )
    assert xsd_result.status == XsdValidationStatus.INVALID

    reconciliation = result.output(
        ConversionStage.RECONCILE_RULES
    )
    assert reconciliation.records
    assert reconciliation.is_fully_reconciled
    assert not reconciliation.unresolved_records

    report_result = result.output(
        ConversionStage.GENERATE_REPORTS
    )
    assert report_result.data.status_final == (
        FinalValidationStatus.NOT_APT_FOR_SUBMISSION
    )
    assert report_result.data.execution_id == result.execution_id
    assert (
        report_result.data.final_status
        == result.status
    )
    assert report_result.data.status_local == result.status_local
    assert report_result.data.status_xsd == result.status_xsd
    assert (
        report_result.data.status_externo
        == result.status_externo
    )
    assert (
        report_result.data.status_historico
        == result.status_historico
    )
    assert any(
        record.status == "ADIADA"
        and record.scope == "LINHA"
        and record.definitive_result is not None
        for record in report_result.data.records
    )

    assert result.stage_records[-1].stage == (
        ConversionStage.GENERATE_REPORTS
    )
    assert result.stage_records[-1].status == (
        ConversionStageStatus.COMPLETED
    )


def test_missing_excel_is_technical_failure_with_reports(
    tmp_path: Path,
) -> None:
    result = convert_excel(
        tmp_path / "inexistente.xlsx",
        output_dir=tmp_path / "saida",
    )

    assert result.status == (
        FinalExecutionStatus.TECHNICAL_FAILURE
    )
    assert result.exit_code == 2
    assert result.artifacts.xml_path is None
    assert result.failed_stage is not None
    assert result.failed_stage.stage == (
        ConversionStage.READ_EXCEL
    )
    assert any(
        issue.code == "XLSX-READ-001"
        for issue in result.issues
    )

    assert result.artifacts.xlsx_path is not None
    assert (
        result.artifacts.xlsx_path.name
        == "Relatorio_DRO_5050_SEM_DATA_BASE.xlsx"
    )
    assert not (tmp_path / "logs").exists()


def test_custom_output_directory_is_respected(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "custom_output"

    result = convert_excel(
        SAMPLE_PATH,
        output_dir=output_dir,
    )

    assert result.artifacts.xml_path is not None
    assert result.artifacts.xml_path.parent == output_dir
    assert result.artifacts.xlsx_path is not None
    assert result.artifacts.xlsx_path.parent == output_dir
    assert not (tmp_path / "custom_logs").exists()


def test_service_does_not_overwrite_previous_outputs(
    tmp_path: Path,
) -> None:
    kwargs = {
        "output_dir": tmp_path / "saida",
    }

    first = convert_excel(SAMPLE_PATH, **kwargs)
    second = convert_excel(SAMPLE_PATH, **kwargs)

    assert first.artifacts.xml_path is not None
    assert second.artifacts.xml_path is not None
    assert (
        first.artifacts.xml_path
        != second.artifacts.xml_path
    )

    assert first.artifacts.xlsx_path is not None
    assert second.artifacts.xlsx_path is not None
    assert (
        first.artifacts.xlsx_path
        != second.artifacts.xlsx_path
    )
    assert second.artifacts.xlsx_path.name.endswith(
        "_001.xlsx"
    )
