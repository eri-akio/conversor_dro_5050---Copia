"""Coleta e padronização das ocorrências da execução."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Iterable

from src.domain.base_row import (
    BaseRowsNormalizationResult,
)
from src.domain.base_row_validation import (
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.conversion import (
    ConversionIssue,
    FinalStatusDecision,
)
from src.domain.event_classification import (
    ConsolidatedCalculationResult,
    EventClassificationResult,
)
from src.domain.document_header import DocumentHeader
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
    DependentValidationStatus,
    ExternalValidationStatus,
    ExecutionReportData,
    FinalExecutionStatus,
    GeneralValidationStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    ReportOccurrenceStatus,
    ReportRecord,
    ReportRuleSummary,
    XsdValidationSummaryStatus,
)
from src.domain.rule_reconciliation import (
    RuleReconciliationResult,
)
from src.domain.xml_generation import (
    XmlGenerationResult,
)
from src.domain.xsd_validation import (
    XsdValidationResult,
)


REPORTABLE_STATUSES = {
    RuleExecutionStatus.FAILED,
    RuleExecutionStatus.NOT_EXECUTED,
}


def _text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return format(value, "f")

    if isinstance(value, (tuple, list, dict, set)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
            sort_keys=True,
        )

    return str(value)


def _pairs_text(
    pairs: Iterable[tuple[str, Any]],
) -> str | None:
    values = {
        key: value
        for key, value in pairs
    }

    if not values:
        return None

    return json.dumps(
        values,
        ensure_ascii=False,
        default=str,
        sort_keys=True,
    )


def _join(values: Iterable[Any]) -> str | None:
    normalized = tuple(
        str(value)
        for value in values
        if value is not None and str(value) != ""
    )

    return ", ".join(normalized) if normalized else None


class ExecutionReportCollector:
    """Converte todos os resultados em um modelo único de relatório."""

    def collect(
        self,
        *,
        started_at: datetime,
        finished_at: datetime,
        input_path: str | Path,
        header: DocumentHeader,
        profile: RegulatoryVersion,
        normalization: BaseRowsNormalizationResult,
        classification: EventClassificationResult,
        consolidated: ConsolidatedCalculationResult,
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
        status_decision: FinalStatusDecision | None = None,
        execution_id: str | None = None,
    ) -> ExecutionReportData:
        input_file = Path(input_path).expanduser().resolve()
        xml_path = xsd_result.final_xml_path
        execution_id = execution_id or (
            "DRO5050-"
            + started_at.strftime("%Y%m%d%H%M%S%f")
        )

        if status_decision is None:
            final_status, final_message = (
                self._final_status(
                    profile=profile,
                    pre_processing=pre_processing,
                    post_processing=post_processing,
                    build_result=build_result,
                    xml_result=xml_result,
                    xsd_result=xsd_result,
                )
            )
        else:
            final_status = status_decision.status
            final_message = status_decision.message

        if status_decision is None:
            status_local = (
                LocalValidationStatus.APPROVED
                if final_status == FinalExecutionStatus.APT
                else LocalValidationStatus.REPROVED
            )
            status_xsd = (
                XsdValidationSummaryStatus.APPROVED
                if xsd_result.is_valid
                else XsdValidationSummaryStatus.REPROVED
            )
            status_externo = ExternalValidationStatus.APPROVED
            status_historico = HistoricalValidationStatus.APPROVED
            status_dependencias = DependentValidationStatus.APPROVED
            general_status = (
                GeneralValidationStatus.APPROVED
                if final_status == FinalExecutionStatus.APT
                else GeneralValidationStatus.REPROVED
            )
        else:
            status_local = status_decision.status_local
            status_xsd = status_decision.status_xsd
            status_externo = status_decision.status_externo
            status_historico = status_decision.status_historico
            status_dependencias = status_decision.status_dependencias
            general_status = status_decision.general_status

        records: list[ReportRecord] = []
        common = {
            "execution_id": execution_id,
            "executed_at": finished_at,
            "final_result": final_status,
            "input_file": str(input_file),
            "xml_file": (
                str(xml_path)
                if xml_path is not None
                else None
            ),
            "version": profile.code,
        }

        records.extend(
            self._normalization_records(
                normalization,
                common,
            )
        )
        records.extend(
            self._classification_records(
                classification,
                common,
            )
        )
        records.extend(
            self._consolidated_calculation_records(
                consolidated,
                common,
            )
        )
        records.extend(
            self._row_rule_records(
                row_validation,
                common,
            )
        )
        records.extend(
            self._event_rule_records(
                "AGRUPAMENTO",
                grouping.rule_results,
                common,
            )
        )
        records.extend(
            self._reconciliation_records(
                reconciliation,
                common,
            )
        )
        records.extend(
            self._event_rule_records(
                "CONSISTÊNCIA DO EVENTO",
                event_validation.rule_results,
                common,
            )
        )
        records.extend(
            self._event_rule_records(
                "VALIDAÇÃO FINANCEIRA",
                financial_validation.rule_results,
                common,
            )
        )
        records.extend(
            self._reference_records(
                references,
                common,
            )
        )
        records.extend(
            self._regulatory_records(
                "PRÉ-PROCESSAMENTO",
                pre_processing.rule_results,
                common,
            )
        )
        records.extend(
            self._regulatory_records(
                "PÓS-PROCESSAMENTO",
                post_processing.rule_results,
                common,
            )
        )
        records.extend(
            self._build_records(
                build_result,
                common,
            )
        )
        records.extend(
            self._xml_records(
                xml_result,
                common,
            )
        )
        records.extend(
            self._xsd_records(
                xsd_result,
                common,
            )
        )

        if status_decision is not None:
            records.extend(
                self._status_decision_records(
                    status_decision,
                    common,
                )
            )

        records = self._deduplicate(records)

        pre_rules = tuple(
            self._pre_rule_summary(result)
            for result in pre_processing.rule_results
        )
        post_rules = tuple(
            self._post_rule_summary(result)
            for result in post_processing.rule_results
        )

        metrics = (
            ("Linhas normalizadas", normalization.row_count),
            (
                "Linhas inválidas",
                normalization.invalid_row_count,
            ),
            ("Eventos agrupados", grouping.event_count),
            (
                "Eventos consolidados",
                (
                    build_result.document.consolidated_event_count
                    if build_result.document is not None
                    else 0
                ),
            ),
            (
                "Eventos com conflito",
                grouping.invalid_event_count,
            ),
            (
                "Contabilizações",
                sum(
                    len(event.accountings)
                    for event in grouping.events
                ),
            ),
            (
                "Sistemas cadastrados",
                len(references.systems.records),
            ),
            (
                "Contas internas cadastradas",
                len(references.accounts.records),
            ),
            (
                "Críticas pré-processamento",
                pre_processing.rule_count,
            ),
            (
                "Críticas pré não executadas",
                len(pre_processing.not_executed_rules),
            ),
            (
                "Críticas pós-processamento",
                post_processing.rule_count,
            ),
            (
                "Críticas pós não executadas",
                len(post_processing.not_executed_rules),
            ),
            ("Situação XSD", xsd_result.status.value),
            ("Ocorrências reportadas", len(records)),
        )

        return ExecutionReportData(
            execution_id=execution_id,
            started_at=started_at,
            finished_at=finished_at,
            input_path=input_file,
            xml_path=xml_path,
            xsd_path=xsd_result.xsd_path,
            data_base=header.data_base,
            profile_code=profile.code,
            status_local=status_local,
            status_xsd=status_xsd,
            status_externo=status_externo,
            status_historico=status_historico,
            status_dependencias=status_dependencias,
            general_status=general_status,
            final_status=final_status,
            final_message=final_message,
            records=tuple(records),
            pre_rules=pre_rules,
            post_rules=post_rules,
            metrics=metrics,
        )

    def collect_interrupted(
        self,
        *,
        started_at: datetime,
        finished_at: datetime,
        input_path: str | Path,
        status_decision: FinalStatusDecision,
        issues: Iterable[ConversionIssue],
        execution_id: str,
        data_base: str = "NÃO DISPONÍVEL",
        profile_code: str = "NÃO SELECIONADO",
        xml_path: Path | None = None,
        xsd_path: Path | None = None,
        metrics: Iterable[
            tuple[str, str | int]
        ] = (),
    ) -> ExecutionReportData:
        """Cria dados do relatório mesmo quando o fluxo termina cedo."""

        input_file = Path(input_path).expanduser().resolve()
        issue_list = tuple(issues)
        records = tuple(
            ReportRecord(
                execution_id=execution_id,
                executed_at=finished_at,
                final_result=status_decision.status,
                input_file=str(input_file),
                xml_file=(
                    str(xml_path)
                    if xml_path is not None
                    else None
                ),
                stage=issue.stage.value,
                sheet_name=issue.sheet_name,
                row_numbers=_join(issue.row_numbers),
                id_evento=issue.id_evento,
                columns=_join(issue.columns),
                original_value=_text(
                    issue.original_value
                ),
                normalized_value=_text(
                    issue.normalized_value
                )
                or _pairs_text(issue.details),
                rule_code=issue.code,
                rule_description=(
                    "Interrupção do serviço de conversão"
                ),
                source=issue.source,
                version=profile_code,
                severity=issue.severity,
                status=(
                    "FALHA TÉCNICA"
                    if issue.is_technical
                    else "REPROVADA"
                ),
                suggestion=issue.suggestion,
                message=issue.message,
                dependency=issue.dependency,
            )
            for issue in issue_list
        )

        base_metrics = (
            ("Etapa interrompida", (
                issue_list[0].stage.value
                if issue_list
                else "NÃO IDENTIFICADA"
            )),
            ("Ocorrências reportadas", len(records)),
        )

        return ExecutionReportData(
            execution_id=execution_id,
            started_at=started_at,
            finished_at=finished_at,
            input_path=input_file,
            xml_path=xml_path,
            xsd_path=xsd_path,
            data_base=data_base,
            profile_code=profile_code,
            status_local=status_decision.status_local,
            status_xsd=status_decision.status_xsd,
            status_externo=status_decision.status_externo,
            status_historico=status_decision.status_historico,
            status_dependencias=status_decision.status_dependencias,
            general_status=status_decision.general_status,
            final_status=status_decision.status,
            final_message=status_decision.message,
            records=records,
            pre_rules=(),
            post_rules=(),
            metrics=(
                *tuple(metrics),
                *base_metrics,
            ),
        )

    @staticmethod
    def _final_status(
        *,
        profile: RegulatoryVersion,
        pre_processing: PreProcessingValidationResult,
        post_processing: PostProcessingValidationResult,
        build_result: DocumentBuildResult,
        xml_result: XmlGenerationResult,
        xsd_result: XsdValidationResult,
    ) -> tuple[FinalExecutionStatus, str]:
        if xsd_result.has_technical_failure:
            return (
                FinalExecutionStatus.TECHNICAL_FAILURE,
                "A validação XSD não pôde ser concluída.",
            )

        blockers: list[str] = []

        if profile.blocks_apt:
            blockers.append(
                "conflito documental do perfil"
            )
        if not pre_processing.is_locally_valid:
            blockers.append(
                "crítica de pré-processamento reprovada"
            )
        if pre_processing.not_executed_rules:
            blockers.append(
                "crítica de pré-processamento não executada"
            )
        if not post_processing.is_locally_valid:
            blockers.append(
                "crítica de pós-processamento reprovada"
            )
        if post_processing.not_executed_rules:
            blockers.append(
                "crítica de pós-processamento não executada"
            )
        if build_result.blocks_apt:
            blockers.append(
                "impedimento na montagem do documento"
            )
        if xml_result.blocks_apt:
            blockers.append(
                "XML gerado como diagnóstico"
            )
        if xsd_result.is_invalid:
            blockers.append(
                "XML inválido no XSD"
            )
        if xsd_result.blocks_apt and not xsd_result.is_invalid:
            blockers.append(
                "bloqueio anterior preservado no resultado XSD"
            )

        if blockers:
            return (
                FinalExecutionStatus.NOT_APT,
                "; ".join(dict.fromkeys(blockers)) + ".",
            )

        return (
            FinalExecutionStatus.APT,
            (
                "XML válido no XSD e sem erros impeditivos "
                "locais ou regras pendentes."
            ),
        )

    @staticmethod
    def _normalization_records(
        result: BaseRowsNormalizationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        return [
            ReportRecord(
                **common,
                stage="NORMALIZAÇÃO",
                sheet_name=result.sheet_name,
                row_numbers=str(issue.row_number),
                id_evento=None,
                columns=issue.column_name,
                original_value=_text(
                    issue.original_value
                ),
                normalized_value=_text(
                    issue.normalized_value
                ),
                rule_code=(
                    issue.rule_code or issue.code
                ),
                rule_description=(
                    "Normalização de campo da aba Base"
                ),
                source="Normalizador local",
                severity=issue.severity,
                status="REPROVADA",
                suggestion=None,
                message=issue.message,
                dependency=None,
            )
            for issue in result.issues
        ]

    @staticmethod
    def _classification_records(
        result: EventClassificationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        """Registra a decisão exclusiva para cada ``idEvento``."""

        columns = (
            "categoriaNivel1",
            "totalPerdaEfetiva",
            "totalProvisao",
            "perdaBrutaAcumulada",
            "riscoNaoCoberto",
            "primeiraDataContabilizacao",
            "blocoDestino",
        )
        return [
                ReportRecord(
                    **common,
                    stage="CLASSIFICAÇÃO DOS EVENTOS",
                    sheet_name="Base",
                    row_numbers=_join(item.row_numbers),
                    id_evento=item.event_id,
                    columns=_join(columns),
                    original_value=None,
                    normalized_value=_pairs_text(
                        (
                            (columns[0], item.category_level_1),
                            (columns[1], item.total_loss),
                            (columns[2], item.total_provision),
                            (columns[3], item.gross_accumulated_loss),
                            (columns[4], item.uncovered_risk),
                            (columns[5], item.first_accounting_date),
                            (columns[6], item.destination.value),
                        )
                    ),
                    rule_code=item.rule_code,
                    rule_description="Classificação pelos limiares",
                    source="INTERNA",
                    severity=(
                        "ERRO IMPEDITIVO"
                        if item.destination.value == "NÃO CLASSIFICADO"
                        else "INFORMAÇÃO"
                    ),
                    status=(
                        "REPROVADA"
                        if item.destination.value == "NÃO CLASSIFICADO"
                        else "APROVADA"
                    ),
                    suggestion=None,
                    message=item.message,
                    dependency=None,
                )
            for item in result.classifications
        ]

    @staticmethod
    def _consolidated_calculation_records(
        result: ConsolidatedCalculationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        """Registra os sete campos calculados de cada categoria."""

        return [
            ReportRecord(
                **common,
                stage="CÁLCULO DOS CONSOLIDADOS",
                sheet_name="Base",
                row_numbers=_join(event.source_rows),
                id_evento=_join(event.source_event_ids),
                columns=(
                    "categoriaNivel1Consol, numEventosTotalConsol, "
                    "numEventosSemestreConsol, perdaEfetivaTotalConsol, "
                    "perdaEfetivaSemestreConsol, provisaoTotalConsol, "
                    "provisaoSemestreConsol"
                ),
                original_value=None,
                normalized_value=_pairs_text(
                    tuple(event.as_xml_attributes().items())
                    + (("idEventos", event.source_event_ids),)
                ),
                rule_code="CONS-GRUPO-001",
                rule_description=(
                    "Agrupamento dos consolidados por categoriaNivel1"
                ),
                source="INTERNA",
                severity="INFORMAÇÃO",
                status="APROVADA",
                suggestion=None,
                message=(
                    "Grupo consolidado calculado exclusivamente a partir "
                    "dos eventos da aba Base."
                ),
                dependency=None,
            )
            for event in result.events
        ]

    @staticmethod
    def _row_rule_records(
        result: BaseRowsValidationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        records: list[ReportRecord] = []

        for item in result.rule_results:
            if item.status not in REPORTABLE_STATUSES:
                continue

            records.append(
                ReportRecord(
                    **common,
                    stage="VALIDAÇÃO POR LINHA",
                    sheet_name="Base",
                    row_numbers=str(item.row_number),
                    id_evento=item.id_evento,
                    columns=_join(item.columns),
                    original_value=_pairs_text(
                        item.original_values
                    ),
                    normalized_value=_pairs_text(
                        item.normalized_values
                    ),
                    rule_code=item.code,
                    rule_description=item.description,
                    source=item.source,
                    severity=item.severity,
                    status=item.status.value,
                    suggestion=item.suggestion,
                    message=item.message,
                    dependency=None,
                )
            )

        return records

    @staticmethod
    def _event_rule_records(
        stage: str,
        results: Iterable[Any],
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        records: list[ReportRecord] = []

        for item in results:
            if item.status not in REPORTABLE_STATUSES:
                continue

            records.append(
                ReportRecord(
                    **common,
                    stage=stage,
                    sheet_name="Base",
                    row_numbers=_join(
                        item.row_numbers
                    ),
                    id_evento=item.id_evento,
                    columns=_join(item.columns),
                    original_value=None,
                    normalized_value=_pairs_text(
                        item.values
                    ),
                    rule_code=item.code,
                    rule_description=item.description,
                    source=item.source,
                    severity=item.severity,
                    status=item.status.value,
                    suggestion=item.suggestion,
                    message=item.message,
                    dependency=None,
                )
            )

        return records

    @staticmethod
    def _reference_records(
        result: ReferenceTablesValidationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        records: list[ReportRecord] = []

        for item in result.rule_results:
            if item.status not in REPORTABLE_STATUSES:
                continue

            row_numbers = tuple(
                dict.fromkeys(
                    (
                        *item.row_numbers,
                        *(
                            (
                                item.accounting_row_number,
                            )
                            if (
                                item.accounting_row_number
                                is not None
                            )
                            else ()
                        ),
                    )
                )
            )

            records.append(
                ReportRecord(
                    **common,
                    stage="TABELAS DE REFERÊNCIA",
                    sheet_name=item.sheet_name,
                    row_numbers=_join(row_numbers),
                    id_evento=item.id_evento,
                    columns=_join(item.columns),
                    original_value=None,
                    normalized_value=_pairs_text(
                        item.values
                    ),
                    rule_code=item.code,
                    rule_description=item.description,
                    source=item.source,
                    severity=item.severity,
                    status=item.status.value,
                    suggestion=item.suggestion,
                    message=item.message,
                    dependency=None,
                )
            )

        return records

    @staticmethod
    def _regulatory_records(
        stage: str,
        results: Iterable[Any],
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        records: list[ReportRecord] = []

        for rule in results:
            if rule.status not in REPORTABLE_STATUSES:
                continue

            for evidence in rule.evidences:
                if (
                    evidence.status
                    not in REPORTABLE_STATUSES
                ):
                    continue

                definition = rule.definition
                records.append(
                    ReportRecord(
                        **common,
                        stage=stage,
                        sheet_name=getattr(
                            evidence,
                            "sheet_name",
                            None,
                        )
                        or (
                            "Base"
                            if evidence.row_numbers
                            else None
                        ),
                        row_numbers=_join(
                            evidence.row_numbers
                        ),
                        id_evento=evidence.id_evento,
                        columns=_join(
                            evidence.columns
                        ),
                        original_value=_pairs_text(
                            getattr(
                                evidence,
                                "original_values",
                                (),
                            )
                        ),
                        normalized_value=_pairs_text(
                            evidence.values
                        ),
                        rule_code=rule.code,
                        rule_description=(
                            rule.description
                        ),
                        source=evidence.source_stage,
                        severity=evidence.severity,
                        status=evidence.status.value,
                        suggestion=(
                            evidence.suggestion
                        ),
                        message=evidence.message,
                        dependency=(
                            definition.dependency
                        ),
                    )
                )

        return records

    @staticmethod
    def _build_records(
        result: DocumentBuildResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        records: list[ReportRecord] = []
        for issue in result.issues:
            values = dict(issue.values)
            records.append(
                ReportRecord(
                    **common,
                    stage="MONTAGEM DO DOCUMENTO",
                    sheet_name=str(
                        values.get("aba")
                        or "Base"
                    ),
                    row_numbers=_join(issue.row_numbers),
                    id_evento=issue.event_id,
                    columns=_join(issue.fields),
                    original_value=(
                        None
                        if values.get("valorOriginal") is None
                        else str(values["valorOriginal"])
                    ),
                    normalized_value=(
                        None
                        if values.get("valorNormalizado") is None
                        else str(values["valorNormalizado"])
                    ),
                    rule_code=issue.code,
                    rule_description="Montagem dos objetos finais",
                    source=issue.source,
                    severity=issue.severity,
                    status=(
                        "REPROVADA"
                        if issue.blocks_apt
                        else "INFORMAÇÃO"
                    ),
                    suggestion=(
                        None
                        if values.get("sugestao") is None
                        else str(values["sugestao"])
                    ),
                    message=issue.message,
                    dependency=None,
                )
            )
        return records

    @staticmethod
    def _xml_records(
        result: XmlGenerationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        return [
            ReportRecord(
                **common,
                stage="GERAÇÃO DO XML",
                sheet_name=None,
                row_numbers=None,
                id_evento=None,
                columns=None,
                original_value=None,
                normalized_value=_pairs_text(
                    issue.details
                ),
                rule_code=issue.code,
                rule_description="Geração do XML",
                source=issue.source,
                severity=issue.severity,
                status=(
                    "REPROVADA"
                    if issue.blocks_apt
                    else "INFORMAÇÃO"
                ),
                suggestion=None,
                message=issue.message,
                dependency=None,
            )
            for issue in result.issues
        ]

    @staticmethod
    def _xsd_records(
        result: XsdValidationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        return [
            ReportRecord(
                **common,
                stage="VALIDAÇÃO XSD",
                sheet_name=None,
                row_numbers=(
                    str(issue.line)
                    if issue.line is not None
                    else None
                ),
                id_evento=None,
                columns=issue.xpath,
                original_value=None,
                normalized_value=None,
                rule_code=issue.code,
                rule_description=(
                    "Validação com o XSD selecionado"
                ),
                source=issue.source,
                severity=issue.severity,
                status=result.status.value,
                suggestion=None,
                message=issue.message,
                dependency=str(result.xsd_path),
            )
            for issue in result.issues
        ]

    @staticmethod
    def _status_decision_records(
        decision: FinalStatusDecision,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        return [
            ReportRecord(
                **common,
                stage="STATUS FINAL",
                sheet_name=None,
                row_numbers=None,
                id_evento=None,
                columns=None,
                original_value=None,
                normalized_value=_pairs_text(
                    reason.details
                ),
                rule_code=reason.code,
                rule_description=(
                    "Motivo da classificação final"
                ),
                source=reason.source,
                severity=reason.severity,
                status=(
                    ReportOccurrenceStatus.PENDING.value
                    if reason.severity == "REGRA NÃO EXECUTADA"
                    else (
                        ReportOccurrenceStatus.REPROVED.value
                        if reason.blocks_apt
                        else ReportOccurrenceStatus.APPROVED.value
                    )
                ),
                suggestion=None,
                message=reason.message,
                dependency=None,
            )
            for reason in decision.reasons
        ]

    @staticmethod
    def _reconciliation_records(
        result: RuleReconciliationResult,
        common: dict[str, Any],
    ) -> list[ReportRecord]:
        return [
            ReportRecord(
                **common,
                stage=record.execution_stage,
                sheet_name="Base",
                row_numbers=str(record.excel_row),
                id_evento=record.event_id,
                columns=None,
                original_value=record.provisional_status.value,
                normalized_value=record.definitive_status.value,
                rule_code=record.rule_code,
                rule_description=(
                    "Reconciliação de regra adiada"
                ),
                source=record.origin,
                severity=(
                    "ERRO IMPEDITIVO"
                    if record.blocks_apt
                    else "INFORMAÇÃO"
                ),
                status=record.provisional_status.value,
                suggestion=None,
                message=(
                    f"{record.reason} Resultado definitivo: "
                    f"{record.definitive_message}"
                ),
                dependency=record.dependency,
                scope=record.scope,
                definitive_result=(
                    record.definitive_status.value
                ),
            )
            for record in result.records
        ]

    @staticmethod
    def _pre_rule_summary(
        result: Any,
    ) -> ReportRuleSummary:
        return ReportRuleSummary(
            phase="PRÉ-PROCESSAMENTO",
            code=result.code,
            official_type=(
                result.definition.official_type
            ),
            description=result.description,
            evaluated_fields=(
                result.definition.confronted_base
            ),
            source_base=(
                result.definition.confronted_base
            ),
            start_label=(
                result.definition.start_label
            ),
            scope=result.definition.scope,
            execution_class=(
                result.definition.execution_class.value
            ),
            dependency=result.definition.dependency,
            provider=result.definition.provider.value,
            status=result.status.value,
            evidence_count=len(result.evidences),
            failed_evidence_count=sum(
                evidence.status
                == RuleExecutionStatus.FAILED
                for evidence in result.evidences
            ),
            not_executed_evidence_count=sum(
                evidence.status
                == RuleExecutionStatus.NOT_EXECUTED
                for evidence in result.evidences
            ),
        )

    @staticmethod
    def _post_rule_summary(
        result: Any,
    ) -> ReportRuleSummary:
        return ReportRuleSummary(
            phase="PÓS-PROCESSAMENTO",
            code=result.code,
            official_type=(
                result.definition.official_type
            ),
            description=result.description,
            evaluated_fields=(
                result.definition.evaluated_fields
            ),
            source_base="DRO",
            start_label="Não informado na fonte",
            scope=result.definition.scope,
            execution_class=(
                result.definition.execution_class.value
            ),
            dependency=result.definition.dependency,
            provider=result.definition.provider.value,
            status=result.status.value,
            evidence_count=len(result.evidences),
            failed_evidence_count=sum(
                evidence.status
                == RuleExecutionStatus.FAILED
                for evidence in result.evidences
            ),
            not_executed_evidence_count=sum(
                evidence.status
                == RuleExecutionStatus.NOT_EXECUTED
                for evidence in result.evidences
            ),
        )

    @staticmethod
    def _deduplicate(
        records: list[ReportRecord],
    ) -> list[ReportRecord]:
        unique: list[ReportRecord] = []
        seen: set[tuple[Any, ...]] = set()

        for record in records:
            key = (
                record.stage,
                record.row_numbers,
                record.id_evento,
                record.columns,
                record.rule_code,
                record.status,
                record.message,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(record)

        return unique


def collect_execution_report(
    **kwargs: Any,
) -> ExecutionReportData:
    """Atalho funcional do coletor padrão."""

    return ExecutionReportCollector().collect(**kwargs)


def collect_interrupted_report(
    **kwargs: Any,
) -> ExecutionReportData:
    """Atalho funcional para término antecipado."""

    return ExecutionReportCollector().collect_interrupted(
        **kwargs
    )
