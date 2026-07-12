"""Serviço de geração e gravação do arquivo XML.

O serviço:

- escolhe o nome normal ou ``NAO_APTO``;
- gera XML mesmo para diagnóstico, desde que o objeto exista;
- nunca sobrescreve silenciosamente;
- cria sufixos ``_001``, ``_002`` e assim por diante;
- não executa validação XSD nesta etapa.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from src.builders.xml_builder import (
    XmlBuildError,
    XmlDocumentBuilder,
)
from src.config import (
    OUTPUT_DIR,
    build_xml_filename,
)
from src.domain.document_model import (
    DocumentBuildResult,
)
from src.domain.xml_generation import (
    XmlElementCounts,
    XmlGenerationIssue,
    XmlGenerationMode,
    XmlGenerationResult,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_INFORMATION = "INFORMAÇÃO"


@dataclass(frozen=True, slots=True)
class XmlGenerationError(Exception):
    """Falha técnica de acesso ou gravação do arquivo."""

    code: str
    message: str
    details: tuple[tuple[str, object], ...] = ()

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class XmlGenerationService:
    """Coordena serialização, nomeação e gravação segura."""

    def __init__(
        self,
        builder: XmlDocumentBuilder | None = None,
    ) -> None:
        self.builder = builder or XmlDocumentBuilder()

    def generate(
        self,
        build_result: DocumentBuildResult,
        *,
        output_dir: str | Path = OUTPUT_DIR,
    ) -> XmlGenerationResult:
        document = build_result.document
        build_issue_codes = tuple(
            issue.code
            for issue in build_result.issues
        )

        empty_counts = XmlElementCounts(
            individualized_events=0,
            probabilities=0,
            accountings=0,
            consolidated_events=0,
            source_systems=0,
            internal_accounts=0,
        )

        if document is None:
            issue = XmlGenerationIssue(
                code="XML-GEN-001",
                severity=SEVERITY_BLOCKING_ERROR,
                message=(
                    "O XML não foi gerado porque o objeto "
                    "final do documento não existe."
                ),
                source="Serviço de geração XML",
                blocks_apt=True,
            )
            return XmlGenerationResult(
                output_path=None,
                requested_filename=None,
                mode=XmlGenerationMode.DIAGNOSTIC,
                bytes_written=0,
                collision_index=0,
                well_formed=False,
                element_counts=empty_counts,
                build_issue_codes=build_issue_codes,
                issues=(issue,),
            )

        is_candidate = (
            build_result.is_xml_ready
            and not build_result.blocks_apt
        )
        mode = (
            XmlGenerationMode.CANDIDATE
            if is_candidate
            else XmlGenerationMode.DIAGNOSTIC
        )
        requested_filename = build_xml_filename(
            document.header.data_base,
            apt_for_submission=is_candidate,
        )

        try:
            xml_bytes = self.builder.serialize(document)
        except XmlBuildError as error:
            raise XmlGenerationError(
                code=error.code,
                message=error.message,
                details=(
                    (
                        "perfil",
                        document.profile_code,
                    ),
                ),
            ) from error

        directory = Path(output_dir).expanduser()

        if directory.exists() and not directory.is_dir():
            raise XmlGenerationError(
                code="XML-WRITE-002",
                message=(
                    "O caminho de saída existe, mas não "
                    "é uma pasta."
                ),
                details=(
                    ("caminho", str(directory)),
                ),
            )

        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as error:
            raise XmlGenerationError(
                code="XML-WRITE-001",
                message=(
                    "Não foi possível criar a pasta de saída."
                ),
                details=(
                    ("pasta", str(directory)),
                    ("erro", str(error)),
                ),
            ) from error

        if not directory.is_dir():
            raise XmlGenerationError(
                code="XML-WRITE-002",
                message=(
                    "O caminho de saída existe, mas não "
                    "é uma pasta."
                ),
                details=(
                    ("caminho", str(directory)),
                ),
            )

        output_path, collision_index = (
            self._write_without_overwrite(
                directory=directory,
                requested_filename=(
                    requested_filename
                ),
                content=xml_bytes,
            )
        )

        issues: list[XmlGenerationIssue] = []

        if mode == XmlGenerationMode.DIAGNOSTIC:
            issues.append(
                XmlGenerationIssue(
                    code="XML-GEN-INFO-001",
                    severity=SEVERITY_INFORMATION,
                    message=(
                        "XML gerado para diagnóstico e "
                        "identificado como NÃO APTO."
                    ),
                    source="Serviço de geração XML",
                    blocks_apt=True,
                    details=(
                        (
                            "ocorrenciasMontagem",
                            build_issue_codes,
                        ),
                    ),
                )
            )

        if collision_index > 0:
            issues.append(
                XmlGenerationIssue(
                    code="XML-GEN-INFO-002",
                    severity=SEVERITY_INFORMATION,
                    message=(
                        "Já existia um arquivo com o nome "
                        "previsto; foi criado um novo nome "
                        "sem sobrescrever o anterior."
                    ),
                    source="Serviço de geração XML",
                    blocks_apt=False,
                    details=(
                        (
                            "nomeSolicitado",
                            requested_filename,
                        ),
                        (
                            "nomeCriado",
                            output_path.name,
                        ),
                    ),
                )
            )

        return XmlGenerationResult(
            output_path=output_path,
            requested_filename=requested_filename,
            mode=mode,
            bytes_written=len(xml_bytes),
            collision_index=collision_index,
            well_formed=True,
            element_counts=(
                self.builder.count_elements(document)
            ),
            build_issue_codes=build_issue_codes,
            issues=tuple(issues),
        )

    @staticmethod
    def _write_without_overwrite(
        *,
        directory: Path,
        requested_filename: str,
        content: bytes,
    ) -> tuple[Path, int]:
        requested_path = directory / requested_filename
        stem = requested_path.stem
        suffix = requested_path.suffix

        for index in range(0, 10000):
            candidate = (
                requested_path
                if index == 0
                else directory
                / f"{stem}_{index:03d}{suffix}"
            )

            try:
                with candidate.open("xb") as file:
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())

                return candidate, index

            except FileExistsError:
                continue
            except OSError as error:
                raise XmlGenerationError(
                    code="XML-WRITE-003",
                    message=(
                        "Não foi possível gravar o arquivo XML."
                    ),
                    details=(
                        ("arquivo", str(candidate)),
                        ("erro", str(error)),
                    ),
                ) from error

        raise XmlGenerationError(
            code="XML-WRITE-004",
            message=(
                "Não foi possível encontrar um nome livre "
                "para o arquivo XML."
            ),
            details=(
                (
                    "nomeSolicitado",
                    requested_filename,
                ),
            ),
        )


def generate_xml(
    build_result: DocumentBuildResult,
    *,
    output_dir: str | Path = OUTPUT_DIR,
) -> XmlGenerationResult:
    """Atalho funcional para geração do arquivo."""

    return XmlGenerationService().generate(
        build_result,
        output_dir=output_dir,
    )
