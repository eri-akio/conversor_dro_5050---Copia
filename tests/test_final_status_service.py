"""Testes da consolidação única do status final."""

from __future__ import annotations

from types import SimpleNamespace

from src.domain.conversion import (
    ConversionIssue,
    ConversionStage,
)
from src.domain.reporting import (
    FinalExecutionStatus,
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
        ),
        "post_processing": SimpleNamespace(
            is_locally_valid=True,
            not_executed_rules=(),
            warning_failed_rules=(),
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


def test_complete_valid_context_is_apt() -> None:
    decision = FinalStatusService().evaluate_complete(
        **valid_context()
    )

    assert decision.status == FinalExecutionStatus.APT
    assert decision.is_apt
    assert not decision.blocking_reasons


def test_pending_and_invalid_rules_are_not_apt() -> None:
    context = valid_context()
    context["pre_processing"] = SimpleNamespace(
        is_locally_valid=True,
        not_executed_rules=(
            SimpleNamespace(code="DRO001001"),
        ),
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
    assert {
        reason.code
        for reason in decision.blocking_reasons
    } >= {
        "STATUS-PRE-NE-001",
        "STATUS-XSD-001",
    }


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
