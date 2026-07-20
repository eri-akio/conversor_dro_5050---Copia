"""Testes da configuração central do projeto."""

from __future__ import annotations

import pytest

from src.config import (
    BASE_ACCOUNTING_COLUMNS,
    BASE_ALL_COLUMNS,
    BASE_CONFIRMED_REQUIRED_COLUMNS,
    BASE_EMBEDDED_REFERENCE_COLUMNS,
    BASE_EVENT_COLUMNS,
    BASE_FUTURE_COLUMNS,
    BASE_KNOWN_COLUMN_ALIASES,
    BASE_METADATA_COLUMNS,
    BASE_PROBABILITY_COLUMNS,
    DOCUMENT_CODE,
    HEADER_DOCUMENT_CODE_COLUMN,
    INSTRUCTION_2020_PATH,
    INSTRUCTION_2026_PATH,
    SOURCE_SYSTEM_NAME_COLUMN,
    SOURCE_SYSTEM_CODE_COLUMN,
    REQUIRED_SOURCE_SYSTEM_COLUMNS,
    REQUIRED_INTERNAL_ACCOUNT_COLUMNS,
    INTERNAL_ACCOUNT_NAME_COLUMN,
    INTERNAL_ACCOUNT_CODE_COLUMN,
    OPTIONAL_HEADER_COLUMNS,
    OPTIONAL_REFERENCE_SHEETS,
    PRE_PROCESSING_CRITICS_PATH,
    POST_PROCESSING_CRITICS_PATH,
    OUTPUT_DIR,
    PROJECT_ROOT,
    RECOGNIZED_HEADER_COLUMNS,
    REGULATORY_ASSETS_DIR,
    REQUIRED_HEADER_COLUMNS,
    REQUIRED_SHEETS,
    SETTINGS,
    XSD_2020_PATH,
    XSD_2025_PATH,
    XSD_PATH_BY_PROFILE,
    XML_ENCODING,
    XML_VERSION,
    build_report_xlsx_filename,
    build_xml_filename,
    ensure_runtime_directories,
    find_missing_project_paths,
    validate_data_base,
)


def test_general_document_configuration() -> None:
    assert DOCUMENT_CODE == "5050"
    assert XML_VERSION == "1.0"
    assert XML_ENCODING == "UTF-8"
    assert SETTINGS.document_code == DOCUMENT_CODE
    assert SETTINGS.project_root == PROJECT_ROOT
    assert (
        SETTINGS.regulatory_assets_dir
        == REGULATORY_ASSETS_DIR
    )


def test_required_sheet_names_are_exact() -> None:
    assert REQUIRED_SHEETS == (
        "Base",
        "Cabecalho",
    )
    assert OPTIONAL_REFERENCE_SHEETS == (
        "Sistemas_Origem",
        "Contas_Internas",
    )
    assert (
        SETTINGS.optional_reference_sheets
        == OPTIONAL_REFERENCE_SHEETS
    )


def test_header_column_configuration() -> None:
    assert HEADER_DOCUMENT_CODE_COLUMN == "codigoDocumento"
    assert REQUIRED_HEADER_COLUMNS == (
        "dataBase",
        "codigoConglomerado",
        "cnpj",
        "tipoRemessa",
        "opcaoPorProvisaoAcumulada",
    )
    assert OPTIONAL_HEADER_COLUMNS == (
        "codigoDocumento",
    )
    assert RECOGNIZED_HEADER_COLUMNS == (
        "codigoDocumento",
        "dataBase",
        "codigoConglomerado",
        "cnpj",
        "tipoRemessa",
        "opcaoPorProvisaoAcumulada",
    )
    assert (
        SETTINGS.required_header_columns
        == REQUIRED_HEADER_COLUMNS
    )


def test_base_column_configuration() -> None:
    assert BASE_METADATA_COLUMNS == ("Source.Name",)
    assert len(BASE_EVENT_COLUMNS) == 20
    assert len(BASE_PROBABILITY_COLUMNS) == 2
    assert len(BASE_ACCOUNTING_COLUMNS) == 9
    assert BASE_FUTURE_COLUMNS == (
        "idEventoAgregador",
        "dataExclusao",
        "motivoExclusao",
    )
    assert len(BASE_CONFIRMED_REQUIRED_COLUMNS) == 32
    assert BASE_EMBEDDED_REFERENCE_COLUMNS == (
        "nomeSistemaOrigem",
        "nomeContaBalAnaliticoDebito",
        "nomeContaBalAnaliticoCredito",
    )
    assert len(BASE_ALL_COLUMNS) == 38
    assert len(set(BASE_ALL_COLUMNS)) == 38
    assert (
        SETTINGS.base_confirmed_required_columns
        == BASE_CONFIRMED_REQUIRED_COLUMNS
    )
    assert (
        SETTINGS.base_future_columns
        == BASE_FUTURE_COLUMNS
    )
    assert (
        SETTINGS.base_embedded_reference_columns
        == BASE_EMBEDDED_REFERENCE_COLUMNS
    )
    assert (
        BASE_KNOWN_COLUMN_ALIASES[
            "idEventoAgreagdor"
        ]
        == "idEventoAgregador"
    )



def test_reference_table_column_configuration() -> None:
    assert SOURCE_SYSTEM_CODE_COLUMN == "codigoSistema"
    assert SOURCE_SYSTEM_NAME_COLUMN == "nomeSistema"
    assert REQUIRED_SOURCE_SYSTEM_COLUMNS == (
        "codigoSistema",
        "nomeSistema",
    )
    assert INTERNAL_ACCOUNT_CODE_COLUMN == "codigoConta"
    assert INTERNAL_ACCOUNT_NAME_COLUMN == "nomeConta"
    assert REQUIRED_INTERNAL_ACCOUNT_COLUMNS == (
        "codigoConta",
        "nomeConta",
    )
    assert (
        SETTINGS.required_source_system_columns
        == REQUIRED_SOURCE_SYSTEM_COLUMNS
    )
    assert (
        SETTINGS.required_internal_account_columns
        == REQUIRED_INTERNAL_ACCOUNT_COLUMNS
    )

def test_project_paths_are_absolute_and_inside_project() -> None:
    assert PROJECT_ROOT.is_absolute()

    for path in (
        OUTPUT_DIR,
        REGULATORY_ASSETS_DIR,
    ):
        assert path.is_absolute()
        assert PROJECT_ROOT in path.parents


def test_official_regulatory_files_exist() -> None:
    assert INSTRUCTION_2020_PATH.is_file()
    assert INSTRUCTION_2026_PATH.is_file()
    assert XSD_2020_PATH.is_file()
    assert XSD_2025_PATH.is_file()
    assert PRE_PROCESSING_CRITICS_PATH.is_file()
    assert POST_PROCESSING_CRITICS_PATH.is_file()
    assert (
        SETTINGS.pre_processing_critics_path
        == PRE_PROCESSING_CRITICS_PATH
    )
    assert (
        SETTINGS.post_processing_critics_path
        == POST_PROCESSING_CRITICS_PATH
    )

    assert (
        XSD_PATH_BY_PROFILE["DRO_2020_12"]
        == XSD_2020_PATH
    )
    assert (
        XSD_PATH_BY_PROFILE["DRO_2025_06"]
        == XSD_2025_PATH
    )
    assert (
        XSD_PATH_BY_PROFILE[
            "DRO_2026_12_PRESUMIDA"
        ]
        == XSD_2025_PATH
    )


@pytest.mark.parametrize(
    ("data_base", "expected"),
    [
        ("2025-06", "2025-06"),
        ("2025-12", "2025-12"),
        (" 2026-06 ", "2026-06"),
    ],
)
def test_validate_data_base_accepts_normalized_semesters(
    data_base: str,
    expected: str,
) -> None:
    assert validate_data_base(data_base) == expected


@pytest.mark.parametrize(
    "data_base",
    [
        "",
        "2025-01",
        "06/2025",
        "2025/06",
        "2025-6",
        "AAAA-MM",
    ],
)
def test_validate_data_base_rejects_invalid_values(
    data_base: str,
) -> None:
    with pytest.raises(ValueError):
        validate_data_base(data_base)


def test_output_filenames() -> None:
    assert (
        build_xml_filename("2026-06")
        == "DRO_5050_2026-06.xml"
    )
    assert (
        build_xml_filename(
            "2026-06",
            apt_for_submission=False,
        )
        == "DRO_5050_2026-06_NAO_APTO.xml"
    )
    assert (
        build_report_xlsx_filename("2026-06")
        == "Relatorio_DRO_5050_2026-06.xlsx"
    )
def test_runtime_directories_can_be_ensured() -> None:
    ensure_runtime_directories()

    assert OUTPUT_DIR.is_dir()


def test_no_required_project_path_is_missing() -> None:
    assert find_missing_project_paths() == []
