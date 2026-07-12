"""Objetos de domínio do versionamento regulatório."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re


_YEAR_MONTH_PATTERN = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})$"
)


@dataclass(
    frozen=True,
    order=True,
    slots=True,
)
class YearMonth:
    """Ano e mês comparáveis sem depender de comparação textual."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if self.year < 1:
            raise ValueError(
                "O ano deve ser maior que zero."
            )

        if not 1 <= self.month <= 12:
            raise ValueError(
                "O mês deve estar entre 1 e 12."
            )

    @classmethod
    def parse(cls, value: str) -> "YearMonth":
        """Converte somente o formato normalizado ``AAAA-MM``."""

        text = str(value).strip()
        match = _YEAR_MONTH_PATTERN.fullmatch(text)

        if match is None:
            raise ValueError(
                "Use o formato normalizado AAAA-MM."
            )

        return cls(
            year=int(match.group("year")),
            month=int(match.group("month")),
        )

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


class VersionStatus(StrEnum):
    """Situação documental do perfil regulatório."""

    CONFIRMED = "CONFIRMADA"
    DOCUMENT_CONFLICT = "CONFLITO_DOCUMENTAL"


@dataclass(frozen=True, slots=True)
class RegulatoryVersion:
    """Combinação de instrução, XSD e vigência."""

    code: str
    start_data_base: YearMonth
    end_data_base: YearMonth | None
    instruction_version: str
    instruction_path: Path
    xsd_version: str
    xsd_path: Path
    layout_profile: str
    status: VersionStatus
    blocks_apt: bool
    conflict_codes: tuple[str, ...] = ()

    def applies_to(
        self,
        data_base: YearMonth,
    ) -> bool:
        """Confirma se a data-base pertence ao intervalo."""

        if data_base < self.start_data_base:
            return False

        if (
            self.end_data_base is not None
            and data_base > self.end_data_base
        ):
            return False

        return True

    @property
    def is_confirmed(self) -> bool:
        """Indica combinação documental confirmada."""

        return self.status == VersionStatus.CONFIRMED

    @property
    def required_paths(self) -> tuple[Path, Path]:
        """Arquivos necessários para usar o perfil."""

        return (
            self.instruction_path,
            self.xsd_path,
        )

    def missing_paths(self) -> tuple[Path, ...]:
        """Arquivos do perfil que não existem."""

        return tuple(
            path
            for path in self.required_paths
            if not path.is_file()
        )
