"""Testes do normalizador monetário com Decimal."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.normalizers.decimal_normalizer import (
    normalize_decimal,
    serialize_decimal,
)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1.427,98", Decimal("1427.98")),
        ("1427,98", Decimal("1427.98")),
        ("1427.98", Decimal("1427.98")),
        (
            "1.552.165,46",
            Decimal("1552165.46"),
        ),
        ("-1.200,00", Decimal("-1200.00")),
        (
            "1,222.11",
            Decimal("1222.11"),
        ),
        ("1,234,567", Decimal("1234567.00")),
        ("1.234.567", Decimal("1234567.00")),
        (1427, Decimal("1427.00")),
        (1427.98, Decimal("1427.98")),
        (
            Decimal("1427.980"),
            Decimal("1427.98"),
        ),
    ],
)
def test_supported_decimal_formats(
    raw_value: object,
    expected: Decimal,
) -> None:
    result = normalize_decimal(raw_value)

    assert result.is_valid
    assert result.normalized_value == expected
    assert result.serialized_value == format(
        expected,
        ".2f",
    )
    assert not isinstance(
        result.normalized_value,
        float,
    )


@pytest.mark.parametrize(
    "raw_value",
    [
        "1.222",
        "1,222",
        "1.222,111,11",
        "1,22,33",
    ],
)
def test_ambiguous_values_are_rejected(
    raw_value: str,
) -> None:
    result = normalize_decimal(raw_value)

    assert result.is_invalid
    assert result.issue_code == "DEC-AMB-001"


@pytest.mark.parametrize(
    "raw_value",
    [
        "R$ 1.200,00",
        "1 200,00",
        "1.2.34",
        "abc",
        True,
    ],
)
def test_invalid_decimal_values(
    raw_value: object,
) -> None:
    result = normalize_decimal(raw_value)

    assert result.is_invalid


def test_sign_and_scale_are_not_silently_fixed() -> None:
    negative = normalize_decimal(
        "-10,00",
        allow_negative=False,
    )
    excessive_scale = normalize_decimal(
        Decimal("10.001")
    )

    assert negative.issue_code == "DEC-SINAL-001"
    assert excessive_scale.issue_code == "DEC-ESCALA-001"


def test_integer_digit_limit() -> None:
    result = normalize_decimal(
        "12345678901234567,00",
        max_integer_digits=16,
    )

    assert result.is_invalid
    assert result.issue_code == "DEC-TAMANHO-001"


@pytest.mark.parametrize(
    "raw_value",
    [None, "", "NULL", "N/A", "-", "*"],
)
def test_absent_decimal_values(
    raw_value: object,
) -> None:
    result = normalize_decimal(raw_value)

    assert result.is_absent
    assert result.issue_code == "DEC-NULO-001"


def test_decimal_serialization() -> None:
    assert (
        serialize_decimal(Decimal("-0"))
        == "0.00"
    )
    assert (
        serialize_decimal(Decimal("1500"))
        == "1500.00"
    )
