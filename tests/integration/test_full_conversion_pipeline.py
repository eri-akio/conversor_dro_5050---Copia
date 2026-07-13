"""Cenários ponta a ponta do serviço público de conversão."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.conversion import ConversionStage
from src.domain.reporting import (
    ExternalValidationStatus,
    FinalExecutionStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    XsdValidationSummaryStatus,
)
from src.presenters import print_conversion_result
from src.services import convert_excel

from .workbook_factory import (
    CREDIT_ACCOUNT,
    DEBIT_ACCOUNT,
    create_missing_reference_workbook,
    create_workbook,
    make_row,
)


def test_complete_pipeline_keeps_status_scopes_and_only_two_artifacts(
    tmp_path: Path,
    capsys,
) -> None:
    path = create_workbook(
        tmp_path / "complete.xlsx",
        rows=(
            make_row(),
            make_row(
                event_id="CON0001",
                total_loss=700,
                accounting_loss=700,
            ),
        ),
    )
    output = tmp_path / "output"

    result = convert_excel(path, output_dir=output)
    print_conversion_result(result)

    assert result.status == FinalExecutionStatus.NOT_APT
    assert result.status_local == LocalValidationStatus.REPROVED
    assert result.status_xsd == XsdValidationSummaryStatus.APPROVED
    assert result.status_externo == ExternalValidationStatus.PENDING
    assert result.status_historico == HistoricalValidationStatus.PENDING
    assert not result.has_technical_failure
    assert result.artifacts.xml_path is not None
    assert result.artifacts.xlsx_path is not None
    assert result.artifacts.xml_path.parent == output.resolve()
    assert result.artifacts.xlsx_path.parent == output.resolve()
    assert {item.suffix.lower() for item in output.iterdir()} == {
        ".xml",
        ".xlsx",
    }
    assert not (output / "logs").exists()
    assert not list(output.glob("*.txt"))
    terminal = capsys.readouterr().out
    assert "Etapa" in terminal
    assert "Situação" in terminal
    assert "Mensagem" in terminal
    assert "Aptidão para envio" in terminal
    assert terminal.count("LEITURA DO EXCEL") == 1


@pytest.mark.parametrize("missing_kind", ["system", "account"])
def test_missing_reference_is_a_local_regulatory_failure(
    tmp_path: Path,
    missing_kind: str,
) -> None:
    path = tmp_path / f"missing_{missing_kind}.xlsx"
    if missing_kind == "system":
        create_missing_reference_workbook(path)
    else:
        create_workbook(
            path,
            rows=(make_row(),),
            accounts=(DEBIT_ACCOUNT,),
        )

    result = convert_excel(path, output_dir=tmp_path / "output")
    references = result.output(ConversionStage.VALIDATE_REFERENCES)

    assert not references.is_valid
    assert references.failed_rules
    assert result.status_local == LocalValidationStatus.REPROVED
    assert not result.has_technical_failure


def test_normalized_event_id_collision_reproves_without_merging(
    tmp_path: Path,
) -> None:
    path = create_workbook(
        tmp_path / "collision.xlsx",
        rows=(
            make_row(
                event_id="IND-0001",
                overrides={"codigoEventoOrigem": "ORIGIND001"},
            ),
            make_row(
                event_id="IND0001",
                overrides={"codigoEventoOrigem": "ORIGIND002"},
            ),
        ),
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    grouping = result.output(ConversionStage.GROUP_EVENTS)

    assert result.status_local == LocalValidationStatus.REPROVED
    assert grouping.event_count == 0
    assert grouping.ungrouped_row_numbers == (2, 3)
    collision = next(
        rule
        for rule in grouping.rule_results
        if rule.code == "MAP-EVT-ID-COLISAO-001"
    )
    assert collision.row_numbers == (2, 3)
    assert collision.id_evento == "IND0001"


def test_unreadable_input_is_reported_as_technical_failure(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does_not_exist.xlsx"

    result = convert_excel(missing, output_dir=tmp_path / "output")

    assert result.status == FinalExecutionStatus.TECHNICAL_FAILURE
    assert result.has_technical_failure
    assert result.failed_stage is not None
    assert result.failed_stage.stage == ConversionStage.READ_EXCEL
    assert result.exit_code == 2
