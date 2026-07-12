"""Testes do normalizador textual."""

from __future__ import annotations

import pytest

from src.normalizers.text_normalizer import normalize_text


def test_text_is_trimmed_and_collapsed() -> None:
    result = normalize_text(
        "  Evento   com\n espaços  ",
        max_length=200,
    )

    assert result.is_valid
    assert result.normalized_value == "Evento com espaços"
    assert result.changed


def test_accents_are_preserved() -> None:
    result = normalize_text(
        "Descrição válida",
        max_length=200,
    )

    assert result.is_valid
    assert result.normalized_value == "Descrição válida"


def test_text_is_not_silently_truncated() -> None:
    result = normalize_text(
        "A" * 201,
        max_length=200,
    )

    assert result.is_invalid
    assert result.issue_code == "TEXTO-TAMANHO-001"


@pytest.mark.parametrize(
    "value",
    [None, "", "NULL", "N/A", "-", "*"],
)
def test_null_candidates_are_absent(
    value: object,
) -> None:
    assert normalize_text(value).is_absent


def test_non_text_value_is_invalid() -> None:
    result = normalize_text(123)

    assert result.is_invalid
    assert result.issue_code == "TEXTO-TIPO-001"
