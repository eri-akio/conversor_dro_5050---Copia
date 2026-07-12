"""Normalizadores reutilizáveis de identificadores da aba ``Base``.

Os identificadores são tratados como texto para preservar zeros à
esquerda. Valores numéricos são rejeitados por padrão, pois não é
possível saber se o Excel já eliminou zeros significativos.
"""

from __future__ import annotations

from collections.abc import Collection
from decimal import Decimal
import math
import re
from typing import Any, Pattern

from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
    valid_result,
)
from src.normalizers.null_normalizer import is_null_candidate


_BACEN_WITH_DESCRIPTION_PATTERN = re.compile(
    r"^\s*(?P<code>[ZIzi][0-9]+)"
    r"(?:\s*-\s*(?P<description>.+))?\s*$"
)


def normalize_identifier(
    value: Any,
    *,
    pattern: str | Pattern[str],
    min_length: int,
    max_length: int,
    rule_code: str = "NORM-ID-001",
    uppercase: bool = False,
    allow_numeric: bool = False,
    field_label: str = "identificador",
    null_issue_code: str = "ID-NULO-001",
    type_issue_code: str = "ID-TIPO-001",
    length_issue_code: str = "ID-TAMANHO-001",
    format_issue_code: str = "ID-FMT-001",
) -> NormalizationResult[str]:
    """Normaliza um identificador com padrão configurável."""

    if min_length < 0:
        raise ValueError(
            "min_length não pode ser negativo."
        )

    if max_length < min_length:
        raise ValueError(
            "max_length deve ser maior ou igual a min_length."
        )

    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code=rule_code,
            issue_code=null_issue_code,
            issue_message=(
                f"O {field_label} representa ausência."
            ),
        )

    text, type_issue = _identifier_value_to_text(
        value,
        allow_numeric=allow_numeric,
    )

    if type_issue is not None:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code=type_issue_code,
            issue_message=type_issue,
        )

    assert text is not None

    normalized = (
        text.upper()
        if uppercase
        else text
    )

    if not min_length <= len(normalized) <= max_length:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code=length_issue_code,
            issue_message=(
                f"O {field_label} deve possuir entre "
                f"{min_length} e {max_length} caracteres."
            ),
            serialized_value=normalized,
        )

    compiled_pattern = (
        re.compile(pattern)
        if isinstance(pattern, str)
        else pattern
    )

    if compiled_pattern.fullmatch(normalized) is None:
        return invalid_result(
            original_value=value,
            rule_code=rule_code,
            issue_code=format_issue_code,
            issue_message=(
                f"O {field_label} possui formato inválido."
            ),
            serialized_value=normalized,
        )

    return valid_result(
        original_value=value,
        normalized_value=normalized,
        serialized_value=normalized,
        rule_code=rule_code,
        changed=(
            not isinstance(value, str)
            or value.strip() != normalized
        ),
    )


def normalize_event_id(
    value: Any,
) -> NormalizationResult[str]:
    """Normaliza ``idEvento`` conforme os XSDs fornecidos."""

    return normalize_identifier(
        value,
        pattern=r"[0-9A-Za-z]+",
        min_length=1,
        max_length=40,
        rule_code="NORM-ID-EVENTO-001",
        field_label="idEvento",
        format_issue_code="ID-EVENTO-FMT-001",
        length_issue_code="ID-EVENTO-TAMANHO-001",
    )


def normalize_source_system_code(
    value: Any,
) -> NormalizationResult[str]:
    """Normaliza o código do sistema de origem."""

    return normalize_identifier(
        value,
        pattern=r"[0-9A-Za-z]+",
        min_length=1,
        max_length=10,
        rule_code="NORM-ID-SISTEMA-001",
        field_label="código do sistema de origem",
        format_issue_code="ID-SISTEMA-FMT-001",
        length_issue_code="ID-SISTEMA-TAMANHO-001",
    )


def normalize_origin_event_code(
    value: Any,
) -> NormalizationResult[str]:
    """Normaliza ``codigoEventoOrigem``."""

    return normalize_identifier(
        value,
        pattern=r"[0-9A-Za-z]+",
        min_length=1,
        max_length=73,
        rule_code="NORM-ID-EVENTO-ORIGEM-001",
        field_label="codigoEventoOrigem",
        format_issue_code="ID-EVENTO-ORIGEM-FMT-001",
        length_issue_code="ID-EVENTO-ORIGEM-TAMANHO-001",
    )


def normalize_internal_account_code(
    value: Any,
) -> NormalizationResult[str]:
    """Normaliza código de conta interna com 1 a 24 dígitos."""

    return normalize_identifier(
        value,
        pattern=r"[0-9]+",
        min_length=1,
        max_length=24,
        rule_code="NORM-ID-CONTA-INTERNA-001",
        field_label="código da conta interna",
        format_issue_code="ID-CONTA-INTERNA-FMT-001",
        length_issue_code="ID-CONTA-INTERNA-TAMANHO-001",
    )


def normalize_cosif_account(
    value: Any,
    *,
    allowed_lengths: Collection[int],
) -> NormalizationResult[str]:
    """Normaliza conta COSIF sem remover pontuação.

    O chamador informa os comprimentos permitidos conforme o perfil:

    - XSD 12/2020: ``{8}``;
    - XSD 06/2025: ``{8, 10}``.
    """

    normalized_lengths = tuple(
        sorted(set(allowed_lengths))
    )

    if not normalized_lengths:
        raise ValueError(
            "allowed_lengths não pode estar vazio."
        )

    if any(length < 1 for length in normalized_lengths):
        raise ValueError(
            "Os comprimentos COSIF devem ser positivos."
        )

    length_alternatives = "|".join(
        f"[0-9]{{{length}}}"
        for length in normalized_lengths
    )

    return normalize_identifier(
        value,
        pattern=rf"(?:{length_alternatives})",
        min_length=min(normalized_lengths),
        max_length=max(normalized_lengths),
        rule_code="NORM-ID-COSIF-001",
        field_label="conta COSIF",
        format_issue_code="ID-COSIF-FMT-001",
        length_issue_code="ID-COSIF-TAMANHO-001",
    )


def normalize_bacen_id(
    value: Any,
) -> NormalizationResult[str]:
    """Extrai e valida ``idBacen``, preservando a descrição."""

    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code="NORM-ID-BACEN-001",
            issue_code="ID-BACEN-NULO-001",
            issue_message="idBacen representa ausência.",
        )

    if not isinstance(value, str):
        return invalid_result(
            original_value=value,
            rule_code="NORM-ID-BACEN-001",
            issue_code="ID-BACEN-TIPO-001",
            issue_message=(
                "idBacen deve ser textual para preservar o prefixo."
            ),
        )

    text = value.strip()
    match = _BACEN_WITH_DESCRIPTION_PATTERN.fullmatch(text)

    if match is None:
        return invalid_result(
            original_value=value,
            rule_code="NORM-ID-BACEN-001",
            issue_code="ID-BACEN-FMT-001",
            issue_message=(
                "idBacen deve seguir Z + 7 dígitos ou I + 5 dígitos."
            ),
        )

    code = match.group("code").upper()
    description = match.group("description")

    if re.fullmatch(
        r"(?:Z[0-9]{7}|I[0-9]{5})",
        code,
    ) is None:
        return invalid_result(
            original_value=value,
            rule_code="NORM-ID-BACEN-001",
            issue_code="ID-BACEN-FMT-001",
            issue_message=(
                "idBacen deve seguir Z + 7 dígitos ou I + 5 dígitos."
            ),
            serialized_value=code,
            extracted_description=(
                description.strip()
                if description
                else None
            ),
        )

    clean_description = (
        description.strip()
        if description
        else None
    )

    return valid_result(
        original_value=value,
        normalized_value=code,
        serialized_value=code,
        rule_code="NORM-ID-BACEN-001",
        changed=text != code,
        extracted_description=clean_description,
    )


def _identifier_value_to_text(
    value: Any,
    *,
    allow_numeric: bool,
) -> tuple[str | None, str | None]:
    if isinstance(value, str):
        return value.strip(), None

    if isinstance(value, bool):
        return (
            None,
            "Valor booleano não é aceito como identificador.",
        )

    if not allow_numeric:
        return (
            None,
            "Identificador numérico não é aceito porque zeros à "
            "esquerda podem ter sido perdidos no Excel."
        )

    if isinstance(value, int):
        return str(value), None

    if isinstance(value, float):
        if not math.isfinite(value):
            return (
                None,
                "Identificador numérico precisa ser finito.",
            )

        if not value.is_integer():
            return (
                None,
                "Identificador numérico não pode possuir decimais.",
            )

        return str(int(value)), None

    if isinstance(value, Decimal):
        if not value.is_finite():
            return (
                None,
                "Identificador numérico precisa ser finito.",
            )

        if value != value.to_integral_value():
            return (
                None,
                "Identificador numérico não pode possuir decimais.",
            )

        return str(value.quantize(Decimal("1"))), None

    return (
        None,
        "Tipo de valor não suportado como identificador.",
    )
