"""Consolidação única do status final da remessa."""

from __future__ import annotations

from typing import Iterable

from src.domain.base_row_validation import (
    BaseRowsValidationResult,
)
from src.domain.conversion import (
    ConversionIssue,
    ConversionStage,
    FinalStatusDecision,
    FinalStatusReason,
)
from src.domain.document_model import (
    DocumentBuildResult,
)
from src.domain.event_financial import (
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventsValidationResult,
)
from src.domain.post_processing import (
    PostProcessingValidationResult,
)
from src.domain.pre_processing import (
    PreProcessingValidationResult,
)
from src.domain.reference_tables import (
    ReferenceTablesValidationResult,
)
from src.domain.regulatory_version import (
    RegulatoryVersion,
)
from src.domain.reporting import (
    FinalExecutionStatus,
)
from src.domain.xml_generation import (
    XmlGenerationResult,
)
from src.domain.xsd_validation import (
    XsdValidationResult,
)


class FinalStatusService:
    """Aplica uma única política de classificação final."""

    def evaluate_complete(
        self,
        *,
        profile: RegulatoryVersion,
        row_validation: BaseRowsValidationResult,
        grouping: EventGroupingResult,
        event_validation: EventsValidationResult,
        financial_validation: (
            EventsFinancialValidationResult
        ),
        references: ReferenceTablesValidationResult,
        pre_processing: PreProcessingValidationResult,
        post_processing: PostProcessingValidationResult,
        build_result: DocumentBuildResult,
        xml_result: XmlGenerationResult,
        xsd_result: XsdValidationResult,
    ) -> FinalStatusDecision:
        reasons: list[FinalStatusReason] = []

        if xsd_result.has_technical_failure:
            reasons.extend(
                FinalStatusReason(
                    code=issue.code,
                    message=issue.message,
                    source=issue.source,
                    severity="FALHA TÉCNICA",
                    blocks_apt=True,
                    details=(
                        ("linha", issue.line),
                        ("coluna", issue.column),
                        ("xpath", issue.xpath),
                    ),
                )
                for issue in xsd_result.technical_issues
            )
            return self._decision(
                reasons,
                technical=True,
            )

        if profile.blocks_apt:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-PERFIL-001",
                    message=(
                        "O perfil possui conflito documental "
                        "impeditivo."
                    ),
                    source="Matriz de versões",
                    severity="ERRO IMPEDITIVO",
                    details=(
                        ("perfil", profile.code),
                        (
                            "conflitos",
                            profile.conflict_codes,
                        ),
                    ),
                )
            )

        self._append_validity_reason(
            reasons,
            valid=row_validation.is_locally_valid,
            code="STATUS-LINHA-001",
            message=(
                "Existem erros impeditivos na validação "
                "das linhas da Base."
            ),
            source="Validação por linha",
        )
        self._append_pending_reason(
            reasons,
            pending=not row_validation.is_fully_verified,
            code="STATUS-LINHA-NE-001",
            message=(
                "Existem regras por linha ainda não executadas."
            ),
            source="Validação por linha",
        )

        self._append_validity_reason(
            reasons,
            valid=grouping.is_valid,
            code="STATUS-AGRUP-001",
            message=(
                "O agrupamento por idEvento possui "
                "conflitos impeditivos."
            ),
            source="Agrupamento de eventos",
        )

        self._append_validity_reason(
            reasons,
            valid=event_validation.is_valid,
            code="STATUS-EVENTO-001",
            message=(
                "Existem eventos com inconsistências "
                "impeditivas."
            ),
            source="Validação dos eventos",
        )
        self._append_pending_reason(
            reasons,
            pending=not event_validation.is_fully_verified,
            code="STATUS-EVENTO-NE-001",
            message=(
                "Existem regras de evento ainda não executadas."
            ),
            source="Validação dos eventos",
        )

        self._append_validity_reason(
            reasons,
            valid=financial_validation.is_valid,
            code="STATUS-FIN-001",
            message=(
                "Existem inconsistências financeiras "
                "impeditivas."
            ),
            source="Validação financeira",
        )
        self._append_pending_reason(
            reasons,
            pending=not financial_validation.is_fully_verified,
            code="STATUS-FIN-NE-001",
            message=(
                "Existem regras financeiras ainda não executadas."
            ),
            source="Validação financeira",
        )

        self._append_validity_reason(
            reasons,
            valid=references.is_valid,
            code="STATUS-REF-001",
            message=(
                "As tabelas de sistemas ou contas possuem "
                "erros impeditivos."
            ),
            source="Tabelas de referência",
        )
        self._append_pending_reason(
            reasons,
            pending=not references.is_fully_verified,
            code="STATUS-REF-NE-001",
            message=(
                "Existem validações de sistemas ou contas "
                "ainda não executadas."
            ),
            source="Tabelas de referência",
        )

        self._append_validity_reason(
            reasons,
            valid=pre_processing.is_locally_valid,
            code="STATUS-PRE-001",
            message=(
                "Existe crítica de pré-processamento reprovada."
            ),
            source="Pré-processamento",
        )
        self._append_pending_reason(
            reasons,
            pending=bool(
                pre_processing.not_executed_rules
            ),
            code="STATUS-PRE-NE-001",
            message=(
                "Existem críticas de pré-processamento "
                "não executadas."
            ),
            source="Pré-processamento",
            details=(
                (
                    "codigos",
                    tuple(
                        result.code
                        for result in (
                            pre_processing
                            .not_executed_rules
                        )
                    ),
                ),
            ),
        )

        self._append_validity_reason(
            reasons,
            valid=post_processing.is_locally_valid,
            code="STATUS-POS-001",
            message=(
                "Existe crítica de pós-processamento reprovada."
            ),
            source="Pós-processamento",
        )
        self._append_pending_reason(
            reasons,
            pending=bool(
                post_processing.not_executed_rules
            ),
            code="STATUS-POS-NE-001",
            message=(
                "Existem críticas de pós-processamento "
                "não executadas."
            ),
            source="Pós-processamento",
            details=(
                (
                    "codigos",
                    tuple(
                        result.code
                        for result in (
                            post_processing
                            .not_executed_rules
                        )
                    ),
                ),
            ),
        )

        if post_processing.warning_failed_rules:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-POS-AVISO-001",
                    message=(
                        "Existem esclarecimentos de "
                        "pós-processamento com ocorrência."
                    ),
                    source="Pós-processamento",
                    severity="AVISO",
                    blocks_apt=False,
                    details=(
                        (
                            "codigos",
                            tuple(
                                result.code
                                for result in (
                                    post_processing
                                    .warning_failed_rules
                                )
                            ),
                        ),
                    ),
                )
            )

        if not build_result.is_built:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-DOC-001",
                    message=(
                        "O objeto final do documento não foi "
                        "construído."
                    ),
                    source="Montagem do documento",
                    severity="ERRO IMPEDITIVO",
                )
            )
        elif build_result.blocks_apt:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-DOC-002",
                    message=(
                        "A montagem do documento registrou "
                        "impedimentos de aptidão."
                    ),
                    source="Montagem do documento",
                    severity="ERRO IMPEDITIVO",
                    details=(
                        (
                            "codigos",
                            tuple(
                                issue.code
                                for issue in (
                                    build_result
                                    .apt_blocking_issues
                                )
                            ),
                        ),
                    ),
                )
            )

        if not xml_result.is_generated:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-XML-001",
                    message="O arquivo XML não foi gerado.",
                    source="Geração do XML",
                    severity="ERRO IMPEDITIVO",
                )
            )
        elif xml_result.blocks_apt:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-XML-002",
                    message=(
                        "O XML foi gerado para diagnóstico e "
                        "permanece identificado como não apto."
                    ),
                    source="Geração do XML",
                    severity="ERRO IMPEDITIVO",
                )
            )

        if xsd_result.is_invalid:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-XSD-001",
                    message=(
                        "O XML é inválido no XSD selecionado."
                    ),
                    source="Validação XSD",
                    severity="ERRO IMPEDITIVO",
                    details=(
                        ("xsd", str(xsd_result.xsd_path)),
                    ),
                )
            )

        return self._decision(reasons)

    def evaluate_interrupted(
        self,
        *,
        stage: ConversionStage,
        issues: Iterable[ConversionIssue],
        technical: bool,
    ) -> FinalStatusDecision:
        reasons = tuple(
            FinalStatusReason(
                code=issue.code,
                message=issue.message,
                source=issue.source,
                severity=issue.severity,
                blocks_apt=True,
                details=issue.details,
            )
            for issue in issues
        )

        if not reasons:
            reasons = (
                FinalStatusReason(
                    code="STATUS-INT-001",
                    message=(
                        "A execução foi interrompida antes "
                        "da conclusão."
                    ),
                    source=stage.value,
                    severity=(
                        "FALHA TÉCNICA"
                        if technical
                        else "ERRO IMPEDITIVO"
                    ),
                ),
            )

        return self._decision(
            reasons,
            technical=technical,
            interrupted_stage=stage,
        )

    @staticmethod
    def _append_validity_reason(
        reasons: list[FinalStatusReason],
        *,
        valid: bool,
        code: str,
        message: str,
        source: str,
    ) -> None:
        if valid:
            return

        reasons.append(
            FinalStatusReason(
                code=code,
                message=message,
                source=source,
                severity="ERRO IMPEDITIVO",
            )
        )

    @staticmethod
    def _append_pending_reason(
        reasons: list[FinalStatusReason],
        *,
        pending: bool,
        code: str,
        message: str,
        source: str,
        details: tuple[
            tuple[str, object],
            ...,
        ] = (),
    ) -> None:
        if not pending:
            return

        reasons.append(
            FinalStatusReason(
                code=code,
                message=message,
                source=source,
                severity="REGRA NÃO EXECUTADA",
                details=details,
            )
        )

    @staticmethod
    def _decision(
        reasons: Iterable[FinalStatusReason],
        *,
        technical: bool = False,
        interrupted_stage: (
            ConversionStage | None
        ) = None,
    ) -> FinalStatusDecision:
        unique: list[FinalStatusReason] = []
        seen: set[tuple[str, str]] = set()

        for reason in reasons:
            key = (reason.code, reason.message)
            if key in seen:
                continue
            seen.add(key)
            unique.append(reason)

        if technical:
            stage_text = (
                f" na etapa {interrupted_stage.value}"
                if interrupted_stage is not None
                else ""
            )
            return FinalStatusDecision(
                status=(
                    FinalExecutionStatus
                    .TECHNICAL_FAILURE
                ),
                message=(
                    "A execução terminou com falha "
                    f"técnica{stage_text}."
                ),
                reasons=tuple(unique),
            )

        blockers = tuple(
            reason
            for reason in unique
            if reason.blocks_apt
        )

        if blockers:
            summary = "; ".join(
                reason.message.rstrip(".")
                for reason in blockers
            )
            return FinalStatusDecision(
                status=FinalExecutionStatus.NOT_APT,
                message=summary + ".",
                reasons=tuple(unique),
            )

        return FinalStatusDecision(
            status=FinalExecutionStatus.APT,
            message=(
                "XML válido no XSD e sem erros "
                "impeditivos locais ou regras pendentes."
            ),
            reasons=tuple(unique),
        )


def consolidate_final_status(
    **kwargs,
) -> FinalStatusDecision:
    """Atalho funcional para a consolidação completa."""

    return FinalStatusService().evaluate_complete(
        **kwargs
    )
