"""Construção do objeto final do Documento 5050.

O construtor não gera XML. Ele transforma os objetos validados das
etapas anteriores em classes finais que espelham os blocos dos XSDs.

O roteamento e o cálculo dos consolidados ocorrem antes deste builder.
Ele recebe os IDs individualizados e os grupos consolidados finais, sem
repetir regras de classificação.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from src.domain.base_row_validation import (
    BaseRowKind,
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.document_header import DocumentHeader
from src.domain.document_model import (
    DocumentBuildIssue,
    DocumentBuildResult,
    FinalAccounting,
    FinalConsolidatedEvent,
    FinalDocument,
    FinalIndividualEvent,
    FinalInternalAccount,
    FinalProbability,
    FinalSourceSystem,
    UnsupportedProfileValue,
)
from src.domain.event_financial import (
    EventsFinancialValidationResult,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventsValidationResult,
    GroupedAccounting,
    GroupedEvent,
)
from src.domain.reference_tables import (
    ReferenceTableRecord,
    ReferenceTablesValidationResult,
)
from src.domain.pre_processing import (
    PreProcessingValidationResult,
)
from src.domain.post_processing import (
    PostProcessingValidationResult,
)
from src.domain.regulatory_version import (
    RegulatoryVersion,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"

REQUIRED_EVENT_FIELDS = (
    "categoriaNivel1",
    "tipoAvaliacao",
    "unidadeNegocio",
    "dataOcorrencia",
    "totalPerdaEfetiva",
    "totalRecuperado",
    "naturezaContingencia",
    "codSistemaOrigem",
    "codigoEventoOrigem",
    "idBacen",
)

REQUIRED_ACCOUNTING_FIELDS = (
    "dataContabilizacao",
    "valorPerdaEfetiva",
)

FUTURE_ONLY_FIELDS = (
    "idEventoAgregador",
    "dataExclusao",
    "motivoExclusao",
)


class DocumentBuilder:
    """Monta os objetos finais sem corrigir dados silenciosamente."""

    def build(
        self,
        *,
        header: DocumentHeader,
        profile: RegulatoryVersion,
        row_validation: BaseRowsValidationResult,
        grouping: EventGroupingResult,
        event_validation: EventsValidationResult,
        financial_validation: (
            EventsFinancialValidationResult
        ),
        references: ReferenceTablesValidationResult,
        pre_processing_validation: (
            PreProcessingValidationResult | None
        ) = None,
        post_processing_validation: (
            PostProcessingValidationResult | None
        ) = None,
        consolidated_events: Iterable[
            FinalConsolidatedEvent
        ] = (),
        individualized_event_ids: Iterable[str] | None = None,
    ) -> DocumentBuildResult:
        issues: list[DocumentBuildIssue] = []

        profile_codes = {
            row_validation.profile_code,
            grouping.profile_code,
            event_validation.profile_code,
            financial_validation.profile_code,
        }

        if pre_processing_validation is not None:
            profile_codes.add(
                pre_processing_validation.profile_code
            )

        if post_processing_validation is not None:
            profile_codes.add(
                post_processing_validation.profile_code
            )

        if profile_codes != {profile.code}:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-BUILD-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "Os resultados anteriores pertencem "
                        "a perfis regulatórios diferentes."
                    ),
                    source="Regra interna de montagem",
                    blocks_xml=True,
                    blocks_apt=True,
                    values=(
                        (
                            "perfisEncontrados",
                            tuple(sorted(profile_codes)),
                        ),
                        (
                            "perfilEsperado",
                            profile.code,
                        ),
                    ),
                )
            )
            return DocumentBuildResult(
                document=None,
                issues=tuple(issues),
            )

        blocking_dependencies = self._dependency_issues(
            row_validation=row_validation,
            grouping=grouping,
            event_validation=event_validation,
            financial_validation=financial_validation,
            references=references,
        )
        issues.extend(blocking_dependencies)

        if any(
            issue.code == "DOC-BUILD-002"
            for issue in blocking_dependencies
        ):
            return DocumentBuildResult(
                document=None,
                issues=tuple(issues),
            )

        issues.extend(
            self._not_executed_issues(
                row_validation=row_validation,
                event_validation=event_validation,
                financial_validation=financial_validation,
                references=references,
                pre_processing_validation=(
                    pre_processing_validation
                ),
                post_processing_validation=(
                    post_processing_validation
                ),
            )
        )

        if pre_processing_validation is not None:
            issues.extend(
                self._pre_processing_issues(
                    pre_processing_validation
                )
            )

        if post_processing_validation is not None:
            issues.extend(
                self._post_processing_issues(
                    post_processing_validation
                )
            )

        if profile.blocks_apt:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-VER-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O perfil selecionado possui conflito "
                        "documental e não pode resultar em APTO."
                    ),
                    source="Matriz de versões",
                    blocks_xml=True,
                    blocks_apt=True,
                    values=(
                        ("perfil", profile.code),
                        (
                            "conflitos",
                            profile.conflict_codes,
                        ),
                    ),
                )
            )

        final_events: list[FinalIndividualEvent] = []
        unsupported_values: list[
            UnsupportedProfileValue
        ] = []

        individualized_ids = (
            None
            if individualized_event_ids is None
            else frozenset(individualized_event_ids)
        )

        for event in grouping.events:
            if event.row_kind == BaseRowKind.EXCLUDED:
                unsupported_values.append(
                    self._unsupported_event(event)
                )
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-EVT-EXC-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "O evento excluído não possui elemento "
                            "compatível nos XSDs fornecidos."
                        ),
                        source=(
                            "Instruções 12/2026 e XSD 06/2025"
                        ),
                        blocks_xml=True,
                        blocks_apt=True,
                        event_id=event.id_evento,
                        row_numbers=event.row_numbers,
                        fields=FUTURE_ONLY_FIELDS,
                    )
                )
                continue

            if (
                individualized_ids is not None
                and event.id_evento not in individualized_ids
            ):
                continue

            final_event, event_issues = (
                self._build_individual_event(event)
            )
            issues.extend(event_issues)

            if final_event is not None:
                final_events.append(final_event)

            future_values = self._future_values(event)
            if future_values:
                unsupported_values.append(
                    UnsupportedProfileValue(
                        event_id=event.id_evento,
                        source_rows=event.row_numbers,
                        values=future_values,
                    )
                )
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-EVT-FUT-001",
                        severity=SEVERITY_WARNING,
                        message=(
                            "Campos de 12/2026 foram preservados, "
                            "mas não serão enviados ao XSD atual."
                        ),
                        source=(
                            "Instruções 12/2026 e XSD 06/2025"
                        ),
                        blocks_xml=profile.blocks_apt,
                        blocks_apt=True,
                        event_id=event.id_evento,
                        row_numbers=event.row_numbers,
                        fields=tuple(
                            name
                            for name, _ in future_values
                        ),
                        values=future_values,
                    )
                )

        consolidated = tuple(consolidated_events)
        issues.extend(
            self._validate_consolidated_events(consolidated)
        )

        source_systems, system_issues = (
            self._build_source_systems(
                grouping,
                references,
            )
        )
        issues.extend(system_issues)

        internal_accounts, account_issues = (
            self._build_internal_accounts(
                grouping,
                references,
            )
        )
        issues.extend(account_issues)

        if not final_events:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CARD-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O XSD exige ao menos um evento "
                        "individualizado."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                )
            )

        if not consolidated:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CONS-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O XSD exige ao menos um evento "
                        "consolidado. Nenhum evento válido da "
                        "Base foi classificado como consolidado."
                    ),
                    source=(
                        "XSD e contrato de entrada do projeto"
                    ),
                    blocks_xml=True,
                    blocks_apt=True,
                    fields=(
                        "categoriaNivel1Consol",
                        "numEventosTotalConsol",
                        "numEventosSemestreConsol",
                        "perdaEfetivaTotalConsol",
                        "perdaEfetivaSemestreConsol",
                        "provisaoTotalConsol",
                        "provisaoSemestreConsol",
                    ),
                )
            )

        if not source_systems:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CARD-002",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O bloco final não possui sistemas "
                        "de origem utilizados."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                )
            )

        if not internal_accounts:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CARD-003",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O bloco final não possui contas "
                        "internas utilizadas."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                )
            )

        document = FinalDocument(
            header=header,
            profile_code=profile.code,
            xsd_path=profile.xsd_path,
            individualized_events=tuple(final_events),
            consolidated_events=consolidated,
            source_systems=source_systems,
            internal_accounts=internal_accounts,
            unsupported_profile_values=tuple(
                unsupported_values
            ),
        )

        return DocumentBuildResult(
            document=document,
            issues=tuple(issues),
        )

    @staticmethod
    def _dependency_issues(
        *,
        row_validation: BaseRowsValidationResult,
        grouping: EventGroupingResult,
        event_validation: EventsValidationResult,
        financial_validation: (
            EventsFinancialValidationResult
        ),
        references: ReferenceTablesValidationResult,
    ) -> list[DocumentBuildIssue]:
        failed_layers: list[tuple[str, int]] = []

        if not row_validation.is_locally_valid:
            failed_layers.append(
                (
                    "validação local das linhas",
                    row_validation.invalid_row_count,
                )
            )
        if not grouping.is_valid:
            failed_layers.append(
                (
                    "agrupamento dos eventos",
                    grouping.invalid_event_count,
                )
            )
        if not event_validation.is_valid:
            failed_layers.append(
                (
                    "consistência dos eventos",
                    event_validation.invalid_event_count,
                )
            )
        if not financial_validation.is_valid:
            failed_layers.append(
                (
                    "validação financeira",
                    financial_validation.invalid_event_count,
                )
            )
        if not references.is_valid:
            failed_layers.append(
                (
                    "tabelas de referência",
                    len(references.failed_rules),
                )
            )

        if not failed_layers:
            return []

        return [
            DocumentBuildIssue(
                code="DOC-BUILD-002",
                severity=SEVERITY_BLOCKING_ERROR,
                message=(
                    "O documento final não pode ser montado "
                    "porque existem falhas impeditivas em "
                    "etapas anteriores."
                ),
                source="Regra interna de montagem",
                blocks_xml=True,
                blocks_apt=True,
                values=tuple(failed_layers),
            )
        ]

    @staticmethod
    def _not_executed_issues(
        *,
        row_validation: BaseRowsValidationResult,
        event_validation: EventsValidationResult,
        financial_validation: (
            EventsFinancialValidationResult
        ),
        references: ReferenceTablesValidationResult,
        pre_processing_validation: (
            PreProcessingValidationResult | None
        ),
        post_processing_validation: (
            PostProcessingValidationResult | None
        ),
    ) -> list[DocumentBuildIssue]:
        """Mantém somente regras ainda não cobertas depois.

        As regras de linha DRO001312, DRO001314 e DRO001452 são
        reavaliadas no nível do evento. Por isso, deixam de ser
        pendentes quando existe resultado posterior para o mesmo
        código.
        """

        later_codes = {
            result.code
            for result in (
                *event_validation.rule_results,
                *financial_validation.rule_results,
                *references.rule_results,
            )
        }

        pending_codes: dict[str, int] = {}

        for result in row_validation.not_executed_rules:
            if (
                pre_processing_validation is not None
                and result.code.startswith("DRO001")
            ):
                continue
            if result.code in later_codes:
                continue
            pending_codes[result.code] = (
                pending_codes.get(result.code, 0) + 1
            )

        for result in (
            *event_validation.not_executed_rules,
            *financial_validation.not_executed_rules,
            *references.not_executed_rules,
        ):
            if (
                pre_processing_validation is not None
                and result.code.startswith("DRO001")
            ):
                continue
            if (
                post_processing_validation is not None
                and result.code.startswith("DRO000")
            ):
                continue
            pending_codes[result.code] = (
                pending_codes.get(result.code, 0) + 1
            )

        return [
            DocumentBuildIssue(
                code="DOC-REGRA-NE-001",
                severity=SEVERITY_NOT_EXECUTED,
                message=(
                    f"A regra {code} ainda não foi "
                    f"verificada em {count} ocorrência(s)."
                ),
                source=(
                    "Resultados acumulados das validações"
                ),
                blocks_xml=False,
                blocks_apt=True,
                values=(
                    ("codigoRegra", code),
                    ("quantidade", count),
                ),
            )
            for code, count in sorted(
                pending_codes.items()
            )
        ]

    @staticmethod
    def _pre_processing_issues(
        validation: PreProcessingValidationResult,
    ) -> list[DocumentBuildIssue]:
        issues: list[DocumentBuildIssue] = []

        for result in validation.not_executed_rules:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-PRE-NE-001",
                    severity=SEVERITY_NOT_EXECUTED,
                    message=(
                        f"A crítica {result.code} não foi "
                        "completamente verificada."
                    ),
                    source=(
                        "Críticas oficiais de pré-processamento"
                    ),
                    blocks_xml=False,
                    blocks_apt=True,
                    row_numbers=result.row_numbers,
                    fields=tuple(
                        dict.fromkeys(
                            column
                            for evidence in result.evidences
                            for column in evidence.columns
                        )
                    ),
                    values=(
                        ("codigoRegra", result.code),
                        (
                            "dependencia",
                            result.definition.dependency,
                        ),
                        (
                            "quantidadeEvidencias",
                            len(result.evidences),
                        ),
                    ),
                )
            )

        return issues

    @staticmethod
    def _post_processing_issues(
        validation: PostProcessingValidationResult,
    ) -> list[DocumentBuildIssue]:
        issues: list[DocumentBuildIssue] = []

        for result in validation.blocking_failed_rules:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-POS-ERR-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        f"A crítica {result.code} foi reprovada."
                    ),
                    source=(
                        "Críticas oficiais de pós-processamento"
                    ),
                    blocks_xml=False,
                    blocks_apt=True,
                    row_numbers=result.row_numbers,
                    fields=tuple(
                        dict.fromkeys(
                            column
                            for evidence in result.evidences
                            for column in evidence.columns
                        )
                    ),
                    values=(
                        ("codigoRegra", result.code),
                        (
                            "quantidadeEvidencias",
                            len(result.evidences),
                        ),
                    ),
                )
            )

        for result in validation.warning_failed_rules:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-POS-AVISO-001",
                    severity=SEVERITY_WARNING,
                    message=(
                        f"A crítica de esclarecimento "
                        f"{result.code} encontrou ocorrência."
                    ),
                    source=(
                        "Críticas oficiais de pós-processamento"
                    ),
                    blocks_xml=False,
                    blocks_apt=False,
                    row_numbers=result.row_numbers,
                    fields=tuple(
                        dict.fromkeys(
                            column
                            for evidence in result.evidences
                            for column in evidence.columns
                        )
                    ),
                    values=(
                        ("codigoRegra", result.code),
                        (
                            "quantidadeEvidencias",
                            len(result.evidences),
                        ),
                    ),
                )
            )

        for result in validation.not_executed_rules:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-POS-NE-001",
                    severity=SEVERITY_NOT_EXECUTED,
                    message=(
                        f"A crítica {result.code} não foi "
                        "completamente verificada."
                    ),
                    source=(
                        "Críticas oficiais de pós-processamento"
                    ),
                    blocks_xml=False,
                    blocks_apt=True,
                    row_numbers=result.row_numbers,
                    fields=tuple(
                        dict.fromkeys(
                            column
                            for evidence in result.evidences
                            for column in evidence.columns
                        )
                    ),
                    values=(
                        ("codigoRegra", result.code),
                        (
                            "dependencia",
                            result.definition.dependency,
                        ),
                        (
                            "quantidadeEvidencias",
                            len(result.evidences),
                        ),
                    ),
                )
            )

        return issues

    def _build_individual_event(
        self,
        event: GroupedEvent,
    ) -> tuple[
        FinalIndividualEvent | None,
        list[DocumentBuildIssue],
    ]:
        issues: list[DocumentBuildIssue] = []

        missing = tuple(
            field_name
            for field_name in REQUIRED_EVENT_FIELDS
            if not event.get_field(
                field_name
            ).is_resolved
        )

        if missing:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-EVT-ATTR-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O evento não possui todos os "
                        "atributos obrigatórios resolvidos."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                    event_id=event.id_evento,
                    row_numbers=event.row_numbers,
                    fields=missing,
                )
            )
            return None, issues

        probabilities: list[FinalProbability] = []
        for probability in event.probabilities:
            if (
                probability.has_conflict
                or probability.value_risk is None
            ):
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-PROB-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Probabilidade não resolvida para "
                            "montagem do documento."
                        ),
                        source="XSD",
                        blocks_xml=True,
                        blocks_apt=True,
                        event_id=event.id_evento,
                        row_numbers=(
                            probability.source_rows
                        ),
                        fields=(
                            "probabilidadePerda",
                            "valorRisco",
                        ),
                    )
                )
                continue

            probabilities.append(
                FinalProbability(
                    probability=(
                        probability.probability_code
                    ),
                    value_risk=probability.value_risk,
                    source_rows=probability.source_rows,
                )
            )

        accountings: list[FinalAccounting] = []
        for accounting in event.accountings:
            final_accounting, issue = (
                self._build_accounting(
                    event,
                    accounting,
                )
            )
            if issue is not None:
                issues.append(issue)
                continue
            assert final_accounting is not None
            accountings.append(final_accounting)

        occurrence_date = event.get_value(
            "dataOcorrencia"
        )
        total_loss = event.get_value(
            "totalPerdaEfetiva"
        )
        total_recovery = event.get_value(
            "totalRecuperado"
        )

        if (
            not isinstance(occurrence_date, date)
            or not isinstance(total_loss, Decimal)
            or not isinstance(total_recovery, Decimal)
        ):
            issues.append(
                DocumentBuildIssue(
                    code="DOC-EVT-TIPO-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O evento possui tipo interno "
                        "incompatível com o objeto final."
                    ),
                    source="Regra interna de montagem",
                    blocks_xml=True,
                    blocks_apt=True,
                    event_id=event.id_evento,
                    row_numbers=event.row_numbers,
                    fields=(
                        "dataOcorrencia",
                        "totalPerdaEfetiva",
                        "totalRecuperado",
                    ),
                )
            )
            return None, issues

        return (
            FinalIndividualEvent(
                event_id=event.id_evento,
                category_level_1=(
                    event.get_serialized_value(
                        "categoriaNivel1"
                    )
                    or ""
                ),
                category_level_2=(
                    event.get_serialized_value(
                        "categoriaNivel2"
                    )
                ),
                assessment_type=(
                    event.get_serialized_value(
                        "tipoAvaliacao"
                    )
                    or ""
                ),
                business_unit=(
                    event.get_serialized_value(
                        "unidadeNegocio"
                    )
                    or ""
                ),
                discovery_date=self._optional_date(
                    event,
                    "dataDescoberta",
                ),
                occurrence_date=occurrence_date,
                total_loss=total_loss,
                total_provision=self._optional_decimal(
                    event,
                    "totalProvisao",
                ),
                total_recovery=total_recovery,
                total_risk=self._optional_decimal(
                    event,
                    "valorTotalRisco",
                ),
                contingency_nature=(
                    event.get_serialized_value(
                        "naturezaContingencia"
                    )
                    or ""
                ),
                source_system_code=(
                    event.get_serialized_value(
                        "codSistemaOrigem"
                    )
                    or ""
                ),
                origin_event_code=(
                    event.get_serialized_value(
                        "codigoEventoOrigem"
                    )
                    or ""
                ),
                event_description=(
                    event.get_serialized_value(
                        "descricaoEvento"
                    )
                ),
                associated_risk=(
                    event.get_serialized_value(
                        "riscoAssociado"
                    )
                ),
                socioenvironmental_risk=(
                    event.get_serialized_value(
                        "ligacaoRiscoSocioambiental"
                    )
                ),
                cyber_risk=(
                    event.get_serialized_value(
                        "ligadoRiscoCibernetico"
                    )
                ),
                discontinued_business=(
                    event.get_serialized_value(
                        "negocioDescontinuado"
                    )
                ),
                bacen_id=(
                    event.get_serialized_value(
                        "idBacen"
                    )
                    or ""
                ),
                source_rows=event.row_numbers,
                probabilities=tuple(probabilities),
                accountings=tuple(accountings),
            ),
            issues,
        )

    @staticmethod
    def _build_accounting(
        event: GroupedEvent,
        accounting: GroupedAccounting,
    ) -> tuple[
        FinalAccounting | None,
        DocumentBuildIssue | None,
    ]:
        missing = tuple(
            field_name
            for field_name in REQUIRED_ACCOUNTING_FIELDS
            if accounting.get_serialized_value(
                field_name
            ) is None
        )

        accounting_date = accounting.get_value(
            "dataContabilizacao"
        )
        loss_value = accounting.get_value(
            "valorPerdaEfetiva"
        )

        if (
            missing
            or not isinstance(accounting_date, date)
            or not isinstance(loss_value, Decimal)
        ):
            return (
                None,
                DocumentBuildIssue(
                    code="DOC-CONT-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "Contabilização sem os atributos "
                        "obrigatórios resolvidos."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                    event_id=event.id_evento,
                    row_numbers=(
                        accounting.row_number,
                    ),
                    fields=(
                        missing
                        or REQUIRED_ACCOUNTING_FIELDS
                    ),
                ),
            )

        return (
            FinalAccounting(
                accounting_date=accounting_date,
                loss_value=loss_value,
                source_row=accounting.row_number,
                internal_debit_account=(
                    accounting.get_serialized_value(
                        "contaBalAnaliticoDebito"
                    )
                ),
                internal_credit_account=(
                    accounting.get_serialized_value(
                        "contaBalAnaliticoCredito"
                    )
                ),
                cosif_debit_account=(
                    accounting.get_serialized_value(
                        "contaCosifDebito"
                    )
                ),
                cosif_credit_account=(
                    accounting.get_serialized_value(
                        "contaCosifCredito"
                    )
                ),
                provision_value=(
                    accounting.get_value(
                        "valorProvisao"
                    )
                    if isinstance(
                        accounting.get_value(
                            "valorProvisao"
                        ),
                        Decimal,
                    )
                    else None
                ),
                recovery_value=(
                    accounting.get_value(
                        "valorRecuperacao"
                    )
                    if isinstance(
                        accounting.get_value(
                            "valorRecuperacao"
                        ),
                        Decimal,
                    )
                    else None
                ),
                recovery_source=(
                    accounting.get_serialized_value(
                        "fonteRecuperacao"
                    )
                ),
            ),
            None,
        )

    @staticmethod
    def _validate_consolidated_events(
        events: tuple[FinalConsolidatedEvent, ...],
    ) -> list[DocumentBuildIssue]:
        issues: list[DocumentBuildIssue] = []

        if len(events) > 8:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CONS-002",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "O XSD permite no máximo oito "
                        "eventos consolidados."
                    ),
                    source="XSD",
                    blocks_xml=True,
                    blocks_apt=True,
                    values=(
                        ("quantidade", len(events)),
                    ),
                )
            )

        categories: dict[str, int] = {}
        for event in events:
            categories[event.category_level_1] = (
                categories.get(
                    event.category_level_1,
                    0,
                )
                + 1
            )

            invalid_values = (
                event.category_level_1
                not in {
                    str(number)
                    for number in range(1, 9)
                }
                or event.total_event_count < 0
                or event.semester_event_count < 0
            )
            if invalid_values:
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-CONS-003",
                        severity=(
                            SEVERITY_BLOCKING_ERROR
                        ),
                        message=(
                            "Evento consolidado possui "
                            "categoria ou contagem inválida."
                        ),
                        source="XSD",
                        blocks_xml=True,
                        blocks_apt=True,
                        fields=(
                            "categoriaNivel1Consol",
                            "numEventosTotalConsol",
                            "numEventosSemestreConsol",
                        ),
                        values=(
                            (
                                "categoria",
                                event.category_level_1,
                            ),
                            (
                                "numEventosTotalConsol",
                                event.total_event_count,
                            ),
                            (
                                "numEventosSemestreConsol",
                                event.semester_event_count,
                            ),
                        ),
                    )
                )

        duplicates = tuple(
            category
            for category, count in categories.items()
            if count > 1
        )
        if duplicates:
            issues.append(
                DocumentBuildIssue(
                    code="DOC-CONS-004",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "Há mais de um evento consolidado "
                        "para a mesma categoria de nível 1."
                    ),
                    source=(
                        "Instruções de preenchimento"
                    ),
                    blocks_xml=True,
                    blocks_apt=True,
                    fields=(
                        "categoriaNivel1Consol",
                    ),
                    values=(
                        (
                            "categoriasDuplicadas",
                            duplicates,
                        ),
                    ),
                )
            )

        return issues

    def _build_source_systems(
        self,
        grouping: EventGroupingResult,
        references: ReferenceTablesValidationResult,
    ) -> tuple[
        tuple[FinalSourceSystem, ...],
        list[DocumentBuildIssue],
    ]:
        used_codes = self._used_system_codes(grouping)
        records = references.systems.unique_valid_records
        final: list[FinalSourceSystem] = []
        issues: list[DocumentBuildIssue] = []

        for code in used_codes:
            record = records.get(code)
            if record is None or record.name is None:
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-SIS-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Sistema utilizado não possui "
                            "registro único e válido."
                        ),
                        source=(
                            "Tabela Sistemas_Origem"
                        ),
                        blocks_xml=True,
                        blocks_apt=True,
                        values=(
                            ("codigoSistema", code),
                        ),
                    )
                )
                continue

            final.append(
                FinalSourceSystem(
                    code=code,
                    name=record.name,
                    source_row=record.row_number,
                )
            )

        return tuple(final), issues

    def _build_internal_accounts(
        self,
        grouping: EventGroupingResult,
        references: ReferenceTablesValidationResult,
    ) -> tuple[
        tuple[FinalInternalAccount, ...],
        list[DocumentBuildIssue],
    ]:
        used_codes = self._used_account_codes(grouping)
        records = references.accounts.unique_valid_records
        final: list[FinalInternalAccount] = []
        issues: list[DocumentBuildIssue] = []

        for code in used_codes:
            record = records.get(code)
            if record is None or record.name is None:
                issues.append(
                    DocumentBuildIssue(
                        code="DOC-CONTA-001",
                        severity=SEVERITY_BLOCKING_ERROR,
                        message=(
                            "Conta utilizada não possui "
                            "registro único e válido."
                        ),
                        source="Tabela Contas_Internas",
                        blocks_xml=True,
                        blocks_apt=True,
                        values=(
                            ("codigoConta", code),
                        ),
                    )
                )
                continue

            final.append(
                FinalInternalAccount(
                    code=code,
                    name=record.name,
                    source_row=record.row_number,
                )
            )

        return tuple(final), issues

    @staticmethod
    def _used_system_codes(
        grouping: EventGroupingResult,
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                code
                for event in grouping.events
                if (
                    code
                    := event.get_serialized_value(
                        "codSistemaOrigem"
                    )
                )
            )
        )

    @staticmethod
    def _used_account_codes(
        grouping: EventGroupingResult,
    ) -> tuple[str, ...]:
        codes: list[str] = []

        for event in grouping.events:
            for accounting in event.accountings:
                for field_name in (
                    "contaBalAnaliticoDebito",
                    "contaBalAnaliticoCredito",
                ):
                    code = (
                        accounting
                        .get_serialized_value(
                            field_name
                        )
                    )
                    if code is not None:
                        codes.append(code)

        return tuple(dict.fromkeys(codes))

    @staticmethod
    def _future_values(
        event: GroupedEvent,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            (
                field_name,
                serialized,
            )
            for field_name in FUTURE_ONLY_FIELDS
            if (
                serialized
                := event.get_serialized_value(
                    field_name
                )
            )
            is not None
        )

    @staticmethod
    def _unsupported_event(
        event: GroupedEvent,
    ) -> UnsupportedProfileValue:
        values = tuple(
            (
                field_name,
                serialized,
            )
            for field_name in FUTURE_ONLY_FIELDS
            if (
                serialized
                := event.get_serialized_value(
                    field_name
                )
            )
            is not None
        )

        return UnsupportedProfileValue(
            event_id=event.id_evento,
            source_rows=event.row_numbers,
            values=values,
        )

    @staticmethod
    def _optional_decimal(
        event: GroupedEvent,
        field_name: str,
    ) -> Decimal | None:
        value = event.get_value(field_name)
        return (
            value
            if isinstance(value, Decimal)
            else None
        )

    @staticmethod
    def _optional_date(
        event: GroupedEvent,
        field_name: str,
    ) -> date | None:
        value = event.get_value(field_name)
        return (
            value
            if isinstance(value, date)
            else None
        )


def build_final_document(
    *,
    header: DocumentHeader,
    profile: RegulatoryVersion,
    row_validation: BaseRowsValidationResult,
    grouping: EventGroupingResult,
    event_validation: EventsValidationResult,
    financial_validation: EventsFinancialValidationResult,
    references: ReferenceTablesValidationResult,
    pre_processing_validation: (
        PreProcessingValidationResult | None
    ) = None,
    post_processing_validation: (
        PostProcessingValidationResult | None
    ) = None,
    consolidated_events: Iterable[
        FinalConsolidatedEvent
    ] = (),
    individualized_event_ids: Iterable[str] | None = None,
) -> DocumentBuildResult:
    """Atalho funcional para o construtor padrão."""

    return DocumentBuilder().build(
        header=header,
        profile=profile,
        row_validation=row_validation,
        grouping=grouping,
        event_validation=event_validation,
        financial_validation=financial_validation,
        references=references,
        pre_processing_validation=(
            pre_processing_validation
        ),
        post_processing_validation=(
            post_processing_validation
        ),
        consolidated_events=consolidated_events,
        individualized_event_ids=individualized_event_ids,
    )
