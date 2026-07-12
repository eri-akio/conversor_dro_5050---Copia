"""Integração do documento de domínio com XML e XSD selecionado."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from lxml import etree

from src.domain.conversion import ConversionStage
from src.domain.xsd_validation import XsdValidationStatus
from src.services import convert_excel
from src.services.xsd_validation_service import validate_generated_xml

from .workbook_factory import create_workbook, make_row


def _mixed_workbook(path: Path) -> Path:
    return create_workbook(
        path,
        rows=(
            make_row(),
            make_row(
                event_id="CON0001",
                category="2",
                total_loss=700,
                accounting_loss=700,
            ),
        ),
    )


def test_xml_contains_individual_and_consolidated_blocks_without_nulls(
    tmp_path: Path,
) -> None:
    result = convert_excel(
        _mixed_workbook(tmp_path / "mixed.xlsx"),
        output_dir=tmp_path / "output",
    )

    xml_path = result.artifacts.xml_path
    assert xml_path is not None
    payload = xml_path.read_bytes()
    tree = etree.parse(str(xml_path))
    individual = tree.find("./eventosIndividualizados/evento")
    consolidated = tree.find(
        "./eventosConsolidados/eventoConsolidado"
    )

    assert tree.getroot().tag == "documento"
    assert individual is not None
    assert individual.get("idEvento") == "IND0001"
    assert individual.get("totalPerdaEfetiva") == "2300.00"
    assert individual.get("ligadoRiscoSocioAmbiental") == "N"
    assert "ligacaoRiscoSocioambiental" not in individual.attrib
    assert consolidated is not None
    assert consolidated.get("categoriaNivel1Consol") == "2"
    assert consolidated.get("perdaEfetivaTotalConsol") == "700.00"
    assert b"None" not in payload


def test_selected_version_validates_generated_xml(
    tmp_path: Path,
) -> None:
    result = convert_excel(
        _mixed_workbook(tmp_path / "valid_xsd.xlsx"),
        output_dir=tmp_path / "output",
    )
    selection = result.output(ConversionStage.SELECT_VERSION)
    xsd = result.output(ConversionStage.VALIDATE_XSD)

    assert selection.profile is not None
    assert xsd.status == XsdValidationStatus.VALID
    assert xsd.xsd_path.name == "dro_5050_2025_06.xsd"
    assert xsd.profile_code == selection.profile.code


def test_schema_rejects_xml_missing_required_header_attribute(
    tmp_path: Path,
) -> None:
    result = convert_excel(
        _mixed_workbook(tmp_path / "invalid_xsd.xlsx"),
        output_dir=tmp_path / "output",
    )
    generated = result.output(ConversionStage.GENERATE_XML)
    selection = result.output(ConversionStage.SELECT_VERSION)
    assert generated.output_path is not None
    assert selection.profile is not None

    invalid_path = tmp_path / "invalid_required_attribute.xml"
    tree = etree.parse(str(generated.output_path))
    root = tree.getroot()
    required_attribute = next(iter(root.attrib))
    del root.attrib[required_attribute]
    tree.write(
        str(invalid_path),
        encoding="utf-8",
        xml_declaration=True,
    )
    invalid_generation = replace(
        generated,
        output_path=invalid_path,
        bytes_written=invalid_path.stat().st_size,
    )

    validation = validate_generated_xml(
        invalid_generation,
        selection.profile,
        data_base="2026-06",
    )

    assert validation.status == XsdValidationStatus.INVALID
    assert validation.schema_errors
    assert validation.final_xml_path == invalid_path
