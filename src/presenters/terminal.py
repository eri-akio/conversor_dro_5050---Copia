"""Apresentação legível das etapas estruturadas no terminal."""

from __future__ import annotations

from collections.abc import Iterable
import sys
from textwrap import wrap
from typing import Any, TextIO

from src.domain.conversion import (
    ConversionResult,
    ConversionStageRecord,
)


TABLE_WIDTH = 112
NAME_WIDTH = 36
STATUS_WIDTH = 21
MESSAGE_WIDTH = TABLE_WIDTH - NAME_WIDTH - STATUS_WIDTH - 6


def _wrapped(value: str, width: int) -> list[str]:
    return wrap(
        value.strip() or "-",
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or ["-"]


def _row_lines(
    name: str,
    status: str,
    message: str,
) -> list[str]:
    columns = (
        _wrapped(name, NAME_WIDTH),
        _wrapped(status, STATUS_WIDTH),
        _wrapped(message, MESSAGE_WIDTH),
    )
    height = max(len(column) for column in columns)
    lines: list[str] = []

    for index in range(height):
        values = tuple(
            column[index] if index < len(column) else ""
            for column in columns
        )
        lines.append(
            f"{values[0]:<{NAME_WIDTH}}  "
            f"{values[1]:<{STATUS_WIDTH}}  "
            f"{values[2]}"
        )

    return lines


def _unique_records(
    records: Iterable[ConversionStageRecord],
) -> tuple[ConversionStageRecord, ...]:
    """Preserva a ordem e evita repetição visual da mesma ocorrência."""

    unique: list[ConversionStageRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (
            record.stage.value,
            record.status.value,
            record.message,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return tuple(unique)


def print_execution_steps(
    records: Iterable[ConversionStageRecord],
    *,
    final_status: str,
    final_message: str,
    stream: TextIO | None = None,
) -> None:
    """Imprime somente etapa, situação e mensagem, na ordem recebida."""

    output = stream or sys.stdout
    print("ETAPAS DA EXECUÇÃO", file=output)
    print("=" * TABLE_WIDTH, file=output)
    print(
        f"{'Etapa':<{NAME_WIDTH}}  "
        f"{'Situação':<{STATUS_WIDTH}}  "
        "Mensagem",
        file=output,
    )
    print("-" * TABLE_WIDTH, file=output)

    for record in _unique_records(records):
        for line in _row_lines(
            record.stage.value,
            record.status.value,
            record.message,
        ):
            print(line, file=output)

    for line in _row_lines(
        "Status final",
        final_status,
        final_message,
    ):
        print(line, file=output)
    print("=" * TABLE_WIDTH, file=output)


def print_conversion_result(
    result: ConversionResult,
    *,
    stream: TextIO | None = None,
) -> None:
    """Renderiza um resultado sem reconstruir decisões regulatórias."""

    print_execution_steps(
        result.stage_records,
        final_status=result.status.value,
        final_message=result.final_message,
        stream=stream,
    )


def print_conversion_summary(
    result: ConversionResult,
    *,
    stream: TextIO | None = None,
) -> None:
    """Imprime no terminal o resumo da conversão iniciada pela GUI."""

    output = stream or sys.stdout
    heading = (
        "Falha técnica."
        if result.has_technical_failure
        else "Conversão concluída."
    )
    print(heading, file=output)
    print(file=output)
    print(f"Status local: {result.status_local.value}", file=output)
    print(f"Validação XSD: {result.status_xsd.value}", file=output)
    print(
        f"Validações externas: {result.status_externo.value}",
        file=output,
    )
    print(
        f"Validações históricas: {result.status_historico.value}",
        file=output,
    )
    print(f"Status final: {result.status.value}", file=output)
    print(file=output)
    print(result.final_message, file=output)


def print_gui_conversion_result(
    result: ConversionResult,
    *,
    stream: TextIO | None = None,
) -> None:
    """Imprime etapas e preserva o resumo atual da execução da GUI."""

    output = stream or sys.stdout
    print_conversion_result(result, stream=output)
    print(file=output)
    print_conversion_summary(result, stream=output)


def print_interface_failure(
    *,
    code: str,
    message: str,
    exception_type: str,
    details: tuple[tuple[str, Any], ...] = (),
    stream: TextIO | None = None,
) -> None:
    """Imprime uma exceção capturada pelo controller da interface."""

    output = stream or sys.stdout
    print("Falha técnica.", file=output)
    print(file=output)
    print(f"Código: {code}", file=output)
    print(f"Tipo: {exception_type}", file=output)
    print(f"Mensagem: {message}", file=output)
    for key, value in details:
        print(f"{key}: {value}", file=output)


def print_execution_failure(
    stage: str,
    message: str,
    *,
    stream: TextIO | None = None,
) -> None:
    """Apresenta uma falha anterior à criação de ConversionResult."""

    output = stream or sys.stdout
    print("ETAPAS DA EXECUÇÃO", file=output)
    print("=" * TABLE_WIDTH, file=output)
    print(
        f"{'Etapa':<{NAME_WIDTH}}  "
        f"{'Situação':<{STATUS_WIDTH}}  "
        "Mensagem",
        file=output,
    )
    print("-" * TABLE_WIDTH, file=output)
    for line in _row_lines(stage, "FALHA TÉCNICA", message):
        print(line, file=output)
    for line in _row_lines(
        "Status final",
        "FALHA TÉCNICA",
        "Conversão interrompida.",
    ):
        print(line, file=output)
    print("=" * TABLE_WIDTH, file=output)
