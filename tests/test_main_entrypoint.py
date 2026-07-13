"""Testes da escolha entre interface e terminal."""

from __future__ import annotations

import main as main_module

from main import (
    build_argument_parser,
    should_launch_gui,
    validate_environment,
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


def test_environment_validation_is_silent_when_successful(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        main_module,
        "ensure_runtime_directories",
        lambda: None,
    )
    monkeypatch.setattr(
        main_module,
        "find_missing_project_paths",
        lambda: (),
    )
    monkeypatch.setattr(
        main_module,
        "is_python_version_compatible",
        lambda: True,
    )
    monkeypatch.setattr(
        main_module,
        "is_tkinter_available",
        lambda: True,
    )
    monkeypatch.setattr(
        main_module,
        "check_dependencies",
        lambda: (),
    )
    monkeypatch.setattr(
        main_module,
        "dependencies_are_compatible",
        lambda statuses: True,
    )

    assert validate_environment()
    assert capsys.readouterr().out == ""
