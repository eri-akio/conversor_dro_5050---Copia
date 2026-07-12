"""Normalizadores reutilizáveis de campos com domínio."""

from __future__ import annotations

from collections.abc import Collection
from decimal import Decimal
import math
import re
from typing import Any

from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
    valid_result,
)
from src.normalizers.null_normalizer import is_null_candidate


RULE_CODE = "NORM-DOMINIO-001"

_CODE_DESCRIPTION_PATTERN = re.compile(
    r"^\s*(?P<code>[A-Za-z0-9_]+)"
    r"\s*-\s*(?P<description>.+?)\s*$"
)
_SIMPLE_CODE_PATTERN = re.compile(
    r"^[A-Za-z0-9_]+$"
)


def normalize_domain(
    value: Any,
    *,
    allowed_codes: Collection[str],
    uppercase: bool = True,
) -> NormalizationResult[str]:
    """Extrai o código e valida contra o domínio informado."""

    if not allowed_codes:
        raise ValueError(
            "allowed_codes não pode estar vazio."
        )

    prepared = _prepare_domain_value(
        value,
        uppercase=uppercase,
        rule_code=RULE_CODE,
    )

    if not prepared.is_valid:
        return prepared

    normalized_code = prepared.normalized_value
    assert normalized_code is not None

    canonical_codes = {
        (
            str(code).strip().upper()
            if uppercase
            else str(code).strip()
        )
        for code in allowed_codes
    }

    if normalized_code not in canonical_codes:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DOM-COD-001",
            issue_message=(
                "Código fora do domínio permitido para a versão."
            ),
            serialized_value=normalized_code,
            extracted_description=(
                prepared.extracted_description
            ),
        )

    return prepared


def extract_unconfirmed_domain_code(
    value: Any,
    *,
    uppercase: bool = True,
) -> NormalizationResult[str]:
    """Extrai um código sem afirmar que o domínio está validado."""

    return _prepare_domain_value(
        value,
        uppercase=uppercase,
        rule_code="NORM-DOMINIO-EXTRACAO-001",
    )


def _prepare_domain_value(
    value: Any,
    *,
    uppercase: bool,
    rule_code: str,
) -> NormalizationResult[str]:
    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="DOM-NULO-001",
            issue_message=(
                "O valor representa ausência e não contém um código."
            ),
        )

    text, type_issue = _domain_value_to_text(value)

    if type_issue is not None:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="DOM-TIPO-001",
            issue_message=type_issue,
        )

    assert text is not None

    match = _CODE_DESCRIPTION_PATTERN.fullmatch(text)

    if match is not None:
        raw_code = match.group("code")
        description = match.group("description").strip()
    else:
        raw_code = text
        description = None

    if _SIMPLE_CODE_PATTERN.fullmatch(raw_code) is None:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code="DOM-FMT-001",
            issue_message=(
                "O código de domínio possui formato inválido."
            ),
            extracted_description=description,
        )

    normalized_code = (
        raw_code.upper()
        if uppercase
        else raw_code
    )

    return valid_result(
        original_value=value,
        normalized_value=normalized_code,
        serialized_value=normalized_code,
        rule_code=rule_code,
        changed=(
            text != normalized_code
            or description is not None
        ),
        extracted_description=description,
    )


def _domain_value_to_text(
    value: Any,
) -> tuple[str | None, str | None]:
    if isinstance(value, str):
        return value.strip(), None

    if isinstance(value, bool):
        return (
            None,
            "Valor booleano não é aceito como código de domínio.",
        )

    if isinstance(value, int):
        return str(value), None

    if isinstance(value, float):
        if not math.isfinite(value):
            return (
                None,
                "Código numérico precisa ser finito.",
            )

        if not value.is_integer():
            return (
                None,
                "Código numérico não pode possuir casas decimais.",
            )

        return str(int(value)), None

    if isinstance(value, Decimal):
        if not value.is_finite():
            return (
                None,
                "Código numérico precisa ser finito.",
            )

        if value != value.to_integral_value():
            return (
                None,
                "Código numérico não pode possuir casas decimais.",
            )

        return str(
            value.quantize(Decimal("1"))
        ), None

    return (
        None,
        "Tipo de valor não suportado como código de domínio.",
    )
