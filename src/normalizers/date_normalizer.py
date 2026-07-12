"""Normalizador reutilizável de datas da aba ``Base``.

Entradas aceitas:

- ``date`` e ``datetime``;
- ``DD/MM/AAAA``;
- ``AAAA-MM-DD``;
- textos com data e hora;
- serial numérico do Excel somente quando a célula possui formato
  reconhecível de data.

O valor interno retornado é ``datetime.date``. A representação para o
XML fica em ``serialized_value`` no formato ``AAAA-MM-DD``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math
import re
from typing import Any

from openpyxl.utils.datetime import from_excel

from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
    valid_result,
)
from src.normalizers.null_normalizer import is_null_candidate


RULE_CODE = "NORM-DATA-001"

_QUOTED_TEXT_PATTERN = re.compile(r'"[^"]*"')
_BRACKET_SECTION_PATTERN = re.compile(r"\[[^\]]*\]")


def normalize_date(
    value: Any,
    *,
    excel_number_format: str | None = None,
) -> NormalizationResult[date]:
    """Normaliza uma data completa sem inventar dia ou mês."""

    if is_null_candidate(value):
        return absent_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DATA-NULO-001",
            issue_message=(
                "O valor representa ausência e não contém uma data."
            ),
        )

    parsed_date: date | None = None

    if isinstance(value, datetime):
        parsed_date = value.date()

    elif isinstance(value, date):
        parsed_date = value

    elif _is_numeric(value):
        if not _looks_like_excel_date_format(excel_number_format):
            return invalid_result(
                original_value=value,
                rule_code=RULE_CODE,
                issue_code="DATA-TIPO-001",
                issue_message=(
                    "Valor numérico não foi interpretado como data "
                    "porque a célula não possui formato de data."
                ),
            )

        parsed_date = _parse_excel_serial(value)

        if parsed_date is None:
            return invalid_result(
                original_value=value,
                rule_code=RULE_CODE,
                issue_code="DATA-EXCEL-001",
                issue_message=(
                    "O serial numérico do Excel não representa uma "
                    "data válida."
                ),
            )

    elif isinstance(value, str):
        parsed_date = _parse_date_text(value)

        if parsed_date is None:
            return invalid_result(
                original_value=value,
                rule_code=RULE_CODE,
                issue_code="DATA-FMT-001",
                issue_message=(
                    "Data inválida. Use DD/MM/AAAA, AAAA-MM-DD ou "
                    "uma data/hora reconhecida."
                ),
            )

    else:
        return invalid_result(
            original_value=value,
            rule_code=RULE_CODE,
            issue_code="DATA-TIPO-001",
            issue_message=(
                "Tipo de valor não suportado para normalização de data."
            ),
        )

    serialized = parsed_date.isoformat()

    return valid_result(
        original_value=value,
        normalized_value=parsed_date,
        serialized_value=serialized,
        rule_code=RULE_CODE,
        changed=not (
            isinstance(value, str)
            and value.strip() == serialized
        ),
    )


def serialize_date(value: date) -> str:
    """Serializa uma data já validada para o XML."""

    return value.isoformat()


def _parse_date_text(value: str) -> date | None:
    text = value.strip()

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
    )

    for format_string in formats:
        try:
            return datetime.strptime(
                text,
                format_string,
            ).date()
        except ValueError:
            continue

    iso_text = (
        text[:-1] + "+00:00"
        if text.endswith("Z")
        else text
    )

    try:
        return datetime.fromisoformat(iso_text).date()
    except ValueError:
        return None


def _parse_excel_serial(value: Any) -> date | None:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(numeric_value):
        return None

    try:
        converted = from_excel(numeric_value)
    except (TypeError, ValueError, OverflowError):
        return None

    if isinstance(converted, datetime):
        return converted.date()

    if isinstance(converted, date):
        return converted

    return None


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    return isinstance(
        value,
        (int, float, Decimal),
    )


def _looks_like_excel_date_format(
    number_format: str | None,
) -> bool:
    if not number_format:
        return False

    cleaned = number_format.lower()
    cleaned = _QUOTED_TEXT_PATTERN.sub("", cleaned)
    cleaned = _BRACKET_SECTION_PATTERN.sub("", cleaned)
    cleaned = cleaned.replace("\\", "")

    return (
        "y" in cleaned
        and (
            "m" in cleaned
            or "d" in cleaned
        )
    )
