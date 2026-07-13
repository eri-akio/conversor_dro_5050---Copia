"""Janela principal simplificada do Conversor XLSX → XML DRO 5050."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from src.domain.conversion import ConversionResult
from src.gui.controller import GuiController
from src.gui.models import (
    GuiEvent,
    GuiEventKind,
    GuiTaskError,
    GuiTaskKind,
)
from src.gui.system_utils import (
    default_dialog_directory,
    default_output_root,
    open_path,
)
from src.presenters import print_interface_failure


POLL_INTERVAL_MS = 150
STATUS_AWAITING = "Aguardando"
STATUS_PROCESSING = "Processando..."
STATUS_COMPLETED = "Concluído"
STATUS_TECHNICAL_FAILURE = "Falha técnica"
PATH_ENTRY_WIDTH = 62
SELECT_BUTTON_WIDTH = 16
ACTION_BUTTON_WIDTH = 38


class Dro5050Application(ttk.Frame):
    """Interface desktop simplificada do conversor."""

    def __init__(
        self,
        master: tk.Tk,
        *,
        controller: GuiController | None = None,
        initial_excel: str | Path | None = None,
        initial_output_root: str | Path | None = None,
    ) -> None:
        super().__init__(master, padding=14)
        self.master = master
        self.controller = controller or GuiController()
        self._result: ConversionResult | None = None
        self._artifact_paths: dict[str, Path | None] = {}

        self.excel_var = tk.StringVar(
            value=str(initial_excel) if initial_excel else ""
        )
        self.output_root_var = tk.StringVar(
            value=str(initial_output_root or default_output_root())
        )
        self.status_var = tk.StringVar(value=STATUS_AWAITING)
        self._configure_window()
        self._configure_styles()
        self._build_widgets()
        self._set_artifact_buttons_state(False)
        self.master.protocol(
            "WM_DELETE_WINDOW",
            self._on_close,
        )
        self.master.after(
            POLL_INTERVAL_MS,
            self._poll_events,
        )

    def _configure_window(self) -> None:
        self.master.title("Smart Reporting")
        self.master.geometry("720x430")
        self.master.minsize(720, 430)
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.master)

        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 17, "bold"),
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 7),
        )
        style.configure(
            "StatusAwaiting.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#4A5568",
        )
        style.configure(
            "StatusProcessing.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#1D4ED8",
        )
        style.configure(
            "StatusCompleted.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#137333",
        )
        style.configure(
            "StatusFailure.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#B91C1C",
        )

    def _build_widgets(self) -> None:
        self._build_title()
        self._build_selection()

    def _build_title(self) -> None:
        ttk.Label(
            self,
            text="Smart Reporting - CADOC 5050",
            style="Title.TLabel",
        ).grid(
            row=0,
            column=0,
            pady=(0, 18),
        )

    def _build_selection(self) -> None:
        frame = ttk.Frame(self, padding=12)
        frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 4),
        )
        ttk.Label(
            frame,
            text="Planilha Excel:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        self.excel_entry = ttk.Entry(
            frame,
            textvariable=self.excel_var,
            width=PATH_ENTRY_WIDTH,
        )
        self.excel_entry.grid(
            row=0,
            column=1,
            pady=4,
        )

        self.browse_excel_button = ttk.Button(
            frame,
            text="Selecionar",
            command=self._browse_excel,
            width=SELECT_BUTTON_WIDTH,
        )
        self.browse_excel_button.grid(
            row=0,
            column=2,
            padx=(8, 0),
            pady=4,
        )

        ttk.Label(
            frame,
            text="Pasta de saída:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        self.output_entry = ttk.Entry(
            frame,
            textvariable=self.output_root_var,
            width=PATH_ENTRY_WIDTH,
        )
        self.output_entry.grid(
            row=1,
            column=1,
            pady=4,
        )

        self.browse_output_button = ttk.Button(
            frame,
            text="Selecionar",
            command=self._browse_output,
            width=SELECT_BUTTON_WIDTH,
        )
        self.browse_output_button.grid(
            row=1,
            column=2,
            padx=(8, 0),
            pady=4,
        )

        self.open_output_button = ttk.Button(
            frame,
            text="Abrir pasta",
            command=self._open_output_root,
        )
        self.open_output_button.grid(
            row=1,
            column=3,
            padx=(8, 0),
            pady=4,
        )

        status_frame = ttk.Frame(frame)
        status_frame.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(14, 8),
        )
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(3, weight=1)
        ttk.Label(
            status_frame,
            text="Status:",
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, padx=(0, 8))
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="StatusAwaiting.TLabel",
        )
        self.status_label.grid(row=0, column=2)

        action_frame = ttk.Frame(frame)
        action_frame.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(8, 0),
        )
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(2, weight=1)

        self.convert_button = ttk.Button(
            action_frame,
            text="Converter, validar e gerar XML/XLSX",
            command=self._start_conversion,
            style="Primary.TButton",
            width=ACTION_BUTTON_WIDTH,
        )
        self.convert_button.grid(
            row=0,
            column=1,
            pady=(0, 8),
        )
        self.artifact_buttons = {
            "xml": ttk.Button(
                action_frame,
                text="Abrir XML",
                command=lambda: self._open_artifact("xml"),
                width=ACTION_BUTTON_WIDTH,
            ),
            "xlsx": ttk.Button(
                action_frame,
                text="Abrir relatório XLSX",
                command=lambda: self._open_artifact("xlsx"),
                width=ACTION_BUTTON_WIDTH,
            ),
        }
        self.artifact_buttons["xml"].grid(
            row=1,
            column=1,
            pady=(0, 8),
        )
        self.artifact_buttons["xlsx"].grid(
            row=2,
            column=1,
        )

    def _browse_excel(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.master,
            title="Selecione a planilha DRO 5050",
            initialdir=str(
                default_dialog_directory()
            ),
            filetypes=(
                ("Planilhas Excel", "*.xlsx"),
                ("Todos os arquivos", "*.*"),
            ),
        )

        if not selected:
            return

        self.excel_var.set(selected)
        self._clear_result()

    def _browse_output(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.master,
            title="Selecione a pasta principal de saída",
            initialdir=self.output_root_var.get()
            or str(default_dialog_directory()),
            mustexist=False,
        )

        if selected:
            self.output_root_var.set(selected)

    def _start_conversion(self) -> None:
        path = self._validated_excel_path()
        if path is None:
            return

        output_root = (
            self.output_root_var.get().strip()
        )
        if not output_root:
            messagebox.showerror(
                "Pasta de saída",
                "Selecione a pasta principal de saída.",
                parent=self.master,
            )
            return

        self._clear_result()
        self.controller.start_conversion(
            path,
            output_root,
        )

    def _validated_excel_path(
        self,
    ) -> Path | None:
        raw_path = self.excel_var.get().strip()

        if not raw_path:
            messagebox.showerror(
                "Planilha Excel",
                "Selecione uma planilha .xlsx.",
                parent=self.master,
            )
            return None

        path = Path(
            raw_path
        ).expanduser().resolve()

        if path.suffix.lower() != ".xlsx":
            messagebox.showerror(
                "Planilha Excel",
                "O arquivo precisa possuir a extensão .xlsx.",
                parent=self.master,
            )
            return None

        if not path.is_file():
            messagebox.showerror(
                "Planilha Excel",
                f"Arquivo não encontrado:\n{path}",
                parent=self.master,
            )
            return None

        return path

    def _poll_events(self) -> None:
        while True:
            event = self.controller.get_event_nowait()
            if event is None:
                break
            self._handle_event(event)

        if self.master.winfo_exists():
            self.master.after(
                POLL_INTERVAL_MS,
                self._poll_events,
            )

    def _handle_event(
        self,
        event: GuiEvent,
    ) -> None:
        if event.kind == GuiEventKind.STARTED:
            self._set_busy(True)
            self._set_status(
                STATUS_PROCESSING,
                "StatusProcessing.TLabel",
            )
            return

        if event.kind == GuiEventKind.REJECTED:
            messagebox.showwarning(
                "Operação não iniciada",
                event.message,
                parent=self.master,
            )
            return

        self._set_busy(False)

        if event.kind == GuiEventKind.FAILED:
            self._handle_task_error(
                event.task,
                event.payload,
            )
            return

        if (
            event.task == GuiTaskKind.CONVERSION
            and isinstance(
                event.payload,
                ConversionResult,
            )
        ):
            self._show_conversion_result(
                event.payload
            )

    def _show_conversion_result(
        self,
        result: ConversionResult,
    ) -> None:
        self._result = result
        self._artifact_paths = {
            "xml": result.artifacts.xml_path,
            "xlsx": result.artifacts.xlsx_path,
        }
        self._set_artifact_buttons_state(True)

        if result.has_technical_failure:
            self._set_status(
                STATUS_TECHNICAL_FAILURE,
                "StatusFailure.TLabel",
            )
            messagebox.showerror(
                "Falha técnica",
                result.final_message,
                parent=self.master,
            )
            return

        self._set_status(
            STATUS_COMPLETED,
            "StatusCompleted.TLabel",
        )

    def _handle_task_error(
        self,
        task: GuiTaskKind,
        payload: Any,
    ) -> None:
        error = (
            payload
            if isinstance(payload, GuiTaskError)
            else GuiTaskError(
                code="GUI-TEC-001",
                message=str(payload),
                exception_type=type(payload).__name__,
            )
        )

        self._set_status(
            STATUS_TECHNICAL_FAILURE,
            "StatusFailure.TLabel",
        )
        print_interface_failure(
            code=error.code,
            message=error.message,
            exception_type=error.exception_type,
            details=error.details,
        )
        messagebox.showerror(
            f"Falha em {task.value}",
            f"{error.code}\n\n{error.message}",
            parent=self.master,
        )

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"

        for widget in (
            self.browse_excel_button,
            self.browse_output_button,
            self.convert_button,
        ):
            widget.configure(state=state)

        self.excel_entry.configure(state=state)
        self.output_entry.configure(state=state)

    def _set_artifact_buttons_state(
        self,
        enabled: bool,
    ) -> None:
        for key, button in (
            self.artifact_buttons.items()
        ):
            path = self._artifact_paths.get(key)
            state = (
                "normal"
                if (
                    enabled
                    and path is not None
                    and path.is_file()
                )
                else "disabled"
            )
            button.configure(state=state)

    def _open_artifact(
        self,
        key: str,
    ) -> None:
        path = self._artifact_paths.get(key)
        if path is None:
            return

        try:
            open_path(path)
        except Exception as error:
            messagebox.showerror(
                "Abrir arquivo",
                str(error),
                parent=self.master,
            )

    def _open_output_root(self) -> None:
        root = self.output_root_var.get().strip()
        if not root:
            return

        path = Path(
            root
        ).expanduser().resolve()
        path.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            open_path(path)
        except Exception as error:
            messagebox.showerror(
                "Abrir pasta",
                str(error),
                parent=self.master,
            )

    def _clear_result(self) -> None:
        self._result = None
        self._artifact_paths.clear()
        self._set_artifact_buttons_state(False)
        self._set_status(
            STATUS_AWAITING,
            "StatusAwaiting.TLabel",
        )

    def _set_status(
        self,
        text: str,
        style: str,
    ) -> None:
        self.status_var.set(text)
        self.status_label.configure(style=style)

    def _on_close(self) -> None:
        if self.controller.busy:
            close_anyway = messagebox.askyesno(
                "Operação em andamento",
                (
                    "Existe uma operação em andamento. "
                    "Encerrar a aplicação mesmo assim?"
                ),
                parent=self.master,
            )
            if not close_anyway:
                return

        self.controller.close()
        self.master.destroy()


def launch_gui(
    *,
    initial_excel: str | Path | None = None,
    initial_output_root: str | Path | None = None,
) -> int:
    """Cria a janela e inicia o loop do Tkinter."""

    root = tk.Tk()
    Dro5050Application(
        root,
        initial_excel=initial_excel,
        initial_output_root=initial_output_root,
    )
    root.mainloop()
    return 0
