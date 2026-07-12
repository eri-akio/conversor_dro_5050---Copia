"""Identificação controlada de candidatos a ausência.

A função deste módulo não decide obrigatoriedade. Ela apenas reconhece
representações que o projeto definiu como candidatas a nulo.

``NA`` não é tratado automaticamente como nulo, pois pode ser um
domínio regulatório válido em outros campos do Documento 5050.
"""

from __future__ import annotations

from decimal import Decimal
import math
from typing import Any


NULL_TEXT_MARKERS: frozenset[str] = frozenset(
    {
        "",
        "NULL",
        "N/A",
        "-",
        "*",
    }
)


def is_null_candidate(value: Any) -> bool:
    """Retorna verdadeiro quando o valor representa ausência provável."""

    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().upper() in NULL_TEXT_MARKERS

    if isinstance(value, Decimal):
        return value.is_nan()

    if isinstance(value, float):
        return math.isnan(value)

    return False
