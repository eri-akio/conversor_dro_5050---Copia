"""Testes da escolha entre interface e terminal."""

from __future__ import annotations

from main import (
    build_argument_parser,
    should_launch_gui,
)


def test_no_arguments_selects_gui() -> None:
    arguments = (
        build_argument_parser()
        .parse_args([])
    )

    assert should_launch_gui(arguments)


def test_gui_flag_forces_gui_with_excel() -> None:
    arguments = (
        build_argument_parser()
        .parse_args(
            [
                "--gui",
                "entrada.xlsx",
            ]
        )
    )

    assert should_launch_gui(arguments)


def test_excel_without_gui_selects_terminal() -> None:
    arguments = (
        build_argument_parser()
        .parse_args(
            ["entrada.xlsx"]
        )
    )

    assert not should_launch_gui(arguments)


def test_cli_exposes_only_xml_and_xlsx_output_directories() -> None:
    help_text = build_argument_parser().format_help()

    assert "--output-dir" in help_text
    assert "--reports-dir" not in help_text
    assert "--logs-dir" not in help_text
