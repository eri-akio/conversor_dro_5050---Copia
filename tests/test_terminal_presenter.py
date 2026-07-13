"""Testes da apresentação estruturada das etapas no terminal."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from src.domain.conversion import (
    ConversionStage,
    ConversionStageRecord,
    ConversionStageStatus,
)
from src.presenters import (
    print_conversion_result,
    print_conversion_summary,
    print_execution_failure,
    print_interface_failure,
    print_gui_conversion_result,
)


def _record(
    stage: ConversionStage = ConversionStage.READ_EXCEL,
    *,
    status: ConversionStageStatus = ConversionStageStatus.COMPLETED,
    message: str = "Arquivo lido com sucesso.",
) -> ConversionStageRecord:
    now = datetime(2026, 7, 12, 10, 0, 0)
    return ConversionStageRecord(
        stage=stage,
        status=status,
        started_at=now,
        finished_at=now,
        message=message,
    )


def _result(*records: ConversionStageRecord):
    return SimpleNamespace(
        stage_records=records,
        status=SimpleNamespace(value="NÃO APTO PARA ENVIO"),
        status_local=SimpleNamespace(value="APROVADO"),
        status_xsd=SimpleNamespace(value="APROVADO"),
        status_externo=SimpleNamespace(value="NAO_EXECUTADO"),
        status_historico=SimpleNamespace(value="NAO_EXECUTADO"),
        has_technical_failure=False,
        final_message="Aptidão completa não comprovada.",
    )


def test_terminal_prints_execution_steps(capsys) -> None:
    print_conversion_result(_result(_record()))

    output = capsys.readouterr().out
    assert "ETAPAS DA EXECUÇÃO" in output
    assert "Etapa" in output
    assert "Situação" in output
    assert "Mensagem" in output
    assert ConversionStage.READ_EXCEL.value in output
    assert "Arquivo lido com sucesso." in output
    assert "Status final" in output


def test_terminal_does_not_print_legacy_blocks(capsys) -> None:
    print_conversion_result(_result(_record()))

    output = capsys.readouterr().out
    assert "[1/5] Configuração central" not in output
    assert "RESULTADO DA CONVERSÃO" not in output
    assert "Execução:" not in output
    assert "Duração:" not in output
    assert "Motivos e avisos:" not in output


def test_terminal_does_not_duplicate_identical_stage(capsys) -> None:
    record = _record()

    print_conversion_result(_result(record, record))

    output = capsys.readouterr().out
    assert output.count(ConversionStage.READ_EXCEL.value) == 1
    assert output.count("Arquivo lido com sucesso.") == 1


def test_long_message_wraps_without_losing_content(capsys) -> None:
    message = (
        "Mensagem longa para comprovar que a apresentação mantém "
        "a tabela legível e não descarta o diagnóstico do usuário."
    )

    print_conversion_result(_result(_record(message=message)))

    output = capsys.readouterr().out
    compact_output = " ".join(output.split())
    assert message in compact_output


def test_technical_failure_has_stage_and_final_status(capsys) -> None:
    print_execution_failure(
        "Leitura do Excel",
        "Não foi possível abrir o arquivo.",
    )

    output = capsys.readouterr().out
    assert "Leitura do Excel" in output
    assert output.count("FALHA TÉCNICA") == 2
    assert "Conversão interrompida." in output


def test_gui_conversion_summary_is_printed_without_artifact_paths(
    capsys,
) -> None:
    print_conversion_summary(_result(_record()))

    output = capsys.readouterr().out
    assert output == (
        "Conversão concluída.\n"
        "\n"
        "Status local: APROVADO\n"
        "Validação XSD: APROVADO\n"
        "Validações externas: NAO_EXECUTADO\n"
        "Validações históricas: NAO_EXECUTADO\n"
        "Status final: NÃO APTO PARA ENVIO\n"
        "\n"
        "Aptidão completa não comprovada.\n"
    )
    assert "XML" not in output
    assert "XLSX" not in output


def test_interface_failure_prints_technical_details(capsys) -> None:
    print_interface_failure(
        code="GUI-TEC-001",
        message="falha simulada",
        exception_type="ValueError",
        details=(("etapa", "leitura"),),
    )

    output = capsys.readouterr().out
    assert "Falha técnica." in output
    assert "Código: GUI-TEC-001" in output
    assert "Tipo: ValueError" in output
    assert "Mensagem: falha simulada" in output
    assert "etapa: leitura" in output


def test_gui_terminal_keeps_execution_steps_and_summary(capsys) -> None:
    print_gui_conversion_result(_result(_record()))

    output = capsys.readouterr().out
    expected_header = "".join(
        (
            "ETAPAS DA EXECUÇÃO\n",
            "=" * 112,
            "\n",
            f"{'Etapa':<36}  {'Situação':<21}  Mensagem\n",
            "-" * 112,
        )
    )
    assert output.startswith(expected_header)
    assert output.count(ConversionStage.READ_EXCEL.value) == 1
    assert "Status final" in output
    assert "Conversão concluída." in output
    assert "Status local: APROVADO" in output
    assert "Aptidão completa não comprovada." in output
