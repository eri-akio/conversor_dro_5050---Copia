"""Ponto de entrada do Conversor XLSX → XML DRO 5050.

Sem argumentos, abre a interface desktop Tkinter/ttk. Quando um caminho
Excel é informado, mantém o modo terminal para automações e testes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from src.config import (
    DOCUMENT_CODE,
    OUTPUT_DIR,
    POST_PROCESSING_CRITICS_PATH,
    PRE_PROCESSING_CRITICS_PATH,
    PROJECT_NAME,
    PROJECT_ROOT,
    REQUIRED_SHEETS,
    XSD_2020_PATH,
    XSD_2025_PATH,
    XML_ENCODING,
    XML_VERSION,
    ensure_runtime_directories,
    find_missing_project_paths,
    relative_to_project,
)
from src.domain.conversion import ConversionResult
from src.gui.system_utils import default_output_root
from src.services import convert_excel
from src.utils.dependency_check import (
    RECOMMENDED_PYTHON,
    check_dependencies,
    current_python_version,
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
    """Confirma a estrutura e as dependências técnicas."""

    print("=" * 72)
    print(PROJECT_NAME.upper())
    print("Etapa 6.1 - Interface desktop Tkinter/ttk")
    print("=" * 72)

    error = False
    ensure_runtime_directories()

    print("\n[1/5] Configuração central")
    print(f"  Código do documento: {DOCUMENT_CODE}")
    print(
        f"  XML: versão {XML_VERSION}, "
        f"encoding {XML_ENCODING}"
    )
    print(
        "  Abas obrigatórias: "
        f"{', '.join(REQUIRED_SHEETS)}"
    )
    print(f"  Raiz do projeto: {PROJECT_ROOT}")
    print("  Configuração carregada. [OK]")

    print("\n[2/5] Estrutura e fontes")
    missing = find_missing_project_paths()

    if missing:
        error = True
        for path in missing:
            print(
                "  [ERRO] Caminho ausente: "
                f"{relative_to_project(path)}"
            )
    else:
        print(
            "  Estrutura e fontes regulatórias "
            "encontradas. [OK]"
        )

    print("\n[3/5] Arquivos regulatórios")
    for path in (
        XSD_2020_PATH,
        XSD_2025_PATH,
        PRE_PROCESSING_CRITICS_PATH,
        POST_PROCESSING_CRITICS_PATH,
    ):
        if path.is_file():
            print(
                f"  {relative_to_project(path)} [OK]"
            )
        else:
            error = True
            print(
                "  [ERRO] Arquivo ausente: "
                f"{relative_to_project(path)}"
            )

    print("\n[4/5] Python e interface")
    print(
        f"  Python encontrado: "
        f"{current_python_version()}"
    )
    print(
        f"  Versão de referência: "
        f"{RECOMMENDED_PYTHON}"
    )

    if is_python_version_compatible():
        print("  Série Python 3.13 confirmada. [OK]")
    else:
        error = True
        print(
            "  [ERRO] O projeto exige Python 3.13.x."
        )

    if is_tkinter_available():
        print("  Tkinter disponível. [OK]")
    else:
        error = True
        print(
            "  [ERRO] Tkinter não está disponível."
        )

    print("\n[5/5] Dependências")
    statuses = check_dependencies()

    for status in statuses:
        prefix = (
            "  "
            if status.compatible
            else "  [ERRO] "
        )
        print(f"{prefix}{status.message}")

    if not dependencies_are_compatible(statuses):
        error = True

    return not error


def print_conversion_result(
    result: ConversionResult,
) -> None:
    """Apresenta o resultado do modo terminal."""

    print("\n" + "=" * 72)
    print("RESULTADO DA CONVERSÃO")
    print("=" * 72)
    print(f"\nExecução: {result.execution_id}")
    print(
        f"Resultado final: {result.status.value}"
    )
    print(f"Mensagem: {result.final_message}")
    print(
        f"Duração: {result.duration_seconds:.3f} "
        "segundo(s)"
    )

    print("\nEtapas:")
    for record in result.stage_records:
        print(
            f"  [{record.status.value}] "
            f"{record.stage.value} "
            f"({record.duration_seconds:.3f}s)"
        )

    if result.decision.reasons:
        print("\nMotivos e avisos:")
        for reason in result.decision.reasons:
            print(
                f"  [{reason.severity}] "
                f"{reason.code} - {reason.message}"
            )

    print("\nArquivos:")
    print(
        "  XML: "
        f"{result.artifacts.xml_path or 'não gerado'}"
    )
    print(
        "  XLSX: "
        f"{result.artifacts.xlsx_path or 'não gerado'}"
    )


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
        print(
            "\n[FALHA TÉCNICA] A interface gráfica "
            "não pôde ser iniciada."
        )
        print(
            f"Tipo: {type(error).__name__}"
        )
        print(f"Detalhes: {error}")
        return 2


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = build_argument_parser().parse_args(
        argv
    )

    if not validate_environment():
        print("\nResultado: FALHA TÉCNICA")
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
