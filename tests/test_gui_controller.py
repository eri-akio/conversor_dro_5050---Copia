"""Testes do controlador assíncrono da interface."""

from __future__ import annotations

from pathlib import Path
from threading import Event
import time
from types import MappingProxyType, SimpleNamespace

from src.gui.controller import GuiController
from src.gui.models import (
    GuiEventKind,
    GuiOutputDirectories,
    GuiTaskKind,
    HeaderPreviewResult,
)


def wait_event(
    controller: GuiController,
    kind: GuiEventKind,
    *,
    timeout: float = 3.0,
):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        event = controller.get_event_nowait()
        if event is None:
            time.sleep(0.01)
            continue

        if event.kind == kind:
            return event

    raise AssertionError(
        f"Evento não recebido: {kind}"
    )


def preview_result(
    path: str | Path,
) -> HeaderPreviewResult:
    return HeaderPreviewResult(
        input_path=Path(path),
        is_valid=True,
        header_values=MappingProxyType(
            {
                "codigoDocumento": "5050",
                "dataBase": "2026-06",
            }
        ),
        profile_code="DRO_2025_06",
        instruction_version="12/2020",
        xsd_version="06/2025",
        xsd_path=Path("teste.xsd"),
        version_status="CONFIRMADA",
        blocks_apt=False,
        issues=(),
    )


def test_output_directories_are_derived_from_root(
    tmp_path: Path,
) -> None:
    directories = (
        GuiOutputDirectories.from_root(
            tmp_path / "saida"
        )
    )

    directories.ensure()

    assert directories.root.is_dir()
    assert not (directories.root / "xml").exists()
    assert not (directories.root / "relatorios").exists()
    assert not (directories.root / "logs").exists()


def test_preview_runs_in_background() -> None:
    controller = GuiController(
        preview_callable=preview_result,
    )

    assert controller.start_preview(
        "entrada.xlsx"
    )

    started = wait_event(
        controller,
        GuiEventKind.STARTED,
    )
    completed = wait_event(
        controller,
        GuiEventKind.COMPLETED,
    )

    assert started.task == GuiTaskKind.PREVIEW
    assert completed.task == GuiTaskKind.PREVIEW
    assert isinstance(
        completed.payload,
        HeaderPreviewResult,
    )
    assert completed.payload.can_convert


def test_conversion_receives_derived_directories(
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_convert(
        input_path,
        **kwargs,
    ):
        captured["input"] = input_path
        captured.update(kwargs)
        return SimpleNamespace(
            status="CONCLUÍDO"
        )

    controller = GuiController(
        preview_callable=preview_result,
        convert_callable=fake_convert,
    )

    output_root = tmp_path / "saida"
    assert controller.start_conversion(
        "entrada.xlsx",
        output_root,
    )

    wait_event(
        controller,
        GuiEventKind.STARTED,
    )
    completed = wait_event(
        controller,
        GuiEventKind.COMPLETED,
    )

    assert completed.task == (
        GuiTaskKind.CONVERSION
    )
    assert captured["output_dir"] == (
        output_root.resolve()
    )
    assert "reports_dir" not in captured
    assert "logs_dir" not in captured


def test_controller_rejects_second_operation(
    tmp_path: Path,
) -> None:
    release = Event()

    def slow_preview(path):
        release.wait(timeout=2)
        return preview_result(path)

    controller = GuiController(
        preview_callable=slow_preview,
    )

    assert controller.start_preview(
        "entrada.xlsx"
    )
    assert not controller.start_conversion(
        "entrada.xlsx",
        tmp_path,
    )

    wait_event(
        controller,
        GuiEventKind.STARTED,
    )
    rejected = wait_event(
        controller,
        GuiEventKind.REJECTED,
    )

    assert rejected.task == (
        GuiTaskKind.CONVERSION
    )
    release.set()

    wait_event(
        controller,
        GuiEventKind.COMPLETED,
    )


def test_controller_converts_exception_to_failed_event() -> None:
    def broken_preview(path):
        raise ValueError("falha simulada")

    controller = GuiController(
        preview_callable=broken_preview,
    )
    controller.start_preview(
        "entrada.xlsx"
    )

    wait_event(
        controller,
        GuiEventKind.STARTED,
    )
    failed = wait_event(
        controller,
        GuiEventKind.FAILED,
    )

    assert failed.payload.code == "GUI-TEC-001"
    assert (
        failed.payload.exception_type
        == "ValueError"
    )
