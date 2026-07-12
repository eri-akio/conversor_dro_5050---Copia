"""Objetos compartilhados pelos normalizadores reutilizáveis.

Os normalizadores da aba ``Base`` precisam retornar mais do que o valor
convertido. O relatório final também precisará saber:

- o valor original;
- o valor normalizado;
- a representação usada no XML;
- a regra aplicada;
- se houve alteração;
- se o valor está válido, ausente ou inválido;
- a descrição separada de códigos como ``8 - Descrição``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, TypeVar


T = TypeVar("T")


class NormalizationStatus(StrEnum):
    """Estado técnico de uma tentativa de normalização."""

    VALID = "VALID"
    ABSENT = "ABSENT"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class NormalizationResult(Generic[T]):
    """Resultado rastreável de um normalizador."""

    status: NormalizationStatus
    original_value: Any
    normalized_value: T | None
    serialized_value: str | None
    rule_code: str
    changed: bool
    extracted_description: str | None = None
    issue_code: str | None = None
    issue_message: str | None = None

    @property
    def is_valid(self) -> bool:
        """Verdadeiro quando o valor foi normalizado com sucesso."""

        return self.status == NormalizationStatus.VALID

    @property
    def is_absent(self) -> bool:
        """Verdadeiro quando o valor representa ausência."""

        return self.status == NormalizationStatus.ABSENT

    @property
    def is_invalid(self) -> bool:
        """Verdadeiro quando o valor não pode ser normalizado."""

        return self.status == NormalizationStatus.INVALID


def valid_result(
    *,
    original_value: Any,
    normalized_value: T,
    serialized_value: str,
    rule_code: str,
    changed: bool,
    extracted_description: str | None = None,
) -> NormalizationResult[T]:
    """Cria um resultado válido."""

    return NormalizationResult(
        status=NormalizationStatus.VALID,
        original_value=original_value,
        normalized_value=normalized_value,
        serialized_value=serialized_value,
        rule_code=rule_code,
        changed=changed,
        extracted_description=extracted_description,
    )


def absent_result(
    *,
    original_value: Any,
    rule_code: str,
    issue_code: str,
    issue_message: str,
) -> NormalizationResult[T]:
    """Cria um resultado de ausência sem decidir obrigatoriedade."""

    return NormalizationResult(
        status=NormalizationStatus.ABSENT,
        original_value=original_value,
        normalized_value=None,
        serialized_value=None,
        rule_code=rule_code,
        changed=True,
        issue_code=issue_code,
        issue_message=issue_message,
    )


def invalid_result(
    *,
    original_value: Any,
    rule_code: str,
    issue_code: str,
    issue_message: str,
    serialized_value: str | None = None,
    extracted_description: str | None = None,
) -> NormalizationResult[T]:
    """Cria um resultado inválido."""

    return NormalizationResult(
        status=NormalizationStatus.INVALID,
        original_value=original_value,
        normalized_value=None,
        serialized_value=serialized_value,
        rule_code=rule_code,
        changed=True,
        extracted_description=extracted_description,
        issue_code=issue_code,
        issue_message=issue_message,
    )
