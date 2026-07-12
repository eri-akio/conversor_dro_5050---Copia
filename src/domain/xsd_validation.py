"""Modelos do resultado da validação XML contra XSD."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


class XsdValidationStatus(StrEnum):
    """Situação técnica e estrutural da validação."""

    VALID = "VÁLIDO"
    INVALID = "INVÁLIDO"
    TECHNICAL_FAILURE = "FALHA TÉCNICA"


@dataclass(frozen=True, slots=True)
class XsdValidationIssue:
    """Ocorrência produzida pelo parser ou pelo XSD."""

    code: str
    severity: str
    message: str
    source: str
    blocks_apt: bool
    line: int | None = None
    column: int | None = None
    xpath: str | None = None
    filename: str | None = None
    level_name: str | None = None
    domain_name: str | None = None
    type_name: str | None = None

    @property
    def location(self) -> str | None:
        """Representação legível da localização do erro."""

        parts: list[str] = []

        if self.line is not None:
            parts.append(f"linha {self.line}")

        if self.column is not None:
            parts.append(f"coluna {self.column}")

        if self.xpath:
            parts.append(f"caminho {self.xpath}")

        return ", ".join(parts) if parts else None


@dataclass(frozen=True, slots=True)
class XsdValidationResult:
    """Resultado completo da validação pelo esquema selecionado."""

    original_xml_path: Path | None
    final_xml_path: Path | None
    xsd_path: Path
    profile_code: str
    xsd_version: str
    status: XsdValidationStatus
    profile_blocks_apt: bool
    upstream_blocks_apt: bool
    reclassified_to_not_apt: bool
    collision_index: int
    issues: tuple[XsdValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == XsdValidationStatus.VALID

    @property
    def is_invalid(self) -> bool:
        return self.status == XsdValidationStatus.INVALID

    @property
    def has_technical_failure(self) -> bool:
        return (
            self.status
            == XsdValidationStatus.TECHNICAL_FAILURE
        )

    @property
    def blocks_apt(self) -> bool:
        """XSD, perfil ou etapas anteriores impedem APTO."""

        return (
            not self.is_valid
            or self.profile_blocks_apt
            or self.upstream_blocks_apt
            or any(
                issue.blocks_apt
                for issue in self.issues
            )
        )

    @property
    def is_xsd_candidate(self) -> bool:
        """Válido no XSD e sem bloqueios já conhecidos."""

        return self.is_valid and not self.blocks_apt

    @property
    def final_filename(self) -> str | None:
        if self.final_xml_path is None:
            return None
        return self.final_xml_path.name

    @property
    def schema_errors(
        self,
    ) -> tuple[XsdValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.code == "XSD-VAL-001"
        )

    @property
    def technical_issues(
        self,
    ) -> tuple[XsdValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == "FALHA TÉCNICA"
        )

    @property
    def issue_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}

        for issue in self.issues:
            counts[issue.severity] = (
                counts.get(issue.severity, 0) + 1
            )

        return MappingProxyType(counts)
