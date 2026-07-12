"""Testes da construção dos objetos finais do documento."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import re

from src.builders import build_final_document
from src.domain.document_model import (
    FinalConsolidatedEvent,
)
from src.mappers import group_base_rows
from src.normalizers.header_normalizer import normalize_header
from src.readers import (
    read_and_normalize_base,
    read_excel,
    read_header,
    read_reference_tables,
)
from src.services.version_resolver import resolve_version
from src.validators import (
    validate_base_rows,
    validate_event_financials,
    validate_grouped_events,
    validate_reference_tables,
)


SAMPLE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "DRO_5050_planilha_testes.xlsx"
)


def prepare_sample():
    excel = read_excel(SAMPLE_PATH)
    header_result = normalize_header(
        read_header(excel)
    )
    assert header_result.header is not None
    header = header_result.header

    profile = resolve_version(header).profile
    assert profile is not None

    normalization = read_and_normalize_base(
        excel,
        profile,
    )
    row_validation = validate_base_rows(
        normalization,
        profile,
    )
    grouping = group_base_rows(
        normalization,
        row_validation,
    )
    event_validation = validate_grouped_events(
        grouping,
        profile,
    )
    financial = validate_event_financials(
        grouping,
        profile,
    )
    references = validate_reference_tables(
        read_reference_tables(excel),
        grouping,
    )

    return {
        "header": header,
        "profile": profile,
        "row_validation": row_validation,
        "grouping": grouping,
        "event_validation": event_validation,
        "financial_validation": financial,
        "references": references,
    }


def consolidated_event() -> FinalConsolidatedEvent:
    """Simula a saída de um cálculo futuro, não uma aba Excel."""

    return FinalConsolidatedEvent(
        category_level_1="1",
        total_event_count=10,
        semester_event_count=3,
        total_loss=Decimal("8000.00"),
        semester_loss=Decimal("2100.00"),
        total_provision=Decimal("0.00"),
        semester_provision=Decimal("0.00"),
        source_event_ids=(
            "CONSOLIDADO_CALCULADO",
        ),
    )


def test_sample_builds_diagnostic_document() -> None:
    context = prepare_sample()

    result = build_final_document(**context)

    assert result.is_built
    assert not result.is_xml_ready
    assert result.blocks_apt
    assert result.document is not None

    document = result.document
    assert document.individualized_event_count == 15
    assert document.consolidated_event_count == 0
    assert document.source_system_count == 5
    assert document.internal_account_count == 10

    assert any(
        issue.code == "DOC-CONS-001"
        for issue in result.blocking_xml_issues
    )
    assert any(
        issue.code == "DOC-REGRA-NE-001"
        and (
            ("codigoRegra", "DRO001241")
            in issue.values
        )
        for issue in result.apt_blocking_issues
    )


def test_event_attributes_use_xsd_names() -> None:
    context = prepare_sample()
    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )

    assert result.document is not None
    event = result.document.individualized_events[0]
    attributes = event.as_xml_attributes()

    assert "idEvento" in attributes
    assert "probabilidadePerda" not in attributes
    assert (
        "ligadoRiscoSocioAmbiental"
        in attributes
    )
    assert (
        "ligacaoRiscoSocioambiental"
        not in attributes
    )
    assert attributes["totalPerdaEfetiva"].endswith(
        ".00"
    )


def test_probabilities_and_accountings_are_preserved() -> None:
    context = prepare_sample()
    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )

    assert result.document is not None
    event_with_probability = next(
        event
        for event in result.document.individualized_events
        if event.probabilities
    )
    event_with_accounting = next(
        event
        for event in result.document.individualized_events
        if event.accountings
    )

    probability = event_with_probability.probabilities[0]
    assert probability.as_xml_attributes() == {
        "probabilidade": probability.probability,
        "valorRisco": format(
            probability.value_risk,
            ".2f",
        ),
    }
    accounting_text = (
        event_with_accounting.accountings[0]
        .as_xml_attributes()[
            "valorPerdaEfetiva"
        ]
    )
    assert re.fullmatch(
        r"-?[0-9]+\.[0-9]{2}",
        accounting_text,
    )


def test_calculated_consolidated_event_makes_structure_ready() -> None:
    context = prepare_sample()

    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )

    assert result.is_built
    assert result.is_xml_ready
    assert result.blocks_apt
    assert result.document is not None
    assert (
        result.document
        .consolidated_events[0]
        .as_xml_attributes()[
            "categoriaNivel1Consol"
        ]
        == "1"
    )


def test_duplicate_consolidated_category_blocks_xml() -> None:
    context = prepare_sample()
    item = consolidated_event()

    result = build_final_document(
        **context,
        consolidated_events=(
            item,
            replace(
                item,
                total_event_count=2,
            ),
        ),
    )

    assert not result.is_xml_ready
    assert any(
        issue.code == "DOC-CONS-004"
        for issue in result.blocking_xml_issues
    )


def test_invalid_grouping_prevents_document_creation() -> None:
    context = prepare_sample()
    invalid_grouping = replace(
        context["grouping"],
        ungrouped_row_numbers=(999,),
    )
    context["grouping"] = invalid_grouping

    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )

    assert not result.is_built
    assert any(
        issue.code == "DOC-BUILD-002"
        for issue in result.issues
    )


def test_optional_attributes_are_omitted() -> None:
    context = prepare_sample()
    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )

    assert result.document is not None
    event = result.document.individualized_events[0]
    modified = replace(
        event,
        category_level_2=None,
        discovery_date=None,
        total_provision=None,
        total_risk=None,
        event_description=None,
        associated_risk=None,
        socioenvironmental_risk=None,
        cyber_risk=None,
        discontinued_business=None,
    )

    attributes = modified.as_xml_attributes()

    for optional_name in (
        "categoriaNivel2",
        "dataDescoberta",
        "totalProvisao",
        "valorTotalRisco",
        "descricaoEvento",
        "riscoAssociado",
        "ligadoRiscoSocioAmbiental",
        "ligadoRiscoCibernetico",
        "negocioDescontinuado",
    ):
        assert optional_name not in attributes
