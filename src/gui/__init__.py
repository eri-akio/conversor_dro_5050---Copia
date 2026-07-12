"""Componentes da interface gráfica do Conversor DRO 5050.

A janela Tkinter é importada somente quando ``launch_gui`` é chamado.
Assim, o modo terminal continua utilizável mesmo em ambientes sem tela.
"""

from __future__ import annotations

from pathlib import Path

from src.gui.controller import GuiController
from src.gui.header_preview_service import (
    HeaderPreviewService,
    preview_header,
)
from src.gui.models import (
    GuiEvent,
    GuiEventKind,
    GuiOutputDirectories,
    GuiTaskError,
    GuiTaskKind,
    HeaderPreviewIssue,
    HeaderPreviewResult,
)
from src.gui.system_utils import (
    default_dialog_directory,
    default_output_root,
    downloads_directory,
    open_path,
)


def launch_gui(
    *,
    initial_excel: str | Path | None = None,
    initial_output_root: str | Path | None = None,
) -> int:
    """Importa e abre a janela somente quando necessário."""

    from src.gui.app import launch_gui as _launch_gui

    return _launch_gui(
        initial_excel=initial_excel,
        initial_output_root=initial_output_root,
    )


__all__ = [
    "GuiController",
    "GuiEvent",
    "GuiEventKind",
    "GuiOutputDirectories",
    "GuiTaskError",
    "GuiTaskKind",
    "HeaderPreviewIssue",
    "HeaderPreviewResult",
    "HeaderPreviewService",
    "default_dialog_directory",
    "default_output_root",
    "downloads_directory",
    "launch_gui",
    "open_path",
    "preview_header",
]
