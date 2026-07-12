"""Modelos independentes da janela Tkinter.

Esses objetos permitem testar a lógica da interface sem abrir uma
janela gráfica, o que é importante para os testes automatizados.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping


class GuiTaskKind(StrEnum):
    """Tipos de trabalho executados em segundo plano."""

    PREVIEW = "PRÉ-VISUALIZAÇÃO"
    CONVERSION = "CONVERSÃO"


class GuiEventKind(StrEnum):
    """Eventos enviados pelo controlador para a janela."""

    STARTED = "INICIADO"
    COMPLETED = "CONCLUÍDO"
    FAILED = "FALHOU"
    REJECTED = "REJEITADO"


@dataclass(frozen=True, slots=True)
class GuiOutputDirectories:
    """Pastas derivadas da pasta principal escolhida pelo usuário."""

    root: Path

    @classmethod
    def from_root(
        cls,
        root: str | Path,
    ) -> "GuiOutputDirectories":
        normalized = Path(
            root
        ).expanduser().resolve()

        return cls(
            root=normalized,
        )

    def ensure(self) -> None:
        """Cria somente as pastas de saída da execução."""

        self.root.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True, slots=True)
class HeaderPreviewIssue:
    """Ocorrência encontrada ao ler o cabeçalho."""

    code: str
    severity: str
    message: str
    field_name: str | None = None
    value: Any = None


@dataclass(frozen=True, slots=True)
class HeaderPreviewResult:
    """Dados exibidos na área de cabeçalho da interface."""

    input_path: Path
    is_valid: bool
    header_values: Mapping[str, str]
    profile_code: str | None
    instruction_version: str | None
    xsd_version: str | None
    xsd_path: Path | None
    version_status: str
    blocks_apt: bool
    issues: tuple[HeaderPreviewIssue, ...]

    @property
    def can_convert(self) -> bool:
        """Permite diagnóstico quando há perfil e cabeçalho válidos."""

        return (
            self.is_valid
            and self.profile_code is not None
            and self.xsd_path is not None
        )

    def get(
        self,
        field_name: str,
        default: str = "",
    ) -> str:
        return self.header_values.get(
            field_name,
            default,
        )


@dataclass(frozen=True, slots=True)
class GuiTaskError:
    """Falha capturada dentro de uma thread da interface."""

    code: str
    message: str
    exception_type: str
    details: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class GuiEvent:
    """Mensagem imutável consumida pela janela principal."""

    task: GuiTaskKind
    kind: GuiEventKind
    message: str
    payload: Any = None
