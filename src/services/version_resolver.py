"""Seleção automática da instrução e do XSD pela ``dataBase``.

A matriz implementada reproduz a documentação aprovada na etapa 1.1:

- 2020-12 a 2024-12:
  instruções 12/2020 + XSD 12/2020;
- 2025-06 a 2026-06:
  instruções 12/2020 + XSD 06/2025;
- 2026-12 em diante:
  instruções 12/2026 + XSD 06/2025 disponível, com conflito
  documental impeditivo para o status APTO.

O serviço não testa vários XSDs para escolher aquele que aceita o XML.
A seleção ocorre exclusivamente pela data-base.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.config import (
    INSTRUCTION_2020_PATH,
    INSTRUCTION_2026_PATH,
    XSD_2020_PATH,
    XSD_2025_PATH,
)
from src.domain.document_header import DocumentHeader
from src.domain.regulatory_version import (
    RegulatoryVersion,
    VersionStatus,
    YearMonth,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_TECHNICAL_FAILURE = "FALHA TÉCNICA"
SEVERITY_INFORMATION = "INFORMAÇÃO"


VERSION_PROFILES: tuple[RegulatoryVersion, ...] = (
    RegulatoryVersion(
        code="DRO_2020_12",
        start_data_base=YearMonth(2020, 12),
        end_data_base=YearMonth(2024, 12),
        instruction_version="12/2020",
        instruction_path=INSTRUCTION_2020_PATH,
        xsd_version="12/2020",
        xsd_path=XSD_2020_PATH,
        layout_profile="LEGADO_ORIGINAL",
        status=VersionStatus.CONFIRMED,
        blocks_apt=False,
    ),
    RegulatoryVersion(
        code="DRO_2025_06",
        start_data_base=YearMonth(2025, 6),
        end_data_base=YearMonth(2026, 6),
        instruction_version="12/2020",
        instruction_path=INSTRUCTION_2020_PATH,
        xsd_version="06/2025",
        xsd_path=XSD_2025_PATH,
        layout_profile="LEGADO_COSIF_8_OU_10",
        status=VersionStatus.CONFIRMED,
        blocks_apt=False,
    ),
    RegulatoryVersion(
        code="DRO_2026_12_PRESUMIDA",
        start_data_base=YearMonth(2026, 12),
        end_data_base=None,
        instruction_version="12/2026",
        instruction_path=INSTRUCTION_2026_PATH,
        xsd_version="06/2025_DISPONIVEL",
        xsd_path=XSD_2025_PATH,
        layout_profile="NOVO_PRESUMIDO",
        status=VersionStatus.DOCUMENT_CONFLICT,
        blocks_apt=True,
        conflict_codes=(
            "CONF-001",
            "VER-001",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class VersionSelectionIssue:
    """Ocorrência produzida pela seleção de versão."""

    code: str
    severity: str
    message: str
    blocks_apt: bool
    dependency: str | None = None
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class VersionSelectionResult:
    """Resultado da resolução regulatória."""

    requested_data_base: str
    parsed_data_base: YearMonth | None
    profile: RegulatoryVersion | None
    issues: tuple[VersionSelectionIssue, ...]

    @property
    def is_resolved(self) -> bool:
        """Existe perfil selecionado para a data-base."""

        return self.profile is not None

    @property
    def has_technical_failure(self) -> bool:
        """Algum arquivo necessário está ausente."""

        return any(
            issue.severity
            == SEVERITY_TECHNICAL_FAILURE
            for issue in self.issues
        )

    @property
    def blocks_apt(self) -> bool:
        """A execução não pode terminar como APTO."""

        profile_blocks = (
            self.profile.blocks_apt
            if self.profile is not None
            else True
        )

        return profile_blocks or any(
            issue.blocks_apt
            for issue in self.issues
        )

    @property
    def can_continue_diagnostic(self) -> bool:
        """É possível seguir para geração diagnóstica."""

        return (
            self.profile is not None
            and not self.has_technical_failure
        )

    @property
    def is_confirmed(self) -> bool:
        """Perfil confirmado e sem bloqueio documental."""

        return (
            self.profile is not None
            and self.profile.is_confirmed
            and not self.blocks_apt
            and not self.has_technical_failure
        )


class VersionResolver:
    """Resolve a versão exclusivamente pela data-base."""

    def __init__(
        self,
        profiles: Iterable[RegulatoryVersion] = (
            VERSION_PROFILES
        ),
    ) -> None:
        self.profiles = tuple(profiles)
        self._validate_catalog(self.profiles)

    def resolve(
        self,
        source: DocumentHeader | str,
    ) -> VersionSelectionResult:
        """Seleciona instrução e XSD sem tentativa por validação."""

        requested_data_base = (
            source.data_base
            if isinstance(source, DocumentHeader)
            else str(source).strip()
        )

        parsed, parse_issue = self._parse_data_base(
            requested_data_base
        )

        if parse_issue is not None:
            return VersionSelectionResult(
                requested_data_base=requested_data_base,
                parsed_data_base=None,
                profile=None,
                issues=(parse_issue,),
            )

        assert parsed is not None

        profile = next(
            (
                candidate
                for candidate in self.profiles
                if candidate.applies_to(parsed)
            ),
            None,
        )

        if profile is None:
            return VersionSelectionResult(
                requested_data_base=requested_data_base,
                parsed_data_base=parsed,
                profile=None,
                issues=(
                    VersionSelectionIssue(
                        code="VER-SEL-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Nenhum perfil regulatório foi "
                            "localizado para a dataBase."
                        ),
                        blocks_apt=True,
                    ),
                ),
            )

        issues: list[VersionSelectionIssue] = []
        issues.extend(
            self._validate_profile_files(profile)
        )

        if (
            profile.status
            == VersionStatus.DOCUMENT_CONFLICT
        ):
            issues.append(
                VersionSelectionIssue(
                    code="VER-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "As instruções 12/2026 exigem campos "
                        "e blocos não previstos no XSD "
                        "06/2025 fornecido. A seleção foi "
                        "realizada para diagnóstico, mas o "
                        "resultado não poderá ser APTO."
                    ),
                    blocks_apt=True,
                    dependency=(
                        "XSD compatível com as instruções "
                        "12/2026"
                    ),
                    path=profile.xsd_path,
                )
            )

        if not issues:
            issues.append(
                VersionSelectionIssue(
                    code="VER-INFO-001",
                    severity=SEVERITY_INFORMATION,
                    message=(
                        "Instrução e XSD selecionados "
                        "automaticamente pela dataBase."
                    ),
                    blocks_apt=False,
                )
            )

        return VersionSelectionResult(
            requested_data_base=requested_data_base,
            parsed_data_base=parsed,
            profile=profile,
            issues=tuple(issues),
        )

    @staticmethod
    def _parse_data_base(
        value: str,
    ) -> tuple[
        YearMonth | None,
        VersionSelectionIssue | None,
    ]:
        try:
            parsed = YearMonth.parse(value)
        except ValueError:
            return (
                None,
                VersionSelectionIssue(
                    code="VER-DATA-003",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "dataBase inválida para seleção. "
                        "Use o formato normalizado AAAA-MM."
                    ),
                    blocks_apt=True,
                ),
            )

        if parsed.month not in {6, 12}:
            return (
                None,
                VersionSelectionIssue(
                    code="VER-DATA-002",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "A dataBase deve usar o mês 06 ou 12."
                    ),
                    blocks_apt=True,
                ),
            )

        if parsed < YearMonth(2020, 12):
            return (
                None,
                VersionSelectionIssue(
                    code="VER-DATA-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "A dataBase é anterior ao primeiro "
                        "perfil fornecido, iniciado em 2020-12."
                    ),
                    blocks_apt=True,
                ),
            )

        return parsed, None

    @staticmethod
    def _validate_profile_files(
        profile: RegulatoryVersion,
    ) -> list[VersionSelectionIssue]:
        issues: list[VersionSelectionIssue] = []

        for missing_path in profile.missing_paths():
            issues.append(
                VersionSelectionIssue(
                    code="VER-ARQ-001",
                    severity=SEVERITY_TECHNICAL_FAILURE,
                    message=(
                        "Arquivo regulatório necessário "
                        "não foi encontrado."
                    ),
                    blocks_apt=True,
                    path=missing_path,
                )
            )

        return issues

    @staticmethod
    def _validate_catalog(
        profiles: tuple[RegulatoryVersion, ...],
    ) -> None:
        """Impede intervalos sobrepostos ou catálogo vazio."""

        if not profiles:
            raise ValueError(
                "O catálogo de versões não pode estar vazio."
            )

        ordered = tuple(
            sorted(
                profiles,
                key=lambda profile: (
                    profile.start_data_base
                ),
            )
        )

        if ordered != profiles:
            raise ValueError(
                "Os perfis devem estar ordenados por vigência."
            )

        for current, following in zip(
            profiles,
            profiles[1:],
            strict=False,
        ):
            if current.end_data_base is None:
                raise ValueError(
                    "Somente o último perfil pode não ter fim."
                )

            if (
                following.start_data_base
                <= current.end_data_base
            ):
                raise ValueError(
                    "Os perfis possuem vigências sobrepostas."
                )


def resolve_version(
    source: DocumentHeader | str,
) -> VersionSelectionResult:
    """Atalho funcional para o resolvedor padrão."""

    return VersionResolver().resolve(source)
