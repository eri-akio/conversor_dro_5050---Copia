"""Verificação das dependências técnicas do projeto.

Este módulo valida apenas as bibliotecas realmente utilizadas pelo
Conversor XLSX → XML DRO 5050.
"""

from __future__ import annotations

import importlib
import platform
from dataclasses import dataclass
from importlib import metadata


RECOMMENDED_PYTHON = "3.13.14"


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """Resultado da verificação de uma dependência."""

    package_name: str
    import_name: str
    expected_version: str
    installed_version: str | None
    installed: bool
    compatible: bool
    message: str


REQUIRED_DEPENDENCIES: tuple[tuple[str, str, str], ...] = (
    ("openpyxl", "openpyxl", "3.1.5"),
    ("lxml", "lxml", "6.1.1"),
    ("defusedxml", "defusedxml", "0.7.1"),
)


def current_python_version() -> str:
    """Retorna a versão atual do Python."""

    return platform.python_version()


def is_python_version_compatible() -> bool:
    """Confirma que a aplicação está sendo executada no Python 3.13."""

    version = platform.python_version_tuple()
    return version[0] == "3" and version[1] == "13"


def is_tkinter_available() -> bool:
    """Verifica se o Tkinter pode ser importado."""

    try:
        importlib.import_module("tkinter")
    except (ImportError, ModuleNotFoundError):
        return False

    return True


def _installed_version(
    package_name: str,
) -> str | None:
    """Obtém a versão instalada do pacote informado."""

    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _version_is_compatible(
    installed_version: str,
    expected_version: str,
) -> bool:
    """Compara a versão instalada com a versão esperada.

    O projeto utiliza versões fixadas no requirements.txt. Por isso,
    a verificação exige igualdade exata.
    """

    return installed_version == expected_version


def check_dependencies() -> tuple[DependencyStatus, ...]:
    """Verifica todas as dependências externas exigidas."""

    statuses: list[DependencyStatus] = []

    for (
        package_name,
        import_name,
        expected_version,
    ) in REQUIRED_DEPENDENCIES:
        installed_version = _installed_version(
            package_name
        )

        import_ok = True

        try:
            importlib.import_module(import_name)
        except (ImportError, ModuleNotFoundError):
            import_ok = False

        installed = (
            installed_version is not None
            and import_ok
        )

        compatible = (
            installed
            and _version_is_compatible(
                installed_version,
                expected_version,
            )
        )

        if not installed:
            message = (
                f"{package_name}: NÃO INSTALADA "
                f"(esperada {expected_version})"
            )
        elif compatible:
            message = (
                f"{package_name}: "
                f"{installed_version} [OK]"
            )
        else:
            message = (
                f"{package_name}: "
                f"{installed_version} "
                f"[VERSÃO ESPERADA: {expected_version}]"
            )

        statuses.append(
            DependencyStatus(
                package_name=package_name,
                import_name=import_name,
                expected_version=expected_version,
                installed_version=installed_version,
                installed=installed,
                compatible=compatible,
                message=message,
            )
        )

    return tuple(statuses)


def dependencies_are_compatible(
    statuses: tuple[DependencyStatus, ...]
    | list[DependencyStatus],
) -> bool:
    """Retorna True quando todas as dependências estão compatíveis."""

    return all(
        status.compatible
        for status in statuses
    )
