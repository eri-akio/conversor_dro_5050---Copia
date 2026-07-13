"""Testes da consolidação única do status final."""

from __future__ import annotations

from types import SimpleNamespace

from src.domain.conversion import (
    ConversionIssue,
    ConversionStage,
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
from src.services.final_status_service import (
    FinalStatusService,
)


def valid_context() -> dict[str, object]:
    return {
        "profile": SimpleNamespace(
            blocks_apt=False,
            code="TESTE",
            conflict_codes=(),
        ),
        "row_validation": SimpleNamespace(
            is_locally_valid=True,
            is_fully_verified=True,
        ),
        "grouping": SimpleNamespace(
            is_valid=True,
        ),
        "event_validation": SimpleNamespace(
            is_valid=True,
            is_fully_verified=True,
        ),
        "reconciliation": SimpleNamespace(
            is_fully_reconciled=True,
            unresolved_records=(),
            failed_records=(),
            blocks_apt=False,
        ),
        "financial_validation": SimpleNamespace(
            is_valid=True,
            is_fully_verified=True,
        ),
        "references": SimpleNamespace(
            is_valid=True,
            is_fully_verified=True,
        ),
        "pre_processing": SimpleNamespace(
            is_locally_valid=True,
            not_executed_rules=(),
            rule_results=(),
        ),
        "post_processing": SimpleNamespace(
            is_locally_valid=True,
            not_executed_rules=(),
            warning_failed_rules=(),
            rule_results=(),
        ),
        "build_result": SimpleNamespace(
            is_built=True,
            blocks_apt=False,
            apt_blocking_issues=(),
        ),
        "xml_result": SimpleNamespace(
            is_generated=True,
            blocks_apt=False,
        ),
        "xsd_result": SimpleNamespace(
            has_technical_failure=False,
            technical_issues=(),
            is_invalid=False,
            xsd_path="teste.xsd",
        ),
    }


def regulatory_rule(
    code: str,
    status: str,
    execution_class: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        code=code,
        status=status,
        has_blocking_failure=(status == "REPROVADA"),
        definition=SimpleNamespace(
            execution_class=execution_class,
        ),
    )


def test_consolidated_status_domains_match_the_decision_matrix() -> None:
    assert {status.value for status in LocalValidationStatus} == {
        "APROVADO",
        "REPROVADO",
    }
    expected_dependencies = {"APROVADO", "PENDENTE", "REPROVADO"}
    assert {status.value for status in ExternalValidationStatus} == (
        expected_dependencies
    )
    assert {status.value for status in HistoricalValidationStatus} == (
        expected_dependencies
    )
    assert {status.value for status in DependentValidationStatus} == (
        expected_dependencies
    )
    assert {status.value for status in GeneralValidationStatus} == {
        "APROVADO",
        "PENDENTE",
        "REPROVADO",
        "FALHA TÉCNICA",
    }


def test_complete_valid_context_is_apt() -> None:
    decision = FinalStatusService().evaluate_complete(
        **valid_context()
    )

    assert decision.status == FinalExecutionStatus.APT
    assert decision.status_local == LocalValidationStatus.APPROVED
    assert decision.status_xsd == (
        XsdValidationSummaryStatus.APPROVED
    )
    assert decision.status_externo == (
        ExternalValidationStatus.APPROVED
    )
    assert decision.status_historico == (
        HistoricalValidationStatus.APPROVED
    )
    assert decision.status_dependencias == DependentValidationStatus.APPROVED
    assert decision.general_status == GeneralValidationStatus.APPROVED
    assert decision.is_apt
    assert not decision.blocking_reasons


def test_pending_and_invalid_rules_are_not_apt() -> None:
    context = valid_context()
    pending_rule = regulatory_rule(
        "DRO001001",
        "REGRA NÃO EXECUTADA",
        "LOCAL",
    )
    context["pre_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(pending_rule,),
        rule_results=(pending_rule,),
    )
    context["xsd_result"] = SimpleNamespace(
        has_technical_failure=False,
        technical_issues=(),
        is_invalid=True,
        xsd_path="teste.xsd",
    )

    decision = FinalStatusService().evaluate_complete(
        **context
    )

    assert decision.status == FinalExecutionStatus.NOT_APT
    assert decision.status_local == LocalValidationStatus.REPROVED
    assert {
        reason.code
        for reason in decision.blocking_reasons
    } >= {
        "STATUS-PRE-NE-001",
        "STATUS-XSD-001",
    }


def test_local_blocking_error_reproves_local_status() -> None:
    context = valid_context()
    context["row_validation"] = SimpleNamespace(
        is_locally_valid=False,
        is_fully_verified=False,
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.REPROVED
    assert decision.status == FinalExecutionStatus.NOT_APT


def test_proven_error_has_precedence_over_external_pending() -> None:
    context = valid_context()
    context["row_validation"] = SimpleNamespace(
        is_locally_valid=False,
        is_fully_verified=False,
    )
    external_rule = regulatory_rule(
        "DRO001401",
        "REGRA NÃO EXECUTADA",
        "EXTERNA",
    )
    context["pre_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(external_rule,),
        rule_results=(external_rule,),
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.REPROVED
    assert decision.status_externo == ExternalValidationStatus.PENDING
    assert decision.status_dependencias == DependentValidationStatus.PENDING
    assert decision.general_status == GeneralValidationStatus.REPROVED
    assert decision.status == FinalExecutionStatus.NOT_APT


def test_unresolved_deferred_rule_leaves_dependencies_pending() -> None:
    context = valid_context()
    pending = SimpleNamespace(rule_code="DRO001312")
    context["reconciliation"] = SimpleNamespace(
        is_fully_reconciled=False,
        unresolved_records=(pending,),
        failed_records=(),
        blocks_apt=True,
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.APPROVED
    assert decision.status_dependencias == DependentValidationStatus.PENDING
    assert decision.general_status == GeneralValidationStatus.PENDING
    assert decision.status == FinalExecutionStatus.NOT_APT
    assert any(
        reason.code == "STATUS-RECON-NE-001"
        for reason in decision.reasons
    )


def test_external_rule_not_executed_leaves_local_approved() -> None:
    context = valid_context()
    external_rule = regulatory_rule(
        "DRO001401",
        "REGRA NÃO EXECUTADA",
        "EXTERNA",
    )
    context["pre_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(external_rule,),
        rule_results=(external_rule,),
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.APPROVED
    assert decision.status_externo == (
        ExternalValidationStatus.PENDING
    )
    assert decision.status_dependencias == DependentValidationStatus.PENDING
    assert decision.general_status == GeneralValidationStatus.PENDING
    assert decision.status == FinalExecutionStatus.NOT_APT
    assert "Validações externas ou históricas: PENDENTE" in decision.message


def test_external_reproof_reproves_general_result_not_local_data() -> None:
    context = valid_context()
    external_rule = regulatory_rule(
        "DRO001401",
        "REPROVADA",
        "EXTERNA",
    )
    context["pre_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(),
        rule_results=(external_rule,),
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.APPROVED
    assert decision.status_externo == ExternalValidationStatus.REPROVED
    assert decision.status_dependencias == DependentValidationStatus.REPROVED
    assert decision.general_status == GeneralValidationStatus.REPROVED
    assert decision.status == FinalExecutionStatus.NOT_APT


def test_historical_rule_not_executed_is_separate() -> None:
    context = valid_context()
    historical_rule = regulatory_rule(
        "DRO000030",
        "REGRA NÃO EXECUTADA",
        "HISTÓRICO DA DATA-BASE ANTERIOR",
    )
    context["post_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(historical_rule,),
        warning_failed_rules=(),
        rule_results=(historical_rule,),
    )

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_local == LocalValidationStatus.APPROVED
    assert decision.status_historico == (
        HistoricalValidationStatus.PENDING
    )
    assert decision.status_dependencias == DependentValidationStatus.PENDING
    assert decision.general_status == GeneralValidationStatus.PENDING
    assert decision.status == FinalExecutionStatus.NOT_APT


def test_approved_external_and_historical_rules_are_apt() -> None:
    context = valid_context()
    external_rule = regulatory_rule(
        "DRO001401",
        "APROVADA",
        "EXTERNA",
    )
    historical_rule = regulatory_rule(
        "DRO000030",
        "APROVADA",
        "HISTÓRICO DA DATA-BASE ANTERIOR",
    )
    context["pre_processing"].rule_results = (external_rule,)
    context["post_processing"].rule_results = (historical_rule,)

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_externo == ExternalValidationStatus.APPROVED
    assert decision.status_historico == (
        HistoricalValidationStatus.APPROVED
    )
    assert decision.general_status == GeneralValidationStatus.APPROVED
    assert decision.status == FinalExecutionStatus.APT


def test_not_applicable_dependent_rules_allow_apt() -> None:
    context = valid_context()
    external_rule = regulatory_rule(
        "DRO001401",
        "NÃO APLICÁVEL",
        "EXTERNA",
    )
    historical_rule = regulatory_rule(
        "DRO000030",
        "NÃO APLICÁVEL",
        "HISTÓRICO DA DATA-BASE ANTERIOR",
    )
    context["pre_processing"].rule_results = (external_rule,)
    context["post_processing"].rule_results = (historical_rule,)

    decision = FinalStatusService().evaluate_complete(**context)

    assert decision.status_externo == (
        ExternalValidationStatus.APPROVED
    )
    assert decision.status_historico == (
        HistoricalValidationStatus.APPROVED
    )
    assert decision.status == FinalExecutionStatus.APT


def test_xsd_technical_failure_has_precedence() -> None:
    context = valid_context()
    technical_issue = SimpleNamespace(
        code="XSD-SCHEMA-001",
        message="XSD ausente.",
        source="Validação XSD",
        line=None,
        column=None,
        xpath=None,
    )
    context["xsd_result"] = SimpleNamespace(
        has_technical_failure=True,
        technical_issues=(technical_issue,),
        is_invalid=False,
        xsd_path="ausente.xsd",
    )

    decision = FinalStatusService().evaluate_complete(
        **context
    )

    assert decision.status == (
        FinalExecutionStatus.TECHNICAL_FAILURE
    )
    assert decision.status_local == LocalValidationStatus.REPROVED
    assert decision.general_status == GeneralValidationStatus.TECHNICAL_FAILURE
    assert decision.status_xsd == (
        XsdValidationSummaryStatus.NOT_EXECUTED
    )
    assert decision.has_technical_failure
    assert decision.reasons[0].code == "XSD-SCHEMA-001"


def test_interrupted_data_validation_is_not_apt() -> None:
    issue = ConversionIssue(
        code="CAB-NORM-001",
        severity="ERRO IMPEDITIVO",
        stage=ConversionStage.NORMALIZE_HEADER,
        message="Cabeçalho inválido.",
        source="Normalização do cabeçalho",
        blocks_apt=True,
    )

    decision = FinalStatusService().evaluate_interrupted(
        stage=ConversionStage.NORMALIZE_HEADER,
        issues=(issue,),
        technical=False,
    )

    assert decision.status == FinalExecutionStatus.NOT_APT


def test_interrupted_read_is_technical_failure() -> None:
    issue = ConversionIssue(
        code="XLSX-READ-001",
        severity="FALHA TÉCNICA",
        stage=ConversionStage.READ_EXCEL,
        message="Arquivo inexistente.",
        source="Leitura do Excel",
        blocks_apt=True,
    )

    decision = FinalStatusService().evaluate_interrupted(
        stage=ConversionStage.READ_EXCEL,
        issues=(issue,),
        technical=True,
    )

    assert decision.status == (
        FinalExecutionStatus.TECHNICAL_FAILURE
    )
    assert decision.status_local == LocalValidationStatus.REPROVED
    assert decision.general_status == GeneralValidationStatus.TECHNICAL_FAILURE
    assert decision.status_xsd == (
        XsdValidationSummaryStatus.NOT_EXECUTED
    )
