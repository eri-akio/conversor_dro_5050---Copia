"""Testes dos normalizadores de identificadores."""

from __future__ import annotations

import pytest

from src.normalizers.identifier_normalizer import (
    normalize_bacen_id,
    normalize_cosif_account,
    normalize_event_id,
    normalize_internal_account_code,
    normalize_origin_event_code,
    normalize_source_system_code,
)


def test_bacen_code_and_name_are_separated() -> None:
    result = normalize_bacen_id(
        "Z1234567 - Banco Exemplo"
    )

    assert result.is_valid
    assert result.normalized_value == "Z1234567"
    assert result.serialized_value == "Z1234567"
    assert (
        result.extracted_description
        == "Banco Exemplo"
    )


@pytest.mark.parametrize(
    "raw_value",
    ["Z0000000", "I12345", " i12345 "],
)
def test_supported_bacen_ids(
    raw_value: str,
) -> None:
    result = normalize_bacen_id(raw_value)

    assert result.is_valid


@pytest.mark.parametrize(
    "raw_value",
    ["Z123", "A1234567", "I123456", 12345678],
)
def test_invalid_bacen_ids(
    raw_value: object,
) -> None:
    result = normalize_bacen_id(raw_value)

    assert result.is_invalid


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("IND-0001", "IND0001"),
        ("ORLD-1234", "ORLD1234"),
        ("ABC-12-XYZ", "ABC12XYZ"),
        ("IND0001", "IND0001"),
    ],
)
def test_event_id_removes_only_safe_hyphen_separators(
    raw_value: str,
    expected: str,
) -> None:
    result = normalize_event_id(raw_value)

    assert result.is_valid
    assert result.original_value == raw_value
    assert result.normalized_value == expected
    assert result.serialized_value == expected
    assert result.changed is (raw_value != expected)


@pytest.mark.parametrize(
    "raw_value",
    [
        "-IND0001",
        "IND0001-",
        "IND--0001",
        "IND@0001",
        "---",
    ],
)
def test_event_id_rejects_unsafe_or_invalid_separators(
    raw_value: str,
) -> None:
    result = normalize_event_id(raw_value)

    assert result.is_invalid
    assert result.issue_code == "ID-EVENTO-FMT-001"


def test_event_id_length_is_checked_after_separator_removal() -> None:
    valid = normalize_event_id(f"{'A' * 20}-{'B' * 20}")
    invalid = normalize_event_id(f"{'A' * 20}-{'B' * 21}")

    assert valid.is_valid
    assert len(valid.serialized_value or "") == 40
    assert invalid.is_invalid
    assert invalid.issue_code == "ID-EVENTO-TAMANHO-001"


def test_identifier_numeric_value_is_rejected() -> None:
    result = normalize_event_id(1234)

    assert result.is_invalid
    assert result.issue_code == "ID-TIPO-001"


def test_internal_account_preserves_leading_zeros() -> None:
    result = normalize_internal_account_code(
        "000000000000000000000001"
    )

    assert result.is_valid
    assert (
        result.normalized_value
        == "000000000000000000000001"
    )


@pytest.mark.parametrize(
    ("raw_value", "lengths", "is_valid"),
    [
        ("10000007", {8}, True),
        ("1000000007", {8}, False),
        ("10000007", {8, 10}, True),
        ("1000000007", {8, 10}, True),
        ("1.00.00.007", {8, 10}, False),
        (10000007, {8, 10}, False),
    ],
)
def test_cosif_depends_on_version_lengths(
    raw_value: object,
    lengths: set[int],
    is_valid: bool,
) -> None:
    result = normalize_cosif_account(
        raw_value,
        allowed_lengths=lengths,
    )

    assert result.is_valid is is_valid


def test_other_identifier_limits() -> None:
    assert normalize_source_system_code(
        "SISTTI001"
    ).is_valid
    assert not normalize_source_system_code(
        "SISTEMA00001"
    ).is_valid

    assert normalize_origin_event_code(
        "EVENTOORIGEM001"
    ).is_valid


def test_empty_cosif_lengths_are_programming_error() -> None:
    with pytest.raises(ValueError):
        normalize_cosif_account(
            "10000007",
            allowed_lengths=set(),
        )
