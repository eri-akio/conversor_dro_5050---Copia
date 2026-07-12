"""Testes dos arquivos estruturais acumulados do projeto."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    'assets',
    'assets/regulatory',
    'config',
    'docs',
    'output',
    'schemas',
    'src/domain',
    'src/gui',
    'src/readers',
    'src/normalizers',
    'src/mappers',
    'src/builders',
    'src/validators',
    'src/reporters',
    'src/services',
    'src/utils',
    'tests',
)

REQUIRED_FILES = (
    'README.md',
    'main.py',
    'src/config.py',
    'src/domain/base_row.py',
    'src/domain/base_row_validation.py',
    'src/domain/grouped_event.py',
    'src/mappers/event_grouper.py',
    'src/normalizers/base_row_normalizer.py',
    'src/readers/base_reader.py',
    'src/validators/base_row_validator.py',
    'src/validators/base_structure_validator.py',
    'src/validators/event_consistency_validator.py',
    'docs/matriz_versoes.md',
    'docs/matriz_campos.md',
    'docs/matriz_criticas.md',
    'docs/conflitos_documentais.md',
    'docs/validacao_linhas_base.md',
    'docs/agrupamento_eventos.md',
    'tests/test_base_row_validator.py',
    'tests/test_event_grouping.py',
    'tests/test_event_financial_validator.py',
    'docs/validacao_financeira_eventos.md',
    'src/validators/event_financial_validator.py',
    'src/domain/event_financial.py',
    'tests/test_reference_tables.py',
    'docs/validacao_tabelas_referencia.md',
    'src/validators/reference_tables_validator.py',
    'src/readers/reference_tables_reader.py',
    'src/normalizers/reference_table_normalizer.py',
    'src/domain/reference_tables.py',
    'tests/test_document_builder.py',
    'docs/construcao_objetos_documento.md',
    'src/builders/document_builder.py',
    'src/domain/document_model.py',
    'tests/test_xml_generation.py',
    'docs/geracao_xml.md',
    'src/services/xml_generation_service.py',
    'src/builders/xml_builder.py',
    'src/domain/xml_generation.py',
    'tests/test_xsd_validation.py',
    'docs/validacao_xsd.md',
    'src/services/xsd_validation_service.py',
    'src/validators/xsd_validator.py',
    'src/domain/xsd_validation.py',
    'tests/test_pre_processing.py',
    'docs/criticas_pre_processamento.md',
    'src/validators/pre_processing/validator.py',
    'src/validators/pre_processing/catalog.py',
    'src/validators/pre_processing/__init__.py',
    'src/domain/pre_processing.py',
    'tests/test_post_processing.py',
    'docs/criticas_pos_processamento.md',
    'src/validators/post_processing/validator.py',
    'src/validators/post_processing/catalog.py',
    'src/validators/post_processing/__init__.py',
    'src/domain/post_processing.py',
    'tests/test_reporting.py',
    'docs/relatorios_execucao.md',
    'src/services/reporting_service.py',
    'src/reporters/xlsx_reporter.py',
    'src/reporters/report_collector.py',
    'src/domain/reporting.py',
    'tests/test_conversion_service.py',
    'tests/test_final_status_service.py',
    'docs/servico_conversao.md',
    'src/services/conversion_service.py',
    'src/services/final_status_service.py',
    'src/domain/conversion.py',
    'tests/test_main_entrypoint.py',
    'tests/test_gui_system_utils.py',
    'tests/test_gui_controller.py',
    'tests/test_gui_header_preview.py',
    'docs/interface_desktop.md',
    'src/gui/system_utils.py',
    'src/gui/models.py',
    'src/gui/header_preview_service.py',
    'src/gui/controller.py',
    'src/gui/app.py',
    'src/gui/__main__.py',
    'src/gui/__init__.py',
    'assets/regulatory/criticas_pos_processamento_5050.xlsx',
    'assets/regulatory/criticas_pre_processamento_5050.xlsx',
)


def test_required_directories_exist() -> None:
    for relative_path in REQUIRED_DIRECTORIES:
        assert (PROJECT_ROOT / relative_path).is_dir(), relative_path


def test_required_files_exist() -> None:
    for relative_path in REQUIRED_FILES:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path
