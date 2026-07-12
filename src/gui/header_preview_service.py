"""Leitura segura do cabeçalho para exibição na interface."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.gui.models import (
    HeaderPreviewIssue,
    HeaderPreviewResult,
)
from src.normalizers.header_normalizer import (
    normalize_header,
)
from src.readers import (
    read_excel,
    read_header,
    validate_header_initial,
)
from src.services.version_resolver import (
    resolve_version,
)


class HeaderPreviewService:
    """Executa somente as etapas necessárias para mostrar o cabeçalho."""

    def preview(
        self,
        input_path: str | Path,
    ) -> HeaderPreviewResult:
        path = Path(
            input_path
        ).expanduser().resolve()

        excel = read_excel(path)
        raw_header = read_header(excel)
        initial = validate_header_initial(
            raw_header
        )

        initial_issues = tuple(
            HeaderPreviewIssue(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                field_name=issue.field_name,
                value=issue.raw_value,
            )
            for issue in initial.issues
        )

        if not initial.is_valid:
            return HeaderPreviewResult(
                input_path=path,
                is_valid=False,
                header_values=MappingProxyType(
                    self._raw_values(raw_header)
                ),
                profile_code=None,
                instruction_version=None,
                xsd_version=None,
                xsd_path=None,
                version_status=(
                    "CABEÇALHO INVÁLIDO"
                ),
                blocks_apt=True,
                issues=initial_issues,
            )

        normalized = normalize_header(
            raw_header
        )
        normalization_issues = tuple(
            HeaderPreviewIssue(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                field_name=issue.field_name,
                value=issue.original_value,
            )
            for issue in normalized.issues
        )

        if (
            not normalized.is_valid
            or normalized.header is None
        ):
            values = {
                key: (
                    "" if value is None else str(value)
                )
                for key, value in (
                    normalized
                    .normalized_values
                    .items()
                )
            }
            return HeaderPreviewResult(
                input_path=path,
                is_valid=False,
                header_values=MappingProxyType(
                    values
                ),
                profile_code=None,
                instruction_version=None,
                xsd_version=None,
                xsd_path=None,
                version_status=(
                    "NORMALIZAÇÃO INVÁLIDA"
                ),
                blocks_apt=True,
                issues=(
                    *initial_issues,
                    *normalization_issues,
                ),
            )

        selection = resolve_version(
            normalized.header
        )
        profile = selection.profile
        version_issues = tuple(
            HeaderPreviewIssue(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                value=(
                    str(issue.path)
                    if issue.path is not None
                    else issue.dependency
                ),
            )
            for issue in selection.issues
        )

        if profile is None:
            return HeaderPreviewResult(
                input_path=path,
                is_valid=False,
                header_values=MappingProxyType(
                    normalized.header
                    .as_xml_attributes()
                ),
                profile_code=None,
                instruction_version=None,
                xsd_version=None,
                xsd_path=None,
                version_status=(
                    "VERSÃO NÃO RESOLVIDA"
                ),
                blocks_apt=True,
                issues=(
                    *initial_issues,
                    *normalization_issues,
                    *version_issues,
                ),
            )

        status = (
            "CONFIRMADA"
            if profile.is_confirmed
            and not selection.blocks_apt
            else "DIAGNÓSTICA — BLOQUEIA APTO"
        )

        return HeaderPreviewResult(
            input_path=path,
            is_valid=(
                not selection
                .has_technical_failure
            ),
            header_values=MappingProxyType(
                normalized.header
                .as_xml_attributes()
            ),
            profile_code=profile.code,
            instruction_version=(
                profile.instruction_version
            ),
            xsd_version=profile.xsd_version,
            xsd_path=profile.xsd_path,
            version_status=status,
            blocks_apt=selection.blocks_apt,
            issues=(
                *initial_issues,
                *normalization_issues,
                *version_issues,
            ),
        )

    @staticmethod
    def _raw_values(
        raw_header: Any,
    ) -> dict[str, str]:
        return {
            field_name: (
                ""
                if field.resolved_value is None
                else str(field.resolved_value)
            )
            for field_name, field in (
                raw_header.fields.items()
            )
        }


def preview_header(
    input_path: str | Path,
) -> HeaderPreviewResult:
    """Atalho funcional para a pré-visualização."""

    return HeaderPreviewService().preview(
        input_path
    )
