"""Testes dos caminhos padrão da interface."""

from __future__ import annotations

from pathlib import Path

from src.gui.system_utils import (
    default_output_root,
    downloads_directory,
)


def test_default_output_uses_downloads() -> None:
    downloads = downloads_directory()
    output = default_output_root()

    assert downloads == (
        Path.home() / "Downloads"
    )
    assert output.parent == downloads
    assert output.name == "Conversor_DRO_5050"
