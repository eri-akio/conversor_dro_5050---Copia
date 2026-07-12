"""Coordenação da validação XSD do XML recém-gerado.

Quando um XML candidato falha no XSD ou não pode ser verificado, o
arquivo é reclassificado com ``NAO_APTO`` sem sobrescrever arquivos
existentes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import shutil

from src.config import build_xml_filename
from src.domain.regulatory_version import RegulatoryVersion
from src.domain.xml_generation import XmlGenerationResult
from src.domain.xsd_validation import (
    XsdValidationIssue,
    XsdValidationResult,
    XsdValidationStatus,
)
from src.validators.xsd_validator import XsdValidator


SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_TECHNICAL_FAILURE = "FALHA TÉCNICA"


@dataclass(frozen=True, slots=True)
class XsdValidationError(Exception):
    """Falha técnica ao reclassificar o arquivo validado."""

    code: str
    message: str
    details: tuple[tuple[str, object], ...] = ()

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class XsdValidationService:
    """Valida o XML gerado usando somente o perfil selecionado."""

    def __init__(
        self,
        validator: XsdValidator | None = None,
    ) -> None:
        self.validator = validator or XsdValidator()

    def validate_generated(
        self,
        xml_result: XmlGenerationResult,
        profile: RegulatoryVersion,
        *,
        data_base: str,
    ) -> XsdValidationResult:
        if (
            not xml_result.is_generated
            or xml_result.output_path is None
        ):
            issue = XsdValidationIssue(
                code="XSD-GEN-001",
                severity=SEVERITY_TECHNICAL_FAILURE,
                message=(
                    "Não existe arquivo XML gerado para "
                    "ser validado pelo XSD."
                ),
                source="Integração geração/XSD",
                blocks_apt=True,
            )
            return XsdValidationResult(
                original_xml_path=None,
                final_xml_path=None,
                xsd_path=profile.xsd_path,
                profile_code=profile.code,
                xsd_version=profile.xsd_version,
                status=(
                    XsdValidationStatus
                    .TECHNICAL_FAILURE
                ),
                profile_blocks_apt=profile.blocks_apt,
                upstream_blocks_apt=True,
                reclassified_to_not_apt=False,
                collision_index=0,
                issues=(issue,),
            )

        validation = self.validator.validate(
            xml_result.output_path,
            profile,
        )
        validation = replace(
            validation,
            upstream_blocks_apt=(
                xml_result.blocks_apt
            ),
        )

        should_reclassify = (
            xml_result.is_candidate
            and validation.blocks_apt
            and validation.final_xml_path is not None
            and validation.final_xml_path.is_file()
        )

        if not should_reclassify:
            return validation

        requested_name = build_xml_filename(
            data_base,
            apt_for_submission=False,
        )

        new_path, collision_index = (
            self._move_without_overwrite(
                source=validation.final_xml_path,
                requested_name=requested_name,
            )
        )

        info = XsdValidationIssue(
            code="XSD-INFO-001",
            severity=SEVERITY_INFORMATION,
            message=(
                "O XML candidato foi identificado como "
                "NÃO APTO após a validação XSD."
            ),
            source="Serviço de validação XSD",
            blocks_apt=True,
            filename=str(new_path),
        )

        return replace(
            validation,
            final_xml_path=new_path,
            reclassified_to_not_apt=True,
            collision_index=collision_index,
            issues=(
                *validation.issues,
                info,
            ),
        )

    @staticmethod
    def _move_without_overwrite(
        *,
        source: Path,
        requested_name: str,
    ) -> tuple[Path, int]:
        directory = source.parent
        requested = directory / requested_name
        stem = requested.stem
        suffix = requested.suffix

        for index in range(0, 10000):
            destination = (
                requested
                if index == 0
                else directory
                / f"{stem}_{index:03d}{suffix}"
            )

            try:
                with source.open("rb") as source_file:
                    with destination.open("xb") as target:
                        shutil.copyfileobj(
                            source_file,
                            target,
                        )
                        target.flush()
                        os.fsync(target.fileno())

                source.unlink()
                return destination, index

            except FileExistsError:
                continue
            except OSError as error:
                if destination.exists():
                    try:
                        destination.unlink()
                    except OSError:
                        pass

                raise XsdValidationError(
                    code="XSD-WRITE-001",
                    message=(
                        "Não foi possível reclassificar o "
                        "XML candidato como NÃO APTO."
                    ),
                    details=(
                        ("origem", str(source)),
                        (
                            "destinoTentado",
                            str(destination),
                        ),
                        ("erro", str(error)),
                    ),
                ) from error

        raise XsdValidationError(
            code="XSD-WRITE-002",
            message=(
                "Não foi encontrado um nome livre para "
                "reclassificar o XML como NÃO APTO."
            ),
            details=(
                ("arquivoOriginal", str(source)),
                (
                    "nomeSolicitado",
                    requested_name,
                ),
            ),
        )


def validate_generated_xml(
    xml_result: XmlGenerationResult,
    profile: RegulatoryVersion,
    *,
    data_base: str,
) -> XsdValidationResult:
    """Atalho funcional do serviço de validação."""

    return XsdValidationService().validate_generated(
        xml_result,
        profile,
        data_base=data_base,
    )
