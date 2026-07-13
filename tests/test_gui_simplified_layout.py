"""Testes da interface desktop compacta."""

from __future__ import annotations

from pathlib import Path


APP_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "gui"
    / "app.py"
)


def _source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_layout_contains_only_requested_controls() -> None:
    source = _source()

    for text in (
        "Conversor XLSX → XML DRO 5050",
        "Planilha Excel:",
        "Pasta de saída:",
        "Status:",
        "Converter, validar e gerar XML/XLSX",
        "Abrir XML",
        "Abrir relatório XLSX",
        "Abrir pasta",
    ):
        assert text in source


def test_subtitle_numbered_sections_and_message_area_were_removed() -> None:
    source = _source()

    assert "Selecione o Excel, escolha a pasta de saída" not in source
    assert "1. Arquivos da execução" not in source
    assert "2. Resultado da execução" not in source
    assert 'text="Mensagem"' not in source
    assert "tk.Text" not in source
    assert "ttk.Scrollbar" not in source
    assert "messages_text" not in source
    assert "_append_message" not in source
    assert "_build_results" not in source


def test_header_preview_and_progress_widgets_remain_removed() -> None:
    source = _source()

    assert "Cabeçalho e versão selecionada" not in source
    assert "Ler cabeçalho" not in source
    assert "_build_header_preview" not in source
    assert "_show_preview" not in source
    assert "ttk.Progressbar" not in source
    assert "self.progress" not in source


def test_no_txt_or_log_artifact_actions_were_reintroduced() -> None:
    source = _source()

    assert "Abrir relatório TXT" not in source
    assert "Abrir LOG" not in source


def test_status_indicator_has_the_four_required_states() -> None:
    source = _source()

    assert 'STATUS_AWAITING = "Aguardando"' in source
    assert 'STATUS_PROCESSING = "Processando..."' in source
    assert 'STATUS_COMPLETED = "Concluído"' in source
    assert 'STATUS_TECHNICAL_FAILURE = "Falha técnica"' in source
    assert "textvariable=self.status_var" in source
    assert "StatusAwaiting.TLabel" in source
    assert "StatusProcessing.TLabel" in source
    assert "StatusCompleted.TLabel" in source
    assert "StatusFailure.TLabel" in source


def test_conversion_events_update_status_and_busy_state() -> None:
    source = _source()
    started = source.split(
        "if event.kind == GuiEventKind.STARTED:",
        maxsplit=1,
    )[1].split(
        "if event.kind == GuiEventKind.REJECTED:",
        maxsplit=1,
    )[0]

    assert "_set_busy(True)" in started
    assert "STATUS_PROCESSING" in started
    assert "self._set_busy(False)" in source
    assert "STATUS_COMPLETED" in source
    assert "STATUS_TECHNICAL_FAILURE" in source


def test_busy_state_disables_selection_and_conversion() -> None:
    source = _source()

    for widget in (
        "self.browse_excel_button",
        "self.browse_output_button",
        "self.convert_button",
        "self.excel_entry",
        "self.output_entry",
    ):
        assert widget in source
    assert 'state = "disabled" if busy else "normal"' in source


def test_artifact_buttons_remain_individually_guarded_by_file() -> None:
    source = _source()

    assert "self.artifact_buttons.items()" in source
    assert "path = self._artifact_paths.get(key)" in source
    assert "path is not None" in source
    assert "path.is_file()" in source
    assert "self._artifact_paths.clear()" in source
    assert "self._set_artifact_buttons_state(False)" in source


def test_gui_remains_queue_driven_and_thread_safe() -> None:
    source = _source()

    assert "self.master.after(" in source
    assert "self.controller.get_event_nowait()" in source
    assert "self._handle_event(event)" in source
