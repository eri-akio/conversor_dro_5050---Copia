"""Testes do normalizador de domínios."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.normalizers.domain_normalizer import normalize_domain


def test_code_and_description_are_separated() -> None:
    result = normalize_domain(
        "8 - Falhas na execução",
        allowed_codes={
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
        },
    )

    assert result.is_valid
    assert result.normalized_value == "8"
    assert result.serialized_value == "8"
    assert (
        result.extracted_description
        == "Falhas na execução"
    )
    assert result.changed


def test_alphabetic_code_is_uppercased() -> None:
    result = normalize_domain(
        "tra - Trabalhista",
        allowed_codes={"TRI", "TRA", "CIV", "NA"},
    )

    assert result.is_valid
    assert result.normalized_value == "TRA"
    assert result.extracted_description == "Trabalhista"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("NA", "NA"),
        (8, "8"),
        (8.0, "8"),
        (Decimal("8"), "8"),
    ],
)
def test_direct_codes(
    raw_value: object,
    expected: str,
) -> None:
    result = normalize_domain(
        raw_value,
        allowed_codes={"8", "NA"},
    )

    assert result.is_valid
    assert result.normalized_value == expected


def test_invalid_code_is_rejected() -> None:
    result = normalize_domain(
        "9 - Código inexistente",
        allowed_codes={"1", "2", "3"},
    )

    assert result.is_invalid
    assert result.issue_code == "DOM-COD-001"
    assert (
        result.extracted_description
        == "Código inexistente"
    )


def test_na_and_n_slash_a_have_different_meanings() -> None:
    valid_na = normalize_domain(
        "NA",
        allowed_codes={"NA"},
    )
    absent_n_slash_a = normalize_domain(
        "N/A",
        allowed_codes={"NA"},
    )

    assert valid_na.is_valid
    assert absent_n_slash_a.is_absent


def test_empty_domain_configuration_is_programming_error() -> None:
    with pytest.raises(ValueError):
        normalize_domain(
            "1",
            allowed_codes=set(),
        )
