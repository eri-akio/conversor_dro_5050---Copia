"""Testes da interface desktop simplificada."""

from __future__ import annotations

from pathlib import Path


APP_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "gui"
    / "app.py"
)


def test_header_preview_section_was_removed() -> None:
    source = APP_PATH.read_text(encoding="utf-8")

    assert "Cabeçalho e versão selecionada" not in source
    assert "Ler cabeçalho" not in source
    assert "_build_header_preview" not in source
    assert "_show_preview" not in source


def test_progress_bar_was_removed() -> None:
    source = APP_PATH.read_text(encoding="utf-8")

    assert "ttk.Progressbar" not in source
    assert "self.progress" not in source


def test_layout_has_only_files_and_results_sections() -> None:
    source = APP_PATH.read_text(encoding="utf-8")

    assert "1. Arquivos da execução" in source
    assert "2. Resultado da execução" in source
    assert "3. Resultado da execução" not in source
    assert "Converter, validar e gerar XML/XLSX" in source


def test_only_xml_and_xlsx_artifact_buttons_remain() -> None:
    source = APP_PATH.read_text(encoding="utf-8")

    assert 'text="Abrir XML"' in source
    assert 'text="Abrir relatório XLSX"' in source
    assert "Abrir relatório TXT" not in source
    assert "Abrir LOG" not in source
