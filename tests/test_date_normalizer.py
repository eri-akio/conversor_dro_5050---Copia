"""Testes do normalizador reutilizável de datas."""

from __future__ import annotations

from datetime import date, datetime

from openpyxl.utils.datetime import to_excel
import pytest

from src.normalizers.date_normalizer import normalize_date


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("30/06/2026", date(2026, 6, 30)),
        ("2026-06-30", date(2026, 6, 30)),
        (
            "30/06/2026 10:20:30",
            date(2026, 6, 30),
        ),
        (
            "2026-06-30 10:20:30",
            date(2026, 6, 30),
        ),
        (
            "2026-06-30T10:20:30",
            date(2026, 6, 30),
        ),
        (
            "2026-06-30T10:20:30-03:00",
            date(2026, 6, 30),
        ),
        (
            date(2026, 6, 30),
            date(2026, 6, 30),
        ),
        (
            datetime(2026, 6, 30, 10, 20),
            date(2026, 6, 30),
        ),
    ],
)
def test_supported_dates(
    raw_value: object,
    expected: date,
) -> None:
    result = normalize_date(raw_value)

    assert result.is_valid
    assert result.normalized_value == expected
    assert result.serialized_value == expected.isoformat()


def test_excel_serial_requires_date_format() -> None:
    serial = to_excel(date(2026, 6, 30))

    valid = normalize_date(
        serial,
        excel_number_format="dd/mm/yyyy",
    )
    invalid = normalize_date(serial)

    assert valid.is_valid
    assert valid.serialized_value == "2026-06-30"

    assert invalid.is_invalid
    assert invalid.issue_code == "DATA-TIPO-001"


@pytest.mark.parametrize(
    "raw_value",
    [
        "31/02/2026",
        "2026-02-30",
        "texto",
        object(),
        True,
    ],
)
def test_invalid_dates(raw_value: object) -> None:
    result = normalize_date(raw_value)

    assert result.is_invalid


@pytest.mark.parametrize(
    "raw_value",
    [None, "", "NULL", "N/A", "-", "*"],
)
def test_absent_dates(raw_value: object) -> None:
    result = normalize_date(raw_value)

    assert result.is_absent
    assert result.issue_code == "DATA-NULO-001"
