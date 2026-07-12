"""Serviço completo de conversão XLSX → XML DRO 5050.

O serviço concentra a ordem das etapas, o tratamento de interrupções,
a decisão final e a geração dos artefatos. A interface de terminal e a
futura interface Tkinter devem chamar este serviço em vez de repetir o
pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar

from src.builders import build_final_document
from src.config import (
    OUTPUT_DIR,
)
from src.domain.conversion import (
    ConversionArtifacts,
    ConversionIssue,
    ConversionRequest,
    ConversionResult,
    ConversionStage,
    ConversionStageRecord,
    ConversionStageStatus,
    FinalStatusDecision,
    freeze_stage_outputs,
)
from src.domain.document_model import DocumentBuildIssue
from src.domain.reporting import (
    FinalExecutionStatus,
    ReportGenerationResult,
)
from src.mappers import group_base_rows
from src.normalizers.header_normalizer import (
    normalize_header,
)
from src.readers import (
    read_and_normalize_base,
    read_excel,
    read_header,
    read_reference_tables,
    validate_header_initial,
)
from src.services.event_classification_service import classify_events
from src.services.consolidated_event_calculator import (
    calculate_consolidated_events,
)
from src.reporters import (
    collect_execution_report,
    collect_interrupted_report,
)
from src.services.final_status_service import (
    FinalStatusService,
)
from src.services.reporting_service import (
    ReportingService,
)
from src.services.rule_reconciliation_service import (
    reconcile_deferred_rules,
)
from src.services.version_resolver import (
    resolve_version,
)
from src.services.xml_generation_service import (
    generate_xml,
)
from src.services.xsd_validation_service import (
    validate_generated_xml,
)
from src.validators import (
    validate_base_rows,
    validate_base_structure,
    validate_event_financials,
    validate_grouped_events,
    validate_post_processing,
    validate_pre_processing,
    validate_reference_tables,
)


T = TypeVar("T")


@dataclass(slots=True)
class _PipelineState:
    request: ConversionRequest
    execution_id: str
    started_at: datetime
    stage_records: list[ConversionStageRecord]
    issues: list[ConversionIssue]
    stage_outputs: dict[ConversionStage, Any]


@dataclass(frozen=True, slots=True)
class _StageExecutionError(Exception):
    stage: ConversionStage
    original_error: Exception


class ConversionService:
    """Executa o fluxo completo e retorna um único resultado."""

    def __init__(
        self,
        *,
        status_service: FinalStatusService | None = None,
        reporting_service: ReportingService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.status_service = (
            status_service or FinalStatusService()
        )
        self.reporting_service = (
            reporting_service or ReportingService()
        )
        self.clock = (
            clock or (lambda: datetime.now().astimezone())
        )

    def convert(
        self,
        request_or_path: ConversionRequest | str | Path,
        *,
        output_dir: str | Path = OUTPUT_DIR,
    ) -> ConversionResult:
        """Executa todas as etapas aplicáveis à remessa."""

        request = (
            request_or_path
            if isinstance(
                request_or_path,
                ConversionRequest,
            )
            else ConversionRequest.create(
                request_or_path,
                output_dir=output_dir,
            )
        )
        started_at = self.clock()
        state = _PipelineState(
            request=request,
            execution_id=(
                "DRO5050-"
                + started_at.strftime("%Y%m%d%H%M%S%f")
            ),
            started_at=started_at,
            stage_records=[],
            issues=[],
            stage_outputs={},
        )

        data_base = "NÃO DISPONÍVEL"
        profile_code = "NÃO SELECIONADO"
        xsd_path: Path | None = None

        try:
            excel = self._execute(
                state,
                ConversionStage.READ_EXCEL,
                lambda: read_excel(request.input_path),
                "Arquivo Excel lido.",
            )

            raw_header = self._execute(
                state,
                ConversionStage.READ_HEADER,
                lambda: read_header(excel),
                "Aba Cabecalho lida.",
            )

            initial_header = self._execute(
                state,
                ConversionStage.VALIDATE_HEADER,
                lambda: validate_header_initial(
                    raw_header
                ),
                "Estrutura inicial do cabeçalho validada.",
            )

            if not initial_header.is_valid:
                self._mark_last_as_stopped(
                    state,
                    (
                        "O cabeçalho possui erros "
                        "impeditivos."
                    ),
                )
                issues = self._header_initial_issues(
                    raw_header,
                    initial_header,
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.VALIDATE_HEADER,
                    issues=issues,
                    technical=False,
                    data_base=self._raw_data_base(
                        raw_header
                    ),
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                )

            header_result = self._execute(
                state,
                ConversionStage.NORMALIZE_HEADER,
                lambda: normalize_header(raw_header),
                "Cabeçalho normalizado.",
            )

            if (
                not header_result.is_valid
                or header_result.header is None
            ):
                self._mark_last_as_stopped(
                    state,
                    (
                        "O cabeçalho não pôde ser "
                        "normalizado."
                    ),
                )
                issues = self._header_normalization_issues(
                    raw_header,
                    header_result,
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.NORMALIZE_HEADER,
                    issues=issues,
                    technical=False,
                    data_base=self._raw_data_base(
                        raw_header
                    ),
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                )

            header = header_result.header
            data_base = header.data_base

            version_selection = self._execute(
                state,
                ConversionStage.SELECT_VERSION,
                lambda: resolve_version(header),
                "Perfil regulatório selecionado pela dataBase.",
            )
            profile = version_selection.profile

            if (
                profile is None
                or version_selection.has_technical_failure
            ):
                technical = (
                    version_selection.has_technical_failure
                )
                self._mark_last_as_stopped(
                    state,
                    (
                        "A seleção de versão terminou "
                        "com falha técnica."
                        if technical
                        else (
                            "Nenhum perfil regulatório "
                            "aplicável foi selecionado."
                        )
                    ),
                    technical=technical,
                )
                issues = self._version_issues(
                    version_selection
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.SELECT_VERSION,
                    issues=issues,
                    technical=technical,
                    data_base=data_base,
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                )

            profile_code = profile.code
            xsd_path = profile.xsd_path

            structure = self._execute(
                state,
                ConversionStage.VALIDATE_BASE_STRUCTURE,
                lambda: validate_base_structure(
                    excel,
                    profile,
                ),
                "Estrutura da aba Base validada.",
            )

            if not structure.is_valid:
                self._mark_last_as_stopped(
                    state,
                    "A estrutura da Base é inválida.",
                )
                return self._finish_interrupted(
                    state,
                    stage=(
                        ConversionStage
                        .VALIDATE_BASE_STRUCTURE
                    ),
                    issues=self._base_structure_issues(
                        structure
                    ),
                    technical=False,
                    data_base=data_base,
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                    metrics=(
                        (
                            "Linhas encontradas",
                            structure.row_count,
                        ),
                        (
                            "Colunas ausentes",
                            len(
                                structure
                                .missing_columns
                            ),
                        ),
                    ),
                )

            normalization = self._execute(
                state,
                ConversionStage.NORMALIZE_BASE,
                lambda: read_and_normalize_base(
                    excel,
                    profile,
                ),
                "Linhas da Base normalizadas.",
            )

            if not normalization.is_valid:
                self._mark_last_as_stopped(
                    state,
                    "Existem valores inválidos na Base.",
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.NORMALIZE_BASE,
                    issues=self._normalization_issues(
                        normalization
                    ),
                    technical=False,
                    data_base=data_base,
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                    metrics=(
                        (
                            "Linhas normalizadas",
                            normalization.row_count,
                        ),
                        (
                            "Linhas inválidas",
                            normalization
                            .invalid_row_count,
                        ),
                    ),
                )

            row_validation = self._execute(
                state,
                ConversionStage.VALIDATE_ROWS,
                lambda: validate_base_rows(
                    normalization,
                    profile,
                ),
                "Obrigatoriedades e relações por linha validadas.",
            )

            grouping = self._execute(
                state,
                ConversionStage.GROUP_EVENTS,
                lambda: group_base_rows(
                    normalization,
                    row_validation,
                ),
                "Linhas agrupadas por idEvento.",
            )

            event_validation = self._execute(
                state,
                ConversionStage.VALIDATE_EVENTS,
                lambda: validate_grouped_events(
                    grouping,
                    profile,
                ),
                "Consistência dos eventos validada.",
            )

            reconciliation = self._execute(
                state,
                ConversionStage.RECONCILE_RULES,
                lambda: reconcile_deferred_rules(
                    row_validation=row_validation,
                    event_validation=event_validation,
                ),
                "Regras adiadas reconciliadas no nível do evento.",
            )

            financial_validation = self._execute(
                state,
                ConversionStage.VALIDATE_FINANCIALS,
                lambda: validate_event_financials(
                    grouping,
                    profile,
                ),
                "Totais, contabilizações e saldos validados.",
            )

            classification = self._execute(
                state,
                ConversionStage.CLASSIFY_EVENTS,
                lambda: classify_events(
                    grouping=grouping,
                    event_validation=event_validation,
                    financial_validation=financial_validation,
                ),
                "Eventos classificados entre os blocos do XML.",
            )

            consolidated = self._execute(
                state,
                ConversionStage.CALCULATE_CONSOLIDATED,
                lambda: calculate_consolidated_events(
                    data_base=header.data_base,
                    grouping=grouping,
                    classification=classification,
                    financial_validation=financial_validation,
                ),
                "Eventos consolidados calculados a partir da Base.",
            )

            references = self._execute(
                state,
                ConversionStage.VALIDATE_REFERENCES,
                lambda: validate_reference_tables(
                    read_reference_tables(excel),
                    grouping,
                ),
                "Sistemas e contas internas validados.",
            )

            pre_processing = self._execute(
                state,
                ConversionStage.PRE_PROCESSING,
                lambda: validate_pre_processing(
                    header=header,
                    profile=profile,
                    row_validation=row_validation,
                    grouping=grouping,
                    event_validation=event_validation,
                    references=references,
                ),
                "Críticas de pré-processamento executadas.",
            )

            post_processing = self._execute(
                state,
                ConversionStage.POST_PROCESSING,
                lambda: validate_post_processing(
                    header=header,
                    profile=profile,
                    grouping=grouping,
                    row_validation=row_validation,
                    financial_validation=(
                        financial_validation
                    ),
                    consolidated_events=consolidated.events,
                ),
                "Críticas de pós-processamento executadas.",
            )

            build_result = self._execute(
                state,
                ConversionStage.BUILD_DOCUMENT,
                lambda: build_final_document(
                    header=header,
                    profile=profile,
                    row_validation=row_validation,
                    grouping=grouping,
                    event_validation=event_validation,
                    financial_validation=(
                        financial_validation
                    ),
                    references=references,
                    pre_processing_validation=(
                        pre_processing
                    ),
                    post_processing_validation=(
                        post_processing
                    ),
                    consolidated_events=consolidated.events,
                    individualized_event_ids=(
                        classification.individualized_event_ids
                    ),
                ),
                "Objetos finais do documento construídos.",
            )

            calculation_issues = (
                *classification.issues,
                *consolidated.issues,
            )
            if calculation_issues:
                build_result = replace(
                    build_result,
                    issues=(
                        *build_result.issues,
                        *self._calculation_build_issues(
                            calculation_issues
                        ),
                    ),
                )
                state.stage_outputs[
                    ConversionStage.BUILD_DOCUMENT
                ] = build_result

            if not build_result.is_built:
                self._mark_last_as_stopped(
                    state,
                    (
                        "O documento final não pôde "
                        "ser construído."
                    ),
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.BUILD_DOCUMENT,
                    issues=self._build_issues(
                        build_result
                    ),
                    technical=False,
                    data_base=data_base,
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                )

            xml_result = self._execute(
                state,
                ConversionStage.GENERATE_XML,
                lambda: generate_xml(
                    build_result,
                    output_dir=request.output_dir,
                ),
                "Arquivo XML gerado.",
            )

            if not xml_result.is_generated:
                self._mark_last_as_stopped(
                    state,
                    "O arquivo XML não foi gerado.",
                )
                return self._finish_interrupted(
                    state,
                    stage=ConversionStage.GENERATE_XML,
                    issues=self._xml_issues(
                        xml_result
                    ),
                    technical=False,
                    data_base=data_base,
                    profile_code=profile_code,
                    xsd_path=xsd_path,
                )

            xsd_result = self._execute(
                state,
                ConversionStage.VALIDATE_XSD,
                lambda: validate_generated_xml(
                    xml_result,
                    profile,
                    data_base=header.data_base,
                ),
                "Validação XSD executada.",
            )

            decision_started = self.clock()
            decision = (
                self.status_service.evaluate_complete(
                    profile=profile,
                    row_validation=row_validation,
                    grouping=grouping,
                    event_validation=event_validation,
                    reconciliation=reconciliation,
                    financial_validation=(
                        financial_validation
                    ),
                    references=references,
                    pre_processing=pre_processing,
                    post_processing=post_processing,
                    build_result=build_result,
                    xml_result=xml_result,
                    xsd_result=xsd_result,
                )
            )
            decision_finished = self.clock()
            state.stage_outputs[
                ConversionStage.CONSOLIDATE_STATUS
            ] = decision
            state.stage_records.append(
                ConversionStageRecord(
                    stage=(
                        ConversionStage
                        .CONSOLIDATE_STATUS
                    ),
                    status=(
                        ConversionStageStatus.COMPLETED
                    ),
                    started_at=decision_started,
                    finished_at=decision_finished,
                    message=decision.message,
                    details=(
                        (
                            "status",
                            decision.status.value,
                        ),
                        (
                            "motivosBloqueantes",
                            len(
                                decision
                                .blocking_reasons
                            ),
                        ),
                    ),
                )
            )

            finished_at = self.clock()
            report_data = collect_execution_report(
                started_at=state.started_at,
                finished_at=finished_at,
                input_path=request.input_path,
                header=header,
                profile=profile,
                normalization=normalization,
                classification=classification,
                consolidated=consolidated,
                row_validation=row_validation,
                grouping=grouping,
                event_validation=event_validation,
                reconciliation=reconciliation,
                financial_validation=(
                    financial_validation
                ),
                references=references,
                pre_processing=pre_processing,
                post_processing=post_processing,
                build_result=build_result,
                xml_result=xml_result,
                xsd_result=xsd_result,
                status_decision=decision,
                execution_id=state.execution_id,
            )

            report_result, decision = (
                self._generate_reports(
                    state,
                    report_data=report_data,
                    current_decision=decision,
                )
            )

            final_path = (
                xsd_result.final_xml_path
                or xml_result.output_path
            )
            return self._result(
                state,
                decision=decision,
                xml_path=final_path,
                report_result=report_result,
            )

        except _StageExecutionError as stage_error:
            issue = self._exception_issue(
                stage_error.stage,
                stage_error.original_error,
            )
            state.issues.append(issue)
            return self._finish_interrupted(
                state,
                stage=stage_error.stage,
                issues=(issue,),
                technical=True,
                data_base=data_base,
                profile_code=profile_code,
                xsd_path=xsd_path,
            )

    def _execute(
        self,
        state: _PipelineState,
        stage: ConversionStage,
        action: Callable[[], T],
        success_message: str,
    ) -> T:
        started_at = self.clock()

        try:
            result = action()
        except Exception as error:
            finished_at = self.clock()
            state.stage_records.append(
                ConversionStageRecord(
                    stage=stage,
                    status=(
                        ConversionStageStatus
                        .TECHNICAL_FAILURE
                    ),
                    started_at=started_at,
                    finished_at=finished_at,
                    message=str(error),
                    details=(
                        (
                            "tipoExcecao",
                            type(error).__name__,
                        ),
                    ),
                )
            )
            raise _StageExecutionError(
                stage,
                error,
            ) from error

        finished_at = self.clock()
        state.stage_outputs[stage] = result
        state.stage_records.append(
            ConversionStageRecord(
                stage=stage,
                status=ConversionStageStatus.COMPLETED,
                started_at=started_at,
                finished_at=finished_at,
                message=success_message,
            )
        )
        return result

    def _finish_interrupted(
        self,
        state: _PipelineState,
        *,
        stage: ConversionStage,
        issues: tuple[ConversionIssue, ...],
        technical: bool,
        data_base: str,
        profile_code: str,
        xsd_path: Path | None,
        metrics: tuple[
            tuple[str, str | int],
            ...,
        ] = (),
    ) -> ConversionResult:
        for issue in issues:
            if issue not in state.issues:
                state.issues.append(issue)

        decision_started = self.clock()
        decision = self.status_service.evaluate_interrupted(
            stage=stage,
            issues=issues,
            technical=technical,
        )
        decision_finished = self.clock()
        state.stage_outputs[
            ConversionStage.CONSOLIDATE_STATUS
        ] = decision
        state.stage_records.append(
            ConversionStageRecord(
                stage=(
                    ConversionStage
                    .CONSOLIDATE_STATUS
                ),
                status=ConversionStageStatus.COMPLETED,
                started_at=decision_started,
                finished_at=decision_finished,
                message=decision.message,
                details=(
                    ("status", decision.status.value),
                ),
            )
        )

        report_data = collect_interrupted_report(
            started_at=state.started_at,
            finished_at=self.clock(),
            input_path=state.request.input_path,
            status_decision=decision,
            issues=issues,
            execution_id=state.execution_id,
            data_base=data_base,
            profile_code=profile_code,
            xsd_path=xsd_path,
            metrics=metrics,
        )

        report_result, decision = self._generate_reports(
            state,
            report_data=report_data,
            current_decision=decision,
        )

        return self._result(
            state,
            decision=decision,
            xml_path=None,
            report_result=report_result,
        )

    def _generate_reports(
        self,
        state: _PipelineState,
        *,
        report_data,
        current_decision: FinalStatusDecision,
    ) -> tuple[
        ReportGenerationResult | None,
        FinalStatusDecision,
    ]:
        started_at = self.clock()

        try:
            result = self.reporting_service.generate(
                report_data,
                output_dir=state.request.output_dir,
            )
        except Exception as error:
            finished_at = self.clock()
            issue = self._exception_issue(
                ConversionStage.GENERATE_REPORTS,
                error,
                default_code="CONV-REL-001",
            )
            state.issues.append(issue)
            state.stage_records.append(
                ConversionStageRecord(
                    stage=(
                        ConversionStage
                        .GENERATE_REPORTS
                    ),
                    status=(
                        ConversionStageStatus
                        .TECHNICAL_FAILURE
                    ),
                    started_at=started_at,
                    finished_at=finished_at,
                    message=issue.message,
                )
            )
            decision = (
                self.status_service.evaluate_interrupted(
                    stage=(
                        ConversionStage
                        .GENERATE_REPORTS
                    ),
                    issues=(issue,),
                    technical=True,
                )
            )
            state.stage_outputs[
                ConversionStage.CONSOLIDATE_STATUS
            ] = decision
            return None, decision

        finished_at = self.clock()
        state.stage_outputs[
            ConversionStage.GENERATE_REPORTS
        ] = result

        if result.issues:
            report_issues = tuple(
                ConversionIssue(
                    code=issue.code,
                    severity="FALHA TÉCNICA",
                    stage=(
                        ConversionStage
                        .GENERATE_REPORTS
                    ),
                    message=issue.message,
                    source="Serviço de relatório Excel",
                    blocks_apt=True,
                    details=(
                        (
                            "tipoSaida",
                            issue.output_type,
                        ),
                        (
                            "caminho",
                            str(issue.path)
                            if issue.path
                            else None,
                        ),
                    ),
                )
                for issue in result.issues
            )
            state.issues.extend(report_issues)
            state.stage_records.append(
                ConversionStageRecord(
                    stage=(
                        ConversionStage
                        .GENERATE_REPORTS
                    ),
                    status=(
                        ConversionStageStatus
                        .TECHNICAL_FAILURE
                    ),
                    started_at=started_at,
                    finished_at=finished_at,
                    message=(
                        "O relatório Excel não foi gerado."
                    ),
                    details=(
                        (
                            "falhas",
                            len(report_issues),
                        ),
                    ),
                )
            )
            decision = (
                self.status_service.evaluate_interrupted(
                    stage=(
                        ConversionStage
                        .GENERATE_REPORTS
                    ),
                    issues=report_issues,
                    technical=True,
                )
            )
            state.stage_outputs[
                ConversionStage.CONSOLIDATE_STATUS
            ] = decision
            return result, decision

        state.stage_records.append(
            ConversionStageRecord(
                stage=ConversionStage.GENERATE_REPORTS,
                status=ConversionStageStatus.COMPLETED,
                started_at=started_at,
                finished_at=finished_at,
                message=(
                    "Relatório XLSX gerado."
                ),
                details=(
                    (
                        "resultadoRegistrado",
                        current_decision.status.value,
                    ),
                ),
            )
        )
        return result, current_decision

    def _result(
        self,
        state: _PipelineState,
        *,
        decision: FinalStatusDecision,
        xml_path: Path | None,
        report_result: ReportGenerationResult | None,
    ) -> ConversionResult:
        reports = (
            report_result.artifacts
            if (
                report_result is not None
                and report_result.is_generated
            )
            else None
        )

        return ConversionResult(
            execution_id=state.execution_id,
            request=state.request,
            started_at=state.started_at,
            finished_at=self.clock(),
            decision=decision,
            stage_records=tuple(
                state.stage_records
            ),
            issues=tuple(state.issues),
            artifacts=ConversionArtifacts(
                xml_path=xml_path,
                reports=reports,
            ),
            stage_outputs=freeze_stage_outputs(
                state.stage_outputs
            ),
        )

    @staticmethod
    def _mark_last_as_stopped(
        state: _PipelineState,
        message: str,
        *,
        technical: bool = False,
    ) -> None:
        last = state.stage_records.pop()
        state.stage_records.append(
            replace(
                last,
                status=(
                    ConversionStageStatus
                    .TECHNICAL_FAILURE
                    if technical
                    else (
                        ConversionStageStatus
                        .STOPPED_NOT_APT
                    )
                ),
                message=message,
            )
        )

    @staticmethod
    def _raw_data_base(raw_header) -> str:
        value = raw_header.get_value(
            "dataBase",
            "NÃO DISPONÍVEL",
        )
        text = str(value).strip()

        if len(text) == 7 and text[4] == "-":
            return text

        return "NÃO DISPONÍVEL"

    @staticmethod
    def _header_initial_issues(
        raw_header,
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.VALIDATE_HEADER,
                message=issue.message,
                source="Validação inicial do cabeçalho",
                blocks_apt=True,
                sheet_name=raw_header.sheet_name,
                row_numbers=(raw_header.row_number,),
                columns=(
                    (issue.field_name,)
                    if issue.field_name
                    else ()
                ),
                original_value=issue.raw_value,
                details=(
                    ("coordenada", issue.coordinate),
                ),
            )
            for issue in result.issues
            if issue.blocks_processing
        )

    @staticmethod
    def _header_normalization_issues(
        raw_header,
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.NORMALIZE_HEADER,
                message=issue.message,
                source="Normalização do cabeçalho",
                blocks_apt=True,
                sheet_name=raw_header.sheet_name,
                row_numbers=(raw_header.row_number,),
                columns=(issue.field_name,),
                original_value=issue.original_value,
                normalized_value=(
                    issue.normalized_value
                ),
                details=(
                    ("coordenada", issue.coordinate),
                ),
            )
            for issue in result.issues
            if issue.blocks_processing
        )

    @staticmethod
    def _version_issues(
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.SELECT_VERSION,
                message=issue.message,
                source="Seleção automática da versão",
                blocks_apt=True,
                dependency=issue.dependency,
                details=(
                    (
                        "caminho",
                        str(issue.path)
                        if issue.path
                        else None,
                    ),
                ),
            )
            for issue in result.issues
            if issue.blocks_apt
            or issue.severity == "FALHA TÉCNICA"
        )

    @staticmethod
    def _base_structure_issues(
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=(
                    ConversionStage
                    .VALIDATE_BASE_STRUCTURE
                ),
                message=issue.message,
                source="Estrutura da aba Base",
                blocks_apt=True,
                sheet_name=result.sheet_name,
                columns=(
                    (issue.column_name,)
                    if issue.column_name
                    else ()
                ),
                suggestion=(
                    issue.suggested_column_name
                ),
                details=(
                    ("detalhes", issue.details),
                ),
            )
            for issue in result.issues
            if issue.blocks_processing
        )

    @staticmethod
    def _normalization_issues(
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.NORMALIZE_BASE,
                message=issue.message,
                source="Normalização da aba Base",
                blocks_apt=True,
                sheet_name=result.sheet_name,
                row_numbers=(issue.row_number,),
                columns=(
                    (issue.column_name,)
                    if issue.column_name
                    else ()
                ),
                original_value=issue.original_value,
                normalized_value=(
                    issue.normalized_value
                ),
            )
            for issue in result.blocking_issues
        )

    @staticmethod
    def _calculation_build_issues(
        issues,
    ) -> tuple[DocumentBuildIssue, ...]:
        """Propaga falhas internas de classificação e cálculo."""

        return tuple(
            DocumentBuildIssue(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                source=issue.source,
                blocks_xml=issue.blocks_processing,
                blocks_apt=issue.blocks_processing,
                event_id=issue.id_evento,
                row_numbers=issue.row_numbers,
                fields=issue.columns,
                values=issue.values,
            )
            for issue in issues
        )

    @staticmethod
    def _build_issues(
        result,
    ) -> tuple[ConversionIssue, ...]:
        return tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.BUILD_DOCUMENT,
                message=issue.message,
                source=issue.source,
                blocks_apt=True,
                row_numbers=issue.row_numbers,
                id_evento=issue.event_id,
                columns=issue.fields,
                details=issue.values,
            )
            for issue in result.issues
            if issue.blocks_xml or issue.blocks_apt
        )

    @staticmethod
    def _xml_issues(
        result,
    ) -> tuple[ConversionIssue, ...]:
        issues = tuple(
            ConversionIssue(
                code=issue.code,
                severity=issue.severity,
                stage=ConversionStage.GENERATE_XML,
                message=issue.message,
                source=issue.source,
                blocks_apt=True,
                details=issue.details,
            )
            for issue in result.issues
        )

        if issues:
            return issues

        return (
            ConversionIssue(
                code="CONV-XML-001",
                severity="ERRO IMPEDITIVO",
                stage=ConversionStage.GENERATE_XML,
                message=(
                    "A geração terminou sem criar "
                    "um arquivo XML."
                ),
                source="Serviço completo de conversão",
                blocks_apt=True,
            ),
        )

    @staticmethod
    def _exception_issue(
        stage: ConversionStage,
        error: Exception,
        *,
        default_code: str = "CONV-TEC-001",
    ) -> ConversionIssue:
        code = getattr(error, "code", default_code)
        message = getattr(error, "message", str(error))
        raw_details = getattr(error, "details", ())

        if isinstance(raw_details, dict):
            details = tuple(raw_details.items())
        else:
            details = tuple(raw_details or ())

        return ConversionIssue(
            code=str(code),
            severity="FALHA TÉCNICA",
            stage=stage,
            message=str(message),
            source=stage.value,
            blocks_apt=True,
            details=details,
            exception_type=type(error).__name__,
        )


def convert_excel(
    input_path: str | Path,
    *,
    output_dir: str | Path = OUTPUT_DIR,
) -> ConversionResult:
    """Atalho funcional usado pelo terminal e pela futura interface."""

    return ConversionService().convert(
        input_path,
        output_dir=output_dir,
    )
