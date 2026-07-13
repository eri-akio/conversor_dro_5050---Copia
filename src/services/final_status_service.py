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
from src.domain.rule_reconciliation import (
    RuleReconciliationResult,
)
from src.domain.reporting import (
    DependentValidationStatus,
    ExternalValidationStatus,
    FinalExecutionStatus,
    GeneralValidationStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    XsdValidationSummaryStatus,
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
        reconciliation: RuleReconciliationResult,
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
        pre_rules = tuple(
            getattr(pre_processing, "rule_results", ())
        )
        post_rules = tuple(
            getattr(post_processing, "rule_results", ())
        )
        external_rules = self._rules_with_execution_class(
            pre_rules,
            "EXTERNA",
        )
        historical_rules = self._rules_with_execution_class(
            post_rules,
            "HISTÓRICO DA DATA-BASE ANTERIOR",
        )
        local_pre_rules = tuple(
            rule for rule in pre_rules
            if rule not in external_rules
        )
        local_post_rules = tuple(
            rule for rule in post_rules
            if rule not in historical_rules
        )
        status_externo = self._external_status(external_rules)
        status_historico = self._historical_status(
            historical_rules
        )

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
                status_local=(
                    LocalValidationStatus.REPROVED
                ),
                status_xsd=(
                    XsdValidationSummaryStatus.NOT_EXECUTED
                ),
                status_externo=status_externo,
                status_historico=status_historico,
                status_dependencias=DependentValidationStatus.PENDING,
            )

        if profile.blocks_apt:
            reasons.append(
                FinalStatusReason(
                    code="STATUS-PERFIL-001",
                    message=(
                        "O perfil possui conflito documental "
                        "ainda não resolvido."
                    ),
                    source="Matriz de versões",
                    severity="REGRA NÃO EXECUTADA",
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
        self._append_pending_reason(
            reasons,
            pending=not reconciliation.is_fully_reconciled,
            code="STATUS-RECON-NE-001",
            message=(
                "Existem regras adiadas sem resultado definitivo."
            ),
            source="Reconciliação de regras adiadas",
            details=((
                "codigos",
                tuple(
                    record.rule_code
                    for record in reconciliation.unresolved_records
                ),
            ),),
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
            valid=not self._has_rule_status(
                local_pre_rules,
                "REPROVADA",
            ),
            code="STATUS-PRE-001",
            message=(
                "Existe crítica local de pré-processamento "
                "reprovada."
            ),
            source="Pré-processamento local",
        )
        self._append_pending_reason(
            reasons,
            pending=self._has_rule_status(
                local_pre_rules,
                "REGRA NÃO EXECUTADA",
            ),
            code="STATUS-PRE-NE-001",
            message=(
                "Existem críticas locais de pré-processamento "
                "não executadas."
            ),
            source="Pré-processamento local",
            details=(
                (
                    "codigos",
                    self._rule_codes_with_status(
                        local_pre_rules,
                        "REGRA NÃO EXECUTADA",
                    ),
                ),
            ),
        )

        self._append_validity_reason(
            reasons,
            valid=not self._has_blocking_failure(
                local_post_rules
            ),
            code="STATUS-POS-001",
            message=(
                "Existe crítica de pós-processamento reprovada."
            ),
            source="Pós-processamento",
        )
        self._append_pending_reason(
            reasons,
            pending=self._has_rule_status(
                local_post_rules,
                "REGRA NÃO EXECUTADA",
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
                    self._rule_codes_with_status(
                        local_post_rules,
                        "REGRA NÃO EXECUTADA",
                    ),
                ),
            ),
        )

        self._append_validity_reason(
            reasons,
            valid=(
                status_externo
                != ExternalValidationStatus.REPROVED
            ),
            code="STATUS-EXT-001",
            message="Existe validação externa reprovada.",
            source="Validações externas",
        )
        self._append_pending_reason(
            reasons,
            pending=(
                status_externo
                == ExternalValidationStatus.PENDING
            ),
            code="STATUS-EXT-NE-001",
            message="Existem validações externas não executadas.",
            source="Validações externas",
            details=(("codigos", self._rule_codes_with_status(
                external_rules,
                "REGRA NÃO EXECUTADA",
            )),),
        )
        self._append_validity_reason(
            reasons,
            valid=(
                status_historico
                != HistoricalValidationStatus.REPROVED
            ),
            code="STATUS-HIST-001",
            message="Existe validação histórica reprovada.",
            source="Validações históricas",
        )
        self._append_pending_reason(
            reasons,
            pending=(
                status_historico
                == HistoricalValidationStatus.PENDING
            ),
            code="STATUS-HIST-NE-001",
            message="Existem validações históricas não executadas.",
            source="Validações históricas",
            details=(("codigos", self._rule_codes_with_status(
                historical_rules,
                "REGRA NÃO EXECUTADA",
            )),),
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

        local_build_issues = tuple(
            issue
            for issue in build_result.apt_blocking_issues
            if not issue.code.startswith((
                "DOC-PRE-",
                "DOC-POS-",
            ))
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
        elif local_build_issues:
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
                                for issue in local_build_issues
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

        local_reproved = any((
            not row_validation.is_locally_valid,
            not grouping.is_valid,
            not event_validation.is_valid,
            bool(getattr(reconciliation, "failed_records", ())),
            not financial_validation.is_valid,
            not references.is_valid,
            self._has_rule_status(
                local_pre_rules,
                "REPROVADA",
            ),
            self._has_blocking_failure(local_post_rules),
            not build_result.is_built,
            bool(local_build_issues),
            not xml_result.is_generated,
            xsd_result.is_invalid,
        ))
        local_pending = any((
            profile.blocks_apt,
            not row_validation.is_fully_verified,
            not event_validation.is_fully_verified,
            not reconciliation.is_fully_reconciled,
            not financial_validation.is_fully_verified,
            not references.is_fully_verified,
            self._has_rule_status(
                local_pre_rules,
                "REGRA NÃO EXECUTADA",
            ),
            self._has_rule_status(
                local_post_rules,
                "REGRA NÃO EXECUTADA",
            ),
            status_externo == ExternalValidationStatus.PENDING,
            status_historico
            == HistoricalValidationStatus.PENDING,
        ))
        if local_reproved:
            status_local = LocalValidationStatus.REPROVED
        else:
            status_local = LocalValidationStatus.APPROVED
        status_dependencias = self._dependent_status(
            status_externo,
            status_historico,
            has_additional_pending=local_pending,
        )
        status_xsd = (
            XsdValidationSummaryStatus.REPROVED
            if xsd_result.is_invalid
            else XsdValidationSummaryStatus.APPROVED
        )

        return self._decision(
            reasons,
            status_local=status_local,
            status_xsd=status_xsd,
            status_externo=status_externo,
            status_historico=status_historico,
            status_dependencias=status_dependencias,
        )

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
            status_local=(
                LocalValidationStatus.REPROVED
            ),
            status_xsd=XsdValidationSummaryStatus.NOT_EXECUTED,
            status_externo=ExternalValidationStatus.PENDING,
            status_historico=(
                HistoricalValidationStatus.PENDING
            ),
            status_dependencias=DependentValidationStatus.PENDING,
        )

    @staticmethod
    def _rules_with_execution_class(
        rules: Iterable[object],
        expected_value: str,
    ) -> tuple[object, ...]:
        return tuple(
            rule
            for rule in rules
            if getattr(
                getattr(rule, "definition", None),
                "execution_class",
                None,
            ) == expected_value
        )

    @staticmethod
    def _rule_status_value(rule: object) -> str:
        return str(getattr(rule, "status", ""))

    @classmethod
    def _has_rule_status(
        cls,
        rules: Iterable[object],
        expected_status: str,
    ) -> bool:
        return any(
            cls._rule_status_value(rule) == expected_status
            for rule in rules
        )

    @classmethod
    def _rule_codes_with_status(
        cls,
        rules: Iterable[object],
        expected_status: str,
    ) -> tuple[str, ...]:
        return tuple(
            str(getattr(rule, "code", "REGRA SEM CÓDIGO"))
            for rule in rules
            if cls._rule_status_value(rule) == expected_status
        )

    @classmethod
    def _has_blocking_failure(
        cls,
        rules: Iterable[object],
    ) -> bool:
        return any(
            bool(getattr(
                rule,
                "has_blocking_failure",
                cls._rule_status_value(rule) == "REPROVADA",
            ))
            for rule in rules
        )

    @classmethod
    def _external_status(
        cls,
        rules: tuple[object, ...],
    ) -> ExternalValidationStatus:
        if cls._has_rule_status(rules, "REPROVADA"):
            return ExternalValidationStatus.REPROVED
        if cls._has_rule_status(
            rules,
            "REGRA NÃO EXECUTADA",
        ):
            return ExternalValidationStatus.PENDING
        if cls._has_rule_status(rules, "APROVADA"):
            return ExternalValidationStatus.APPROVED
        return ExternalValidationStatus.APPROVED

    @classmethod
    def _historical_status(
        cls,
        rules: tuple[object, ...],
    ) -> HistoricalValidationStatus:
        if cls._has_rule_status(rules, "REPROVADA"):
            return HistoricalValidationStatus.REPROVED
        if cls._has_rule_status(
            rules,
            "REGRA NÃO EXECUTADA",
        ):
            return HistoricalValidationStatus.PENDING
        if cls._has_rule_status(rules, "APROVADA"):
            return HistoricalValidationStatus.APPROVED
        return HistoricalValidationStatus.APPROVED

    @staticmethod
    def _dependent_status(
        external: ExternalValidationStatus,
        historical: HistoricalValidationStatus,
        *,
        has_additional_pending: bool = False,
    ) -> DependentValidationStatus:
        if (
            external == ExternalValidationStatus.REPROVED
            or historical == HistoricalValidationStatus.REPROVED
        ):
            return DependentValidationStatus.REPROVED
        if (
            has_additional_pending
            or external == ExternalValidationStatus.PENDING
            or historical == HistoricalValidationStatus.PENDING
        ):
            return DependentValidationStatus.PENDING
        return DependentValidationStatus.APPROVED

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

    @classmethod
    def _decision(
        cls,
        reasons: Iterable[FinalStatusReason],
        *,
        status_local: LocalValidationStatus,
        status_xsd: XsdValidationSummaryStatus,
        status_externo: ExternalValidationStatus,
        status_historico: HistoricalValidationStatus,
        status_dependencias: DependentValidationStatus,
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
                status_local=status_local,
                status_xsd=status_xsd,
                status_externo=status_externo,
                status_historico=status_historico,
                status_dependencias=status_dependencias,
                general_status=GeneralValidationStatus.TECHNICAL_FAILURE,
                message=(
                    "A execução terminou com falha "
                    f"técnica{stage_text}."
                ),
                reasons=tuple(unique),
            )

        if (
            status_local == LocalValidationStatus.REPROVED
            or status_xsd == XsdValidationSummaryStatus.REPROVED
            or status_dependencias == DependentValidationStatus.REPROVED
        ):
            general_status = GeneralValidationStatus.REPROVED
        elif (
            status_xsd == XsdValidationSummaryStatus.NOT_EXECUTED
            or status_dependencias == DependentValidationStatus.PENDING
        ):
            general_status = GeneralValidationStatus.PENDING
        else:
            general_status = GeneralValidationStatus.APPROVED

        is_apt = general_status == GeneralValidationStatus.APPROVED

        if not is_apt:
            return FinalStatusDecision(
                status=FinalExecutionStatus.NOT_APT,
                status_local=status_local,
                status_xsd=status_xsd,
                status_externo=status_externo,
                status_historico=status_historico,
                status_dependencias=status_dependencias,
                general_status=general_status,
                message=cls._status_message(
                    status_local,
                    status_xsd,
                    status_dependencias,
                    general_status,
                ),
                reasons=tuple(unique),
            )

        return FinalStatusDecision(
            status=FinalExecutionStatus.APT,
            status_local=status_local,
            status_xsd=status_xsd,
            status_externo=status_externo,
            status_historico=status_historico,
            status_dependencias=status_dependencias,
            general_status=general_status,
            message=(
                "XML válido no XSD e sem erros "
                "impeditivos locais ou regras pendentes."
            ),
            reasons=tuple(unique),
        )

    @staticmethod
    def _status_message(
        status_local: LocalValidationStatus,
        status_xsd: XsdValidationSummaryStatus,
        status_dependencias: DependentValidationStatus,
        general_status: GeneralValidationStatus,
    ) -> str:
        return (
            f"Validações locais: {status_local.value}; "
            f"Validação XSD: {status_xsd.value}; "
            "Validações externas ou históricas: "
            f"{status_dependencias.value}; "
            f"Resultado geral: {general_status.value}; "
            "Motivo final: aptidão regulatória completa não "
            "comprovada."
        )


def consolidate_final_status(
    **kwargs,
) -> FinalStatusDecision:
    """Atalho funcional para a consolidação completa."""

    return FinalStatusService().evaluate_complete(
        **kwargs
    )
