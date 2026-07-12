"""Controlador assíncrono usado pela janela Tkinter."""

from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any, Callable

from src.domain.conversion import (
    ConversionResult,
)
from src.gui.header_preview_service import (
    HeaderPreviewService,
)
from src.gui.models import (
    GuiEvent,
    GuiEventKind,
    GuiOutputDirectories,
    GuiTaskError,
    GuiTaskKind,
    HeaderPreviewResult,
)
from src.services.conversion_service import (
    convert_excel,
)


PreviewCallable = Callable[
    [str | Path],
    HeaderPreviewResult,
]
ConvertCallable = Callable[..., ConversionResult]


class GuiController:
    """Executa leitura e conversão fora da thread principal."""

    def __init__(
        self,
        *,
        preview_callable: PreviewCallable | None = None,
        convert_callable: ConvertCallable | None = None,
    ) -> None:
        self._preview = (
            preview_callable
            or HeaderPreviewService().preview
        )
        self._convert = (
            convert_callable
            or convert_excel
        )
        self._events: Queue[GuiEvent] = Queue()
        self._lock = Lock()
        self._busy = False
        self._closed = False

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    def start_preview(
        self,
        input_path: str | Path,
    ) -> bool:
        """Agenda a leitura do cabeçalho."""

        return self._start(
            task=GuiTaskKind.PREVIEW,
            target=lambda: self._preview(
                input_path
            ),
            started_message=(
                "Lendo o cabeçalho e selecionando "
                "a versão regulatória..."
            ),
            completed_message=(
                "Cabeçalho carregado."
            ),
        )

    def start_conversion(
        self,
        input_path: str | Path,
        output_root: str | Path,
    ) -> bool:
        """Agenda a conversão completa."""

        directories = (
            GuiOutputDirectories.from_root(
                output_root
            )
        )

        def convert() -> ConversionResult:
            directories.ensure()
            return self._convert(
                input_path,
                output_dir=directories.root,
            )

        return self._start(
            task=GuiTaskKind.CONVERSION,
            target=convert,
            started_message=(
                "Conversão iniciada. A interface "
                "continuará responsiva."
            ),
            completed_message=(
                "Conversão concluída."
            ),
        )

    def get_event_nowait(
        self,
    ) -> GuiEvent | None:
        """Retorna o próximo evento sem bloquear a janela."""

        try:
            return self._events.get_nowait()
        except Empty:
            return None

    def close(self) -> None:
        """Impede o início de novos trabalhos."""

        with self._lock:
            self._closed = True

    def _start(
        self,
        *,
        task: GuiTaskKind,
        target: Callable[[], Any],
        started_message: str,
        completed_message: str,
    ) -> bool:
        with self._lock:
            if self._closed:
                self._events.put(
                    GuiEvent(
                        task=task,
                        kind=(
                            GuiEventKind
                            .REJECTED
                        ),
                        message=(
                            "A interface está sendo "
                            "encerrada."
                        ),
                    )
                )
                return False

            if self._busy:
                self._events.put(
                    GuiEvent(
                        task=task,
                        kind=(
                            GuiEventKind
                            .REJECTED
                        ),
                        message=(
                            "Já existe uma operação "
                            "em andamento."
                        ),
                    )
                )
                return False

            self._busy = True

        self._events.put(
            GuiEvent(
                task=task,
                kind=GuiEventKind.STARTED,
                message=started_message,
            )
        )

        worker = Thread(
            target=self._run,
            kwargs={
                "task": task,
                "target": target,
                "completed_message": (
                    completed_message
                ),
            },
            name=(
                "dro5050-"
                + task.name.lower()
            ),
            daemon=True,
        )
        worker.start()
        return True

    def _run(
        self,
        *,
        task: GuiTaskKind,
        target: Callable[[], Any],
        completed_message: str,
    ) -> None:
        try:
            payload = target()
            event = GuiEvent(
                task=task,
                kind=GuiEventKind.COMPLETED,
                message=completed_message,
                payload=payload,
            )
        except Exception as error:
            raw_details = getattr(
                error,
                "details",
                (),
            )
            if isinstance(raw_details, dict):
                details = tuple(
                    raw_details.items()
                )
            else:
                details = tuple(
                    raw_details or ()
                )

            event = GuiEvent(
                task=task,
                kind=GuiEventKind.FAILED,
                message=str(error),
                payload=GuiTaskError(
                    code=str(
                        getattr(
                            error,
                            "code",
                            "GUI-TEC-001",
                        )
                    ),
                    message=str(
                        getattr(
                            error,
                            "message",
                            error,
                        )
                    ),
                    exception_type=(
                        type(error).__name__
                    ),
                    details=details,
                ),
            )
        finally:
            with self._lock:
                self._busy = False

        self._events.put(event)
