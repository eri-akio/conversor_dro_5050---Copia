"""Normalização controlada de campos textuais."""

from __future__ import annotations

from typing import Any

from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
    valid_result,
)
from src.normalizers.null_normalizer import is_null_candidate


def normalize_text(
    value: Any,
    *,
    rule_code: str = "NORM-TEXTO-001",
    min_length: int = 1,
    max_length: int | None = None,
    collapse_whitespace: bool = True,
) -> NormalizationResult[str]:
    """Normaliza texto sem truncar ou inventar conteúdo."""

    if min_length < 0:
        raise ValueError(
            "min_length não pode ser negativo."
        )

    if (
        max_length is not None
        and max_length < min_length
    ):
        raise ValueError(
            "max_length deve ser maior ou igual a min_length."
        )

    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="TEXTO-NULO-001",
            issue_message=(
                "O valor representa ausência e não contém texto."
            ),
        )

    if not isinstance(value, str):
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="TEXTO-TIPO-001",
            issue_message=(
                "O valor textual deve ser informado como texto."
            ),
        )

    stripped = value.strip()
    normalized = (
        " ".join(stripped.split())
        if collapse_whitespace
        else stripped
    )

    if len(normalized) < min_length:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="TEXTO-TAMANHO-001",
            issue_message=(
                f"O texto deve possuir ao menos {min_length} "
                "caractere(s)."
            ),
            serialized_value=normalized,
        )

    if (
        max_length is not None
        and len(normalized) > max_length
    ):
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="TEXTO-TAMANHO-001",
            issue_message=(
                f"O texto ultrapassa o limite de "
                f"{max_length} caracteres."
            ),
            serialized_value=normalized,
        )

    return valid_result(
        original_value=value,
        normalized_value=normalized,
        serialized_value=normalized,
        rule_code=rule_code,
        changed=value != normalized,
    )
