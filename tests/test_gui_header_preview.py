"""Testes da leitura do cabeçalho exibido na interface."""

from __future__ import annotations

from pathlib import Path

from src.gui.header_preview_service import (
    preview_header,
)


SAMPLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "DRO_5050_planilha_testes.xlsx"
)


def test_preview_reads_header_and_version() -> None:
    result = preview_header(SAMPLE_PATH)

    assert result.is_valid
    assert result.can_convert
    assert result.get("codigoDocumento") == "5050"
    assert result.get("dataBase") == "2026-06"
    assert result.get(
        "codigoConglomerado"
    ) == "C0099999"
    assert result.get("cnpj") == "99999999"
    assert result.get("tipoRemessa") == "I"
    assert result.get(
        "opcaoPorProvisaoAcumulada"
    ) == "N"
    assert result.profile_code == "DRO_2025_06"
    assert result.instruction_version == "12/2020"
    assert result.xsd_version == "06/2025"
    assert result.xsd_path is not None
    assert result.xsd_path.is_file()
    assert result.version_status == "CONFIRMADA"


def test_preview_missing_file_raises_reader_error(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "ausente.xlsx"

    try:
        preview_header(missing)
    except Exception as error:
        assert getattr(
            error,
            "code",
            None,
        ) == "XLSX-READ-001"
    else:
        raise AssertionError(
            "Era esperada uma falha de leitura."
        )
