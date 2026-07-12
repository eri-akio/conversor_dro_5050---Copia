"""Objetos de resultado da geração do XML."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class XmlGenerationMode(StrEnum):
    """Finalidade do arquivo gerado nesta etapa."""

    CANDIDATE = "CANDIDATO_A_VALIDACAO"
    DIAGNOSTIC = "DIAGNOSTICO_NAO_APTO"


@dataclass(frozen=True, slots=True)
class XmlElementCounts:
    """Quantidade dos elementos de negócio serializados."""

    individualized_events: int
    probabilities: int
    accountings: int
    consolidated_events: int
    source_systems: int
    internal_accounts: int

    def as_mapping(self) -> Mapping[str, int]:
        return MappingProxyType(
            {
                "eventosIndividualizados": (
                    self.individualized_events
                ),
                "probabilidadesPerdas": (
                    self.probabilities
                ),
                "contabilizacoes": self.accountings,
                "eventosConsolidados": (
                    self.consolidated_events
                ),
                "sistemasOrigem": self.source_systems,
                "contasSubtitulosInternos": (
                    self.internal_accounts
                ),
            }
        )


@dataclass(frozen=True, slots=True)
class XmlGenerationIssue:
    """Ocorrência específica da geração ou gravação do XML."""

    code: str
    severity: str
    message: str
    source: str
    blocks_apt: bool
    details: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class XmlGenerationResult:
    """Resultado da tentativa de gerar e gravar o XML."""

    output_path: Path | None
    requested_filename: str | None
    mode: XmlGenerationMode
    bytes_written: int
    collision_index: int
    well_formed: bool
    element_counts: XmlElementCounts
    build_issue_codes: tuple[str, ...]
    issues: tuple[XmlGenerationIssue, ...]

    @property
    def is_generated(self) -> bool:
        return (
            self.output_path is not None
            and self.output_path.is_file()
            and self.bytes_written > 0
        )

    @property
    def is_diagnostic(self) -> bool:
        return self.mode == XmlGenerationMode.DIAGNOSTIC

    @property
    def is_candidate(self) -> bool:
        return self.mode == XmlGenerationMode.CANDIDATE

    @property
    def actual_filename(self) -> str | None:
        if self.output_path is None:
            return None
        return self.output_path.name

    @property
    def blocks_apt(self) -> bool:
        return (
            self.is_diagnostic
            or any(
                issue.blocks_apt
                for issue in self.issues
            )
        )
