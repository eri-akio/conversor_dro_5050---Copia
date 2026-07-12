"""Testes da seleção automática de instrução e XSD."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.config import (
    INSTRUCTION_2020_PATH,
    INSTRUCTION_2026_PATH,
    XSD_2020_PATH,
    XSD_2025_PATH,
)
from src.domain.document_header import DocumentHeader
from src.domain.regulatory_version import (
    RegulatoryVersion,
    VersionStatus,
    YearMonth,
)
from src.services.version_resolver import (
    VERSION_PROFILES,
    VersionResolver,
    resolve_version,
)


@pytest.mark.parametrize(
    ("data_base", "expected_code"),
    [
        ("2020-12", "DRO_2020_12"),
        ("2021-06", "DRO_2020_12"),
        ("2024-12", "DRO_2020_12"),
        ("2025-06", "DRO_2025_06"),
        ("2025-12", "DRO_2025_06"),
        ("2026-06", "DRO_2025_06"),
        ("2026-12", "DRO_2026_12_PRESUMIDA"),
        ("2027-06", "DRO_2026_12_PRESUMIDA"),
    ],
)
def test_profile_boundaries(
    data_base: str,
    expected_code: str,
) -> None:
    result = resolve_version(data_base)

    assert result.is_resolved
    assert result.profile is not None
    assert result.profile.code == expected_code
    assert result.can_continue_diagnostic


def test_2020_profile_selects_2020_instruction_and_xsd() -> None:
    result = resolve_version("2024-12")
    profile = result.profile

    assert profile is not None
    assert profile.instruction_version == "12/2020"
    assert profile.instruction_path == INSTRUCTION_2020_PATH
    assert profile.xsd_version == "12/2020"
    assert profile.xsd_path == XSD_2020_PATH
    assert profile.status == VersionStatus.CONFIRMED
    assert result.is_confirmed
    assert not result.blocks_apt


def test_2025_profile_selects_2020_instruction_and_2025_xsd() -> None:
    result = resolve_version("2026-06")
    profile = result.profile

    assert profile is not None
    assert profile.code == "DRO_2025_06"
    assert profile.instruction_version == "12/2020"
    assert profile.instruction_path == INSTRUCTION_2020_PATH
    assert profile.xsd_version == "06/2025"
    assert profile.xsd_path == XSD_2025_PATH
    assert result.is_confirmed
    assert not result.blocks_apt


def test_2026_profile_is_selected_but_blocks_apt() -> None:
    result = resolve_version("2026-12")
    profile = result.profile

    assert profile is not None
    assert profile.instruction_version == "12/2026"
    assert profile.instruction_path == INSTRUCTION_2026_PATH
    assert profile.xsd_path == XSD_2025_PATH
    assert (
        profile.status
        == VersionStatus.DOCUMENT_CONFLICT
    )
    assert result.blocks_apt
    assert not result.is_confirmed
    assert result.can_continue_diagnostic
    assert any(
        issue.code == "VER-001"
        for issue in result.issues
    )


def test_document_header_can_be_used_as_source() -> None:
    header = DocumentHeader(
        codigo_documento="5050",
        data_base="2025-06",
        codigo_conglomerado="C0099999",
        cnpj="99999999",
        tipo_remessa="I",
        opcao_por_provisao_acumulada="N",
    )

    result = resolve_version(header)

    assert result.profile is not None
    assert result.profile.code == "DRO_2025_06"


@pytest.mark.parametrize(
    ("data_base", "expected_code"),
    [
        ("texto", "VER-DATA-003"),
        ("2025-6", "VER-DATA-003"),
        ("2025-01", "VER-DATA-002"),
        ("2020-06", "VER-DATA-001"),
    ],
)
def test_invalid_data_base_selection(
    data_base: str,
    expected_code: str,
) -> None:
    result = resolve_version(data_base)

    assert not result.is_resolved
    assert not result.can_continue_diagnostic
    assert result.blocks_apt
    assert result.issues[0].code == expected_code


def test_missing_regulatory_file_is_technical_failure(
    tmp_path: Path,
) -> None:
    missing_xsd = tmp_path / "ausente.xsd"
    modified_profile = replace(
        VERSION_PROFILES[0],
        xsd_path=missing_xsd,
    )

    resolver = VersionResolver(
        (
            modified_profile,
            *VERSION_PROFILES[1:],
        )
    )

    result = resolver.resolve("2020-12")

    assert result.profile is not None
    assert result.has_technical_failure
    assert not result.can_continue_diagnostic
    assert any(
        issue.code == "VER-ARQ-001"
        and issue.path == missing_xsd
        for issue in result.issues
    )


def test_all_default_profile_files_exist() -> None:
    for profile in VERSION_PROFILES:
        assert profile.missing_paths() == ()


def test_profiles_are_ordered_without_overlap() -> None:
    assert VERSION_PROFILES[0].end_data_base is not None
    assert VERSION_PROFILES[1].end_data_base is not None

    assert (
        VERSION_PROFILES[0].end_data_base
        < VERSION_PROFILES[1].start_data_base
    )
    assert (
        VERSION_PROFILES[1].end_data_base
        < VERSION_PROFILES[2].start_data_base
    )


def test_year_month_uses_structured_comparison() -> None:
    assert YearMonth.parse("2024-12") < YearMonth.parse(
        "2025-06"
    )
    assert str(YearMonth(2026, 12)) == "2026-12"


def test_overlapping_catalog_is_rejected() -> None:
    overlapping = RegulatoryVersion(
        code="TESTE",
        start_data_base=YearMonth(2024, 12),
        end_data_base=YearMonth(2025, 12),
        instruction_version="teste",
        instruction_path=INSTRUCTION_2020_PATH,
        xsd_version="teste",
        xsd_path=XSD_2020_PATH,
        layout_profile="TESTE",
        status=VersionStatus.CONFIRMED,
        blocks_apt=False,
    )

    with pytest.raises(ValueError):
        VersionResolver(
            (
                VERSION_PROFILES[0],
                overlapping,
                *VERSION_PROFILES[1:],
            )
        )
