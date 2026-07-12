"""Testes da validação XML com o XSD selecionado."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from lxml import etree

from src.config import (
    XSD_2020_PATH,
    XSD_2025_PATH,
)
from src.domain.document_model import (
    DocumentBuildResult,
)
from src.domain.xsd_validation import (
    XsdValidationStatus,
)
from src.services import (
    generate_xml,
    validate_generated_xml,
)
from src.validators import (
    validate_xml_with_xsd,
)
from tests.test_xml_generation import (
    complete_build_result,
    diagnostic_build_result,
)


def selected_profile():
    from src.services import resolve_version

    profile = resolve_version("2026-06").profile
    assert profile is not None
    return profile


def remove_required_root_attribute(
    xml_path: Path,
) -> None:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    del root.attrib["codigoDocumento"]
    tree.write(
        str(xml_path),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )


def test_complete_document_is_valid_in_selected_xsd(
    tmp_path: Path,
) -> None:
    profile = selected_profile()
    generated = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )

    result = validate_generated_xml(
        generated,
        profile,
        data_base="2026-06",
    )

    assert result.status == XsdValidationStatus.VALID
    assert result.is_valid
    assert not result.blocks_apt
    assert result.xsd_path == XSD_2025_PATH
    assert result.profile_code == "DRO_2025_06"
    assert not result.reclassified_to_not_apt
    assert result.final_xml_path == generated.output_path


def test_diagnostic_document_reports_missing_consolidated_event(
    tmp_path: Path,
) -> None:
    profile = selected_profile()
    generated = generate_xml(
        diagnostic_build_result(),
        output_dir=tmp_path,
    )

    result = validate_generated_xml(
        generated,
        profile,
        data_base="2026-06",
    )

    assert result.is_invalid
    assert result.blocks_apt
    assert not result.reclassified_to_not_apt
    assert result.final_xml_path == generated.output_path
    assert result.schema_errors

    issue = result.schema_errors[0]
    assert issue.code == "XSD-VAL-001"
    assert issue.line is not None
    assert issue.xpath == (
        "/documento/eventosConsolidados"
    )
    assert "eventoConsolidado" in issue.message


def test_invalid_candidate_is_reclassified_as_not_apt(
    tmp_path: Path,
) -> None:
    profile = selected_profile()
    generated = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )
    assert generated.output_path is not None
    original_path = generated.output_path

    remove_required_root_attribute(original_path)

    result = validate_generated_xml(
        generated,
        profile,
        data_base="2026-06",
    )

    assert result.is_invalid
    assert result.reclassified_to_not_apt
    assert result.final_filename == (
        "DRO_5050_2026-06_NAO_APTO.xml"
    )
    assert result.final_xml_path is not None
    assert result.final_xml_path.is_file()
    assert not original_path.exists()
    assert any(
        issue.code == "XSD-INFO-001"
        for issue in result.issues
    )


def test_reclassification_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    profile = selected_profile()
    existing = (
        tmp_path
        / "DRO_5050_2026-06_NAO_APTO.xml"
    )
    existing.write_text(
        "arquivo anterior",
        encoding="utf-8",
    )

    generated = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )
    assert generated.output_path is not None
    remove_required_root_attribute(
        generated.output_path
    )

    result = validate_generated_xml(
        generated,
        profile,
        data_base="2026-06",
    )

    assert result.reclassified_to_not_apt
    assert result.final_filename == (
        "DRO_5050_2026-06_NAO_APTO_001.xml"
    )
    assert result.collision_index == 1
    assert existing.read_text(
        encoding="utf-8"
    ) == "arquivo anterior"


def test_validator_uses_exact_profile_xsd(
    tmp_path: Path,
) -> None:
    generated = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )
    assert generated.output_path is not None

    current_profile = selected_profile()
    current = validate_xml_with_xsd(
        generated.output_path,
        current_profile,
    )
    assert current.is_valid

    old_profile = replace(
        current_profile,
        code="TESTE_XSD_2020",
        xsd_version="12/2020",
        xsd_path=XSD_2020_PATH,
    )
    old = validate_xml_with_xsd(
        generated.output_path,
        old_profile,
    )

    assert old.is_invalid
    assert old.xsd_path == XSD_2020_PATH
    assert any(
        "contaCosif" in issue.message
        for issue in old.schema_errors
    )


def test_malformed_xml_is_technical_failure(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "malformado.xml"
    xml_path.write_text(
        "<documento>",
        encoding="utf-8",
    )

    result = validate_xml_with_xsd(
        xml_path,
        selected_profile(),
    )

    assert result.has_technical_failure
    assert any(
        issue.code == "XSD-XML-002"
        for issue in result.technical_issues
    )


def test_missing_xsd_is_technical_failure(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "minimo.xml"
    xml_path.write_text(
        "<documento/>",
        encoding="utf-8",
    )
    profile = replace(
        selected_profile(),
        xsd_path=tmp_path / "ausente.xsd",
    )

    result = validate_xml_with_xsd(
        xml_path,
        profile,
    )

    assert result.has_technical_failure
    assert any(
        issue.code == "XSD-SCHEMA-001"
        for issue in result.technical_issues
    )


def test_invalid_xsd_is_technical_failure(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "minimo.xml"
    xml_path.write_text(
        "<documento/>",
        encoding="utf-8",
    )
    invalid_xsd = tmp_path / "invalido.xsd"
    invalid_xsd.write_text(
        "<xs:schema",
        encoding="utf-8",
    )
    profile = replace(
        selected_profile(),
        xsd_path=invalid_xsd,
    )

    result = validate_xml_with_xsd(
        xml_path,
        profile,
    )

    assert result.has_technical_failure
    assert any(
        issue.code == "XSD-SCHEMA-002"
        for issue in result.technical_issues
    )


def test_missing_generated_xml_returns_technical_failure() -> None:
    from src.domain.xml_generation import (
        XmlElementCounts,
        XmlGenerationMode,
        XmlGenerationResult,
    )

    generation = XmlGenerationResult(
        output_path=None,
        requested_filename=None,
        mode=XmlGenerationMode.DIAGNOSTIC,
        bytes_written=0,
        collision_index=0,
        well_formed=False,
        element_counts=XmlElementCounts(
            individualized_events=0,
            probabilities=0,
            accountings=0,
            consolidated_events=0,
            source_systems=0,
            internal_accounts=0,
        ),
        build_issue_codes=(),
        issues=(),
    )

    result = validate_generated_xml(
        generation,
        selected_profile(),
        data_base="2026-06",
    )

    assert result.has_technical_failure
    assert result.final_xml_path is None
    assert any(
        issue.code == "XSD-GEN-001"
        for issue in result.technical_issues
    )


def test_upstream_diagnostic_stays_not_apt_even_if_xsd_valid(
    tmp_path: Path,
) -> None:
    build = complete_build_result()
    assert build.document is not None

    diagnostic_build = DocumentBuildResult(
        document=build.document,
        issues=(
            # Um código já conhecido basta para manter o modo
            # diagnóstico; não altera a estrutura do XML.
            diagnostic_build_result().issues[0],
        ),
    )

    generated = generate_xml(
        diagnostic_build,
        output_dir=tmp_path,
    )
    assert generated.is_diagnostic

    result = validate_generated_xml(
        generated,
        selected_profile(),
        data_base="2026-06",
    )

    assert result.is_valid
    assert result.blocks_apt
    assert not result.reclassified_to_not_apt
    assert result.final_filename is not None
    assert "NAO_APTO" in result.final_filename
