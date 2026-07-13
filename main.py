"""Ponto de entrada do Conversor XLSX → XML DRO 5050.

Sem argumentos, abre a interface desktop Tkinter/ttk. Quando um caminho
Excel é informado, mantém o modo terminal para automações e testes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from src.config import (
    OUTPUT_DIR,
    POST_PROCESSING_CRITICS_PATH,
    PRE_PROCESSING_CRITICS_PATH,
    XSD_2020_PATH,
    XSD_2025_PATH,
    ensure_runtime_directories,
    find_missing_project_paths,
)
from src.domain.conversion import ConversionResult
from src.gui.system_utils import default_output_root
from src.presenters import (
    print_conversion_result,
    print_execution_failure,
)
from src.services import convert_excel
from src.utils.dependency_check import (
    check_dependencies,
    dependencies_are_compatible,
    is_python_version_compatible,
    is_tkinter_available,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Cria os argumentos do modo gráfico e do modo terminal."""

    parser = argparse.ArgumentParser(
        description=(
            "Interface desktop e modo terminal do "
            "Conversor DRO 5050."
        )
    )
    parser.add_argument(
        "excel",
        nargs="?",
        help=(
            "Caminho do arquivo .xlsx. Quando informado "
            "sem --gui, executa no terminal."
        ),
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help=(
            "Abre a interface gráfica, opcionalmente com "
            "o Excel já selecionado."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=str(default_output_root()),
        help=(
            "Pasta principal sugerida na interface gráfica."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Pasta dos arquivos XML no modo terminal.",
    )
    return parser


def should_launch_gui(
    arguments: argparse.Namespace,
) -> bool:
    """A interface é o modo padrão quando não há Excel posicional."""

    return bool(
        arguments.gui
        or arguments.excel is None
    )


def validate_environment() -> bool:
    """Confirma silenciosamente estrutura e dependências técnicas."""

    error = False
    ensure_runtime_directories()
    missing = find_missing_project_paths()

    if missing:
        error = True

    for path in (
        XSD_2020_PATH,
        XSD_2025_PATH,
        PRE_PROCESSING_CRITICS_PATH,
        POST_PROCESSING_CRITICS_PATH,
    ):
        if not path.is_file():
            error = True

    if not is_python_version_compatible():
        error = True

    if not is_tkinter_available():
        error = True
    statuses = check_dependencies()

    if not dependencies_are_compatible(statuses):
        error = True

    return not error


def process_excel(
    excel_path: str | Path,
    *,
    output_dir: str | Path = OUTPUT_DIR,
) -> ConversionResult:
    """Executa o serviço completo no modo terminal."""

    return convert_excel(
        excel_path,
        output_dir=output_dir,
    )


def launch_desktop(
    *,
    excel_path: str | Path | None = None,
    output_root: str | Path | None = None,
) -> int:
    """Abre a interface sem importar a janela durante os testes do CLI."""

    try:
        from src.gui.app import launch_gui

        return launch_gui(
            initial_excel=excel_path,
            initial_output_root=output_root,
        )
    except Exception as error:
        print_execution_failure(
            "Inicialização da interface",
            (
                "A interface gráfica não pôde ser iniciada: "
                f"{error}"
            ),
        )
        return 2


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = build_argument_parser().parse_args(
        argv
    )

    if not validate_environment():
        print_execution_failure(
            "Validação do ambiente",
            (
                "A estrutura, a versão do Python ou uma "
                "dependência obrigatória não está disponível."
            ),
        )
        return 1

    if should_launch_gui(arguments):
        return launch_desktop(
            excel_path=arguments.excel,
            output_root=arguments.output_root,
        )

    result = process_excel(
        arguments.excel,
        output_dir=arguments.output_dir,
    )
    print_conversion_result(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
