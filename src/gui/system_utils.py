"""Utilidades de caminhos e integração com o sistema operacional."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def downloads_directory() -> Path:
    """Retorna a pasta Downloads do usuário."""

    return Path.home() / "Downloads"


def default_output_root() -> Path:
    """Pasta inicial sugerida pela interface."""

    return (
        downloads_directory()
        / "Conversor_DRO_5050"
    )


def default_dialog_directory() -> Path:
    """Diretório inicial dos seletores de arquivo e pasta."""

    downloads = downloads_directory()
    return downloads if downloads.is_dir() else Path.home()


def open_path(path: str | Path) -> None:
    """Abre arquivo ou pasta no aplicativo padrão do sistema."""

    target = Path(path).expanduser().resolve()

    if not target.exists():
        raise FileNotFoundError(
            f"Caminho não encontrado: {target}"
        )

    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
        return

    command = (
        ["open", str(target)]
        if sys.platform == "darwin"
        else ["xdg-open", str(target)]
    )
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
