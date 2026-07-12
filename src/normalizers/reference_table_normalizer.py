"""Normalizadores específicos das tabelas auxiliares."""

from __future__ import annotations

import re
from typing import Any

from src.domain.normalization import (
    NormalizationResult,
    invalid_result,
    valid_result,
)
from src.normalizers.text_normalizer import normalize_text


_REFERENCE_NAME_PATTERN = re.compile(r"[0-9A-Za-z ]+")


def normalize_reference_name(
    value: Any,
    *,
    field_label: str,
) -> NormalizationResult[str]:
    """Normaliza nome conforme ``tipoAlphaNumerico70`` dos XSDs.

    O XSD permite somente letras ASCII, números e espaço, entre 1 e 70
    caracteres. O texto não é transliterado nem tem acentos removidos.
    """

    text_result = normalize_text(
        value,
        rule_code="NORM-TABELA-NOME-001",
        min_length=1,
        max_length=70,
        collapse_whitespace=True,
    )

    if not text_result.is_valid:
        return text_result

    normalized = text_result.normalized_value
    assert normalized is not None

    if _REFERENCE_NAME_PATTERN.fullmatch(normalized) is None:
        return invalid_result(
            original_value=value,
            rule_code="NORM-TABELA-NOME-001",
            issue_code="TBL-NOME-FMT-001",
            issue_message=(
                f"O {field_label} deve conter somente letras ASCII, "
                "números e espaços, conforme o XSD."
            ),
            serialized_value=normalized,
        )

    return valid_result(
        original_value=value,
        normalized_value=normalized,
        serialized_value=normalized,
        rule_code="NORM-TABELA-NOME-001",
        changed=text_result.changed,
    )
