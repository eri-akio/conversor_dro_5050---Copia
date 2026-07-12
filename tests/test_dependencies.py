"""Testes das dependências definidas na etapa 2.2."""

from __future__ import annotations

from src.utils.dependency_check import (
    check_dependencies,
    dependencies_are_compatible,
    is_artifact_tool_available,
    is_python_version_compatible,
    is_tkinter_available,
)


def test_python_belongs_to_series_313() -> None:
    assert is_python_version_compatible()


def test_tkinter_is_available() -> None:
    assert is_tkinter_available()


def test_runtime_dependencies_are_installed() -> None:
    statuses = check_dependencies()
    assert dependencies_are_compatible(statuses), [
        status.message for status in statuses if not status.compatible
    ]


def test_development_dependencies_are_installed() -> None:
    statuses = check_dependencies(include_development=True)
    assert dependencies_are_compatible(statuses), [
        status.message for status in statuses if not status.compatible
    ]



def test_artifact_tool_is_available() -> None:
    assert is_artifact_tool_available()
