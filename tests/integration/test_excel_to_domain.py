"""Integração da leitura física do Excel até os objetos de domínio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.domain.conversion import ConversionStage
from src.mappers import group_base_rows
from src.readers import read_and_normalize_base, read_excel
from src.services import convert_excel
from src.services.version_resolver import resolve_version
from src.validators import validate_base_rows

from .workbook_factory import create_workbook, make_row, set_formula


def _normalize_and_group(path: Path):
    profile = resolve_version("2026-06").profile
    assert profile is not None
    normalization = read_and_normalize_base(read_excel(path), profile)
    validation = validate_base_rows(normalization, profile)
    return normalization, group_base_rows(normalization, validation)


def test_typed_cells_reach_domain_with_source_traceability(
    tmp_path: Path,
) -> None:
    path = create_workbook(
        tmp_path / "typed.xlsx",
        rows=(
            make_row(accounting_loss=1000),
            make_row(accounting_loss=800),
            make_row(accounting_loss=500),
        ),
    )

    normalization, grouping = _normalize_and_group(path)

    assert normalization.is_valid
    assert normalization.row_count == 3
    assert normalization.rows[0].row_number == 2
    assert normalization.rows[0].get_value("dataOcorrencia") == date(
        2026, 3, 15
    )
    assert normalization.rows[0].get_value(
        "valorPerdaEfetiva"
    ) == Decimal("1000.00")
    assert grouping.event_count == 1
    assert grouping.events[0].row_numbers == (2, 3, 4)
    assert len(grouping.events[0].accountings) == 3


@pytest.mark.parametrize(
    "raw_value",
    [2300, 2300.0, "2300,00", "2.300,00", "R$ 2.300,00"],
)
def test_supported_monetary_formats_have_one_domain_value(
    tmp_path: Path,
    raw_value: int | float | str,
) -> None:
    path = create_workbook(
        tmp_path / "money.xlsx",
        rows=(make_row(overrides={"valorPerdaEfetiva": raw_value}),),
    )

    normalization, _ = _normalize_and_group(path)

    assert normalization.rows[0].get_value(
        "valorPerdaEfetiva"
    ) == Decimal("2300.00")


@pytest.mark.parametrize(
    ("column_name", "raw_value", "expected_code"),
    [
        ("valorPerdaEfetiva", "100,123", "DEC-ESCALA-001"),
        ("dataOcorrencia", "31/02/2026", "DATA-FMT-001"),
        ("categoriaNivel1", "9", "DOM-COD-001"),
    ],
)
def test_invalid_excel_values_stop_before_domain_build(
    tmp_path: Path,
    column_name: str,
    raw_value: str,
    expected_code: str,
) -> None:
    path = create_workbook(
        tmp_path / f"invalid_{column_name}.xlsx",
        rows=(make_row(overrides={column_name: raw_value}),),
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    normalization = result.output(ConversionStage.NORMALIZE_BASE)

    assert not normalization.is_valid
    assert expected_code in {issue.code for issue in normalization.issues}
    assert result.output(ConversionStage.BUILD_DOCUMENT) is None
    assert not result.has_technical_failure


def test_monetary_formula_with_cache_is_normalized_and_traced(
    tmp_path: Path,
) -> None:
    path = create_workbook(
        tmp_path / "formula_cache.xlsx",
        rows=(make_row(),),
    )
    set_formula(
        path,
        column_name="valorPerdaEfetiva",
        formula="=2000+300",
        cached_value="2300",
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    normalization = result.output(ConversionStage.NORMALIZE_BASE)

    assert normalization.rows[0].get_value(
        "valorPerdaEfetiva"
    ) == Decimal("2300.00")
    assert "BASE-NORM-FORMULA-AVISO-001" in {
        issue.code for issue in normalization.issues
    }


@pytest.mark.parametrize(
    ("column_name", "formula", "cached_value", "cached_type", "code"),
    [
        (
            "idEvento",
            '=CONCAT("IND","0001")',
            "IND0001",
            "str",
            "BASE-NORM-FORMULA-ID-001",
        ),
        (
            "valorPerdaEfetiva",
            "=2000+300",
            None,
            None,
            "BASE-NORM-FORMULA-SEM-RESULTADO-001",
        ),
    ],
)
def test_formula_policy_rejects_identifier_and_missing_cache(
    tmp_path: Path,
    column_name: str,
    formula: str,
    cached_value: str | None,
    cached_type: str | None,
    code: str,
) -> None:
    path = create_workbook(
        tmp_path / f"formula_{column_name}.xlsx",
        rows=(make_row(),),
    )
    set_formula(
        path,
        column_name=column_name,
        formula=formula,
        cached_value=cached_value,
        cached_type=cached_type,
    )

    result = convert_excel(path, output_dir=tmp_path / "output")
    normalization = result.output(ConversionStage.NORMALIZE_BASE)

    assert not normalization.is_valid
    assert code in {issue.code for issue in normalization.blocking_issues}
