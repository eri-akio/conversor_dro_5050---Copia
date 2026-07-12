"""Testes da geração do XML a partir dos objetos finais."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from lxml import etree

from src.builders import (
    XmlDocumentBuilder,
    build_final_document,
)
from src.domain.document_model import (
    DocumentBuildResult,
)
from src.domain.xml_generation import (
    XmlGenerationMode,
)
from src.services import generate_xml
from tests.test_document_builder import (
    consolidated_event,
    prepare_sample,
)


def diagnostic_build_result():
    context = prepare_sample()
    return build_final_document(**context)


def complete_build_result():
    context = prepare_sample()
    result = build_final_document(
        **context,
        consolidated_events=(
            consolidated_event(),
        ),
    )
    assert result.document is not None

    return DocumentBuildResult(
        document=result.document,
        issues=(),
    )


def parse(path: Path):
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
    )
    return etree.parse(str(path), parser)


def test_exact_root_blocks_and_order() -> None:
    result = complete_build_result()
    assert result.document is not None

    tree = XmlDocumentBuilder().build_tree(
        result.document
    )
    root = tree.getroot()

    assert root.tag == "documento"
    assert list(root.attrib) == [
        "codigoDocumento",
        "dataBase",
        "codigoConglomerado",
        "cnpj",
        "tipoRemessa",
        "opcaoPorProvisaoAcumulada",
    ]
    assert [
        child.tag
        for child in root
    ] == [
        "eventosIndividualizados",
        "eventosConsolidados",
        "sistemasOrigem",
        "contasSubtitulosInternos",
    ]


def test_nested_event_order() -> None:
    result = complete_build_result()
    assert result.document is not None

    root = XmlDocumentBuilder().build_tree(
        result.document
    ).getroot()

    event = next(
        element
        for element in root.findall(
            "./eventosIndividualizados/evento"
        )
        if len(element) > 0
    )

    child_tags = [
        child.tag
        for child in event
    ]

    assert child_tags in (
        ["probabilidadesPerdas"],
        ["contabilizacoes"],
        [
            "probabilidadesPerdas",
            "contabilizacoes",
        ],
    )


def test_diagnostic_xml_is_generated_when_xsd_structure_is_incomplete(
    tmp_path: Path,
) -> None:
    result = generate_xml(
        diagnostic_build_result(),
        output_dir=tmp_path,
    )

    assert result.is_generated
    assert result.is_diagnostic
    assert result.mode == (
        XmlGenerationMode.DIAGNOSTIC
    )
    assert result.actual_filename == (
        "DRO_5050_2026-06_NAO_APTO.xml"
    )
    assert result.well_formed
    assert result.output_path is not None

    root = parse(result.output_path).getroot()
    consolidated = root.find(
        "eventosConsolidados"
    )

    assert consolidated is not None
    assert len(consolidated) == 0
    assert (
        result.element_counts
        .individualized_events
        == 15
    )


def test_complete_document_uses_candidate_filename(
    tmp_path: Path,
) -> None:
    result = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )

    assert result.is_generated
    assert result.is_candidate
    assert result.actual_filename == (
        "DRO_5050_2026-06.xml"
    )
    assert not result.blocks_apt


def test_existing_file_is_not_overwritten(
    tmp_path: Path,
) -> None:
    build_result = complete_build_result()

    first = generate_xml(
        build_result,
        output_dir=tmp_path,
    )
    assert first.output_path is not None
    first_content = first.output_path.read_bytes()

    second = generate_xml(
        build_result,
        output_dir=tmp_path,
    )

    assert second.output_path is not None
    assert second.actual_filename == (
        "DRO_5050_2026-06_001.xml"
    )
    assert second.collision_index == 1
    assert first.output_path.read_bytes() == first_content
    assert second.output_path.read_bytes() == first_content
    assert any(
        issue.code == "XML-GEN-INFO-002"
        for issue in second.issues
    )


def test_xml_declaration_and_utf8(
    tmp_path: Path,
) -> None:
    result = generate_xml(
        complete_build_result(),
        output_dir=tmp_path,
    )
    assert result.output_path is not None

    content = result.output_path.read_bytes()

    assert content.startswith(
        b"<?xml version='1.0' encoding='UTF-8'?>"
    )
    assert content.endswith(b"\n")
    assert b"xmlns" not in content


def test_special_characters_are_escaped(
    tmp_path: Path,
) -> None:
    result = complete_build_result()
    assert result.document is not None

    first = result.document.individualized_events[0]
    changed_first = replace(
        first,
        event_description=(
            "Falha & perda <teste>"
        ),
    )
    changed_document = replace(
        result.document,
        individualized_events=(
            changed_first,
            *result.document
            .individualized_events[1:],
        ),
    )

    changed_result = DocumentBuildResult(
        document=changed_document,
        issues=(),
    )

    generated = generate_xml(
        changed_result,
        output_dir=tmp_path,
    )
    assert generated.output_path is not None

    raw = generated.output_path.read_text(
        encoding="utf-8"
    )
    assert "&amp;" in raw
    assert "&lt;teste&gt;" in raw

    root = parse(generated.output_path).getroot()
    event = root.find(
        "./eventosIndividualizados/evento"
    )
    assert event is not None
    assert event.get("descricaoEvento") == (
        "Falha & perda <teste>"
    )


def test_optional_event_containers_are_omitted(
    tmp_path: Path,
) -> None:
    result = complete_build_result()
    assert result.document is not None

    first = replace(
        result.document.individualized_events[0],
        probabilities=(),
        accountings=(),
    )
    changed_document = replace(
        result.document,
        individualized_events=(
            first,
            *result.document
            .individualized_events[1:],
        ),
    )

    generated = generate_xml(
        DocumentBuildResult(
            document=changed_document,
            issues=(),
        ),
        output_dir=tmp_path,
    )
    assert generated.output_path is not None

    event = parse(
        generated.output_path
    ).getroot().find(
        "./eventosIndividualizados/evento"
    )

    assert event is not None
    assert event.find(
        "probabilidadesPerdas"
    ) is None
    assert event.find(
        "contabilizacoes"
    ) is None


def test_unsupported_profile_values_are_not_serialized(
    tmp_path: Path,
) -> None:
    result = complete_build_result()
    assert result.document is not None

    changed_document = replace(
        result.document,
        unsupported_profile_values=(
            replace(
                result.document
                .unsupported_profile_values[0],
            )
            if (
                result.document
                .unsupported_profile_values
            )
            else ()
        ),
    )

    generated = generate_xml(
        DocumentBuildResult(
            document=changed_document,
            issues=(),
        ),
        output_dir=tmp_path,
    )
    assert generated.output_path is not None

    content = generated.output_path.read_text(
        encoding="utf-8"
    )
    assert "idEventoAgregador" not in content
    assert "dataExclusao" not in content
    assert "motivoExclusao" not in content


def test_missing_document_does_not_create_file(
    tmp_path: Path,
) -> None:
    result = generate_xml(
        DocumentBuildResult(
            document=None,
            issues=(),
        ),
        output_dir=tmp_path,
    )

    assert not result.is_generated
    assert result.output_path is None
    assert not result.well_formed
    assert any(
        issue.code == "XML-GEN-001"
        for issue in result.issues
    )
    assert list(tmp_path.iterdir()) == []


def test_output_path_must_be_directory(
    tmp_path: Path,
) -> None:
    from src.services import XmlGenerationError

    output_file = tmp_path / "arquivo.txt"
    output_file.write_text(
        "conteúdo",
        encoding="utf-8",
    )

    try:
        generate_xml(
            complete_build_result(),
            output_dir=output_file,
        )
    except XmlGenerationError as error:
        assert error.code == "XML-WRITE-002"
    else:
        raise AssertionError(
            "Era esperado XmlGenerationError."
        )
