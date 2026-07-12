"""Validação segura de um XML com o XSD do perfil selecionado.

O validador não tenta esquemas alternativos. O XSD utilizado é sempre
``profile.xsd_path``, previamente selecionado pela ``dataBase``.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from src.domain.regulatory_version import RegulatoryVersion
from src.domain.xsd_validation import (
    XsdValidationIssue,
    XsdValidationResult,
    XsdValidationStatus,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_TECHNICAL_FAILURE = "FALHA TÉCNICA"


class XsdValidator:
    """Compila o esquema e valida um arquivo XML."""

    def validate(
        self,
        xml_path: str | Path,
        profile: RegulatoryVersion,
    ) -> XsdValidationResult:
        xml = Path(xml_path).expanduser()
        xsd = Path(profile.xsd_path).expanduser()

        if not xml.is_file():
            return self._technical_result(
                xml_path=xml,
                profile=profile,
                code="XSD-XML-001",
                message=(
                    "O arquivo XML informado não existe "
                    "ou não é um arquivo."
                ),
                source="Leitura do XML",
                filename=str(xml),
            )

        if not xsd.is_file():
            return self._technical_result(
                xml_path=xml,
                profile=profile,
                code="XSD-SCHEMA-001",
                message=(
                    "O XSD selecionado para o perfil não "
                    "existe ou não é um arquivo."
                ),
                source="Seleção automática do XSD",
                filename=str(xsd),
            )

        schema_document = self._parse_schema(
            xml_path=xml,
            profile=profile,
        )

        if isinstance(
            schema_document,
            XsdValidationResult,
        ):
            return schema_document

        schema = self._compile_schema(
            xml_path=xml,
            profile=profile,
            schema_document=schema_document,
        )

        if isinstance(schema, XsdValidationResult):
            return schema

        xml_document = self._parse_xml(
            xml_path=xml,
            profile=profile,
        )

        if isinstance(
            xml_document,
            XsdValidationResult,
        ):
            return xml_document

        try:
            valid = schema.validate(xml_document)
        except etree.XMLSchemaError as error:
            return self._technical_result_from_log(
                xml_path=xml,
                profile=profile,
                code="XSD-VAL-TECH-001",
                message=(
                    "O mecanismo de validação XSD falhou "
                    f"tecnicamente: {error}"
                ),
                source="lxml.XMLSchema.validate",
                error_log=error.error_log,
            )

        if valid:
            return XsdValidationResult(
                original_xml_path=xml,
                final_xml_path=xml,
                xsd_path=xsd,
                profile_code=profile.code,
                xsd_version=profile.xsd_version,
                status=XsdValidationStatus.VALID,
                profile_blocks_apt=profile.blocks_apt,
                upstream_blocks_apt=False,
                reclassified_to_not_apt=False,
                collision_index=0,
                issues=(),
            )

        issues = tuple(
            self._issue_from_log_entry(
                entry,
                code="XSD-VAL-001",
                severity=SEVERITY_BLOCKING_ERROR,
                source=(
                    f"XSD {profile.xsd_version}"
                ),
            )
            for entry in schema.error_log
        )

        if not issues:
            issues = (
                XsdValidationIssue(
                    code="XSD-VAL-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O XML não atende ao XSD selecionado, "
                        "mas o mecanismo não retornou detalhes."
                    ),
                    source=(
                        f"XSD {profile.xsd_version}"
                    ),
                    blocks_apt=True,
                    filename=str(xml),
                ),
            )

        return XsdValidationResult(
            original_xml_path=xml,
            final_xml_path=xml,
            xsd_path=xsd,
            profile_code=profile.code,
            xsd_version=profile.xsd_version,
            status=XsdValidationStatus.INVALID,
            profile_blocks_apt=profile.blocks_apt,
            upstream_blocks_apt=False,
            reclassified_to_not_apt=False,
            collision_index=0,
            issues=issues,
        )

    def _parse_schema(
        self,
        *,
        xml_path: Path,
        profile: RegulatoryVersion,
    ) -> etree._ElementTree | XsdValidationResult:
        parser = self._secure_parser()

        try:
            return etree.parse(
                str(profile.xsd_path),
                parser,
            )
        except etree.XMLSyntaxError as error:
            return self._technical_result_from_log(
                xml_path=xml_path,
                profile=profile,
                code="XSD-SCHEMA-002",
                message=(
                    "O arquivo XSD selecionado não é um "
                    "XML bem-formado."
                ),
                source="Leitura do XSD",
                error_log=error.error_log,
            )
        except OSError as error:
            return self._technical_result(
                xml_path=xml_path,
                profile=profile,
                code="XSD-SCHEMA-003",
                message=(
                    "O XSD selecionado não pôde ser lido: "
                    f"{error}"
                ),
                source="Leitura do XSD",
                filename=str(profile.xsd_path),
            )

    def _compile_schema(
        self,
        *,
        xml_path: Path,
        profile: RegulatoryVersion,
        schema_document: etree._ElementTree,
    ) -> etree.XMLSchema | XsdValidationResult:
        try:
            return etree.XMLSchema(schema_document)
        except etree.XMLSchemaParseError as error:
            return self._technical_result_from_log(
                xml_path=xml_path,
                profile=profile,
                code="XSD-SCHEMA-004",
                message=(
                    "O arquivo XSD é bem-formado, mas não "
                    "pôde ser compilado como XML Schema."
                ),
                source="Compilação do XSD",
                error_log=error.error_log,
            )
        except etree.XMLSchemaError as error:
            return self._technical_result(
                xml_path=xml_path,
                profile=profile,
                code="XSD-SCHEMA-005",
                message=(
                    "Falha técnica ao compilar o XSD: "
                    f"{error}"
                ),
                source="Compilação do XSD",
                filename=str(profile.xsd_path),
            )

    def _parse_xml(
        self,
        *,
        xml_path: Path,
        profile: RegulatoryVersion,
    ) -> etree._ElementTree | XsdValidationResult:
        parser = self._secure_parser()

        try:
            return etree.parse(
                str(xml_path),
                parser,
            )
        except etree.XMLSyntaxError as error:
            return self._technical_result_from_log(
                xml_path=xml_path,
                profile=profile,
                code="XSD-XML-002",
                message=(
                    "O arquivo que seria validado não é "
                    "um XML bem-formado."
                ),
                source="Leitura do XML",
                error_log=error.error_log,
            )
        except OSError as error:
            return self._technical_result(
                xml_path=xml_path,
                profile=profile,
                code="XSD-XML-003",
                message=(
                    "O XML não pôde ser lido: "
                    f"{error}"
                ),
                source="Leitura do XML",
                filename=str(xml_path),
            )

    @staticmethod
    def _secure_parser() -> etree.XMLParser:
        """Parser sem rede, DTD carregada ou entidades resolvidas."""

        return etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            recover=False,
            huge_tree=False,
            remove_blank_text=False,
        )

    def _technical_result_from_log(
        self,
        *,
        xml_path: Path,
        profile: RegulatoryVersion,
        code: str,
        message: str,
        source: str,
        error_log: etree._ListErrorLog,
    ) -> XsdValidationResult:
        entries = tuple(error_log)

        issues = tuple(
            self._issue_from_log_entry(
                entry,
                code=code,
                severity=SEVERITY_TECHNICAL_FAILURE,
                source=source,
            )
            for entry in entries
        )

        if not issues:
            issues = (
                XsdValidationIssue(
                    code=code,
                    severity=(
                        SEVERITY_TECHNICAL_FAILURE
                    ),
                    message=message,
                    source=source,
                    blocks_apt=True,
                    filename=str(xml_path),
                ),
            )

        return XsdValidationResult(
            original_xml_path=xml_path,
            final_xml_path=xml_path,
            xsd_path=profile.xsd_path,
            profile_code=profile.code,
            xsd_version=profile.xsd_version,
            status=(
                XsdValidationStatus.TECHNICAL_FAILURE
            ),
            profile_blocks_apt=profile.blocks_apt,
            upstream_blocks_apt=False,
            reclassified_to_not_apt=False,
            collision_index=0,
            issues=issues,
        )

    @staticmethod
    def _technical_result(
        *,
        xml_path: Path,
        profile: RegulatoryVersion,
        code: str,
        message: str,
        source: str,
        filename: str | None = None,
    ) -> XsdValidationResult:
        issue = XsdValidationIssue(
            code=code,
            severity=SEVERITY_TECHNICAL_FAILURE,
            message=message,
            source=source,
            blocks_apt=True,
            filename=filename,
        )

        return XsdValidationResult(
            original_xml_path=xml_path,
            final_xml_path=xml_path,
            xsd_path=profile.xsd_path,
            profile_code=profile.code,
            xsd_version=profile.xsd_version,
            status=(
                XsdValidationStatus.TECHNICAL_FAILURE
            ),
            profile_blocks_apt=profile.blocks_apt,
            upstream_blocks_apt=False,
            reclassified_to_not_apt=False,
            collision_index=0,
            issues=(issue,),
        )

    @staticmethod
    def _issue_from_log_entry(
        entry: etree._LogEntry,
        *,
        code: str,
        severity: str,
        source: str,
    ) -> XsdValidationIssue:
        return XsdValidationIssue(
            code=code,
            severity=severity,
            message=entry.message,
            source=source,
            blocks_apt=True,
            line=(
                entry.line
                if entry.line > 0
                else None
            ),
            column=(
                entry.column
                if entry.column > 0
                else None
            ),
            xpath=entry.path or None,
            filename=entry.filename or None,
            level_name=entry.level_name or None,
            domain_name=entry.domain_name or None,
            type_name=entry.type_name or None,
        )


def validate_xml_with_xsd(
    xml_path: str | Path,
    profile: RegulatoryVersion,
) -> XsdValidationResult:
    """Atalho funcional para validação direta de um XML."""

    return XsdValidator().validate(
        xml_path,
        profile,
    )
