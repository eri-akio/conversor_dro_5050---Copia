"""Testes do reconhecimento de candidatos a ausência."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.normalizers.null_normalizer import is_null_candidate


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        "NULL",
        " null ",
        "N/A",
        "-",
        "*",
        float("nan"),
        Decimal("NaN"),
    ],
)
def test_null_candidates_are_recognized(value: object) -> None:
    assert is_null_candidate(value)


@pytest.mark.parametrize(
    "value",
    [
        "NA",
        "0",
        0,
        False,
        "I",
        "S",
        "2026-06",
    ],
)
def test_valid_values_are_not_treated_as_null(
    value: object,
) -> None:
    assert not is_null_candidate(value)
