"""Janela principal simplificada do Conversor XLSX → XML DRO 5050."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from src.config import PROJECT_NAME
from src.domain.conversion import ConversionResult
from src.domain.reporting import FinalExecutionStatus
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


POLL_INTERVAL_MS = 150


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
        self.output_hint_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Selecione uma planilha Excel."
        )
        self.result_var = tk.StringVar(
            value="AGUARDANDO EXECUÇÃO"
        )

        self._configure_window()
        self._configure_styles()
        self._build_widgets()
        self._update_output_hint()
        self._set_artifact_buttons_state(False)

        self.output_root_var.trace_add(
            "write",
            lambda *_: self._update_output_hint(),
        )
        self.master.protocol(
            "WM_DELETE_WINDOW",
            self._on_close,
        )
        self.master.after(
            POLL_INTERVAL_MS,
            self._poll_events,
        )

    def _configure_window(self) -> None:
        self.master.title(PROJECT_NAME)
        self.master.geometry("1120x700")
        self.master.minsize(920, 620)
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

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
            "Subtitle.TLabel",
            font=("Segoe UI", 9),
            foreground="#4A5568",
        )
        style.configure(
            "Section.TLabelframe.Label",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Status.TLabel",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 5),
        )
        style.configure(
            "ResultWaiting.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="#4A5568",
        )
        style.configure(
            "ResultApt.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="#137333",
        )
        style.configure(
            "ResultNotApt.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="#B45309",
        )
        style.configure(
            "ResultFailure.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="#B91C1C",
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 7),
        )
        style.configure("Treeview", rowheight=25)

    def _build_widgets(self) -> None:
        self._build_title()
        self._build_selection()
        self._build_results()
        self._build_status_bar()

    def _build_title(self) -> None:
        title_frame = ttk.Frame(self)
        title_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )
        title_frame.columnconfigure(0, weight=1)

        ttk.Label(
            title_frame,
            text="Conversor XLSX → XML DRO 5050",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            title_frame,
            text=(
                "Selecione o Excel, escolha a pasta de saída "
                "e execute a conversão completa."
            ),
            style="Subtitle.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(3, 0),
        )

    def _build_selection(self) -> None:
        frame = ttk.LabelFrame(
            self,
            text="1. Arquivos da execução",
            style="Section.TLabelframe",
            padding=12,
        )
        frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )
        frame.columnconfigure(1, weight=1)

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
        )
        self.excel_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        self.browse_excel_button = ttk.Button(
            frame,
            text="Selecionar...",
            command=self._browse_excel,
        )
        self.browse_excel_button.grid(
            row=0,
            column=2,
            padx=(8, 0),
            pady=4,
        )

        ttk.Label(
            frame,
            text="Pasta principal de saída:",
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
        )
        self.output_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
        )

        self.browse_output_button = ttk.Button(
            frame,
            text="Selecionar...",
            command=self._browse_output,
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

        ttk.Label(
            frame,
            textvariable=self.output_hint_var,
            style="Subtitle.TLabel",
        ).grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="w",
            pady=(2, 8),
        )

        action_frame = ttk.Frame(frame)
        action_frame.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(4, 0),
        )
        action_frame.columnconfigure(0, weight=1)

        ttk.Label(
            action_frame,
            text=(
                "A versão regulatória será selecionada "
                "automaticamente pela dataBase."
            ),
            style="Subtitle.TLabel",
        ).grid(row=0, column=0, sticky="w")

        self.convert_button = ttk.Button(
            action_frame,
            text="Converter, validar e gerar XML/XLSX",
            command=self._start_conversion,
            style="Primary.TButton",
        )
        self.convert_button.grid(
            row=0,
            column=1,
            sticky="e",
        )

    def _build_results(self) -> None:
        frame = ttk.LabelFrame(
            self,
            text="2. Resultado da execução",
            style="Section.TLabelframe",
            padding=10,
        )
        frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 10),
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        summary = ttk.Frame(frame)
        summary.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        summary.columnconfigure(0, weight=1)

        self.result_label = ttk.Label(
            summary,
            textvariable=self.result_var,
            style="ResultWaiting.TLabel",
        )
        self.result_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        artifact_frame = ttk.Frame(summary)
        artifact_frame.grid(
            row=0,
            column=1,
            sticky="e",
        )

        self.artifact_buttons = {
            "xml": ttk.Button(
                artifact_frame,
                text="Abrir XML",
                command=lambda: self._open_artifact("xml"),
            ),
            "xlsx": ttk.Button(
                artifact_frame,
                text="Abrir relatório XLSX",
                command=lambda: self._open_artifact("xlsx"),
            ),
        }

        for index, button in enumerate(
            self.artifact_buttons.values()
        ):
            button.grid(
                row=0,
                column=index,
                padx=(6, 0),
            )

        notebook = ttk.Notebook(frame)
        notebook.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        stages_tab = ttk.Frame(
            notebook,
            padding=6,
        )
        messages_tab = ttk.Frame(
            notebook,
            padding=6,
        )
        notebook.add(stages_tab, text="Etapas")
        notebook.add(
            messages_tab,
            text="Mensagens e motivos",
        )

        stages_tab.columnconfigure(0, weight=1)
        stages_tab.rowconfigure(0, weight=1)

        self.stage_tree = ttk.Treeview(
            stages_tab,
            columns=(
                "status",
                "duration",
                "message",
            ),
            show="tree headings",
        )
        self.stage_tree.heading("#0", text="Etapa")
        self.stage_tree.heading(
            "status",
            text="Situação",
        )
        self.stage_tree.heading(
            "duration",
            text="Duração",
        )
        self.stage_tree.heading(
            "message",
            text="Mensagem",
        )
        self.stage_tree.column(
            "#0",
            width=230,
            stretch=False,
        )
        self.stage_tree.column(
            "status",
            width=170,
            stretch=False,
        )
        self.stage_tree.column(
            "duration",
            width=90,
            anchor="e",
            stretch=False,
        )
        self.stage_tree.column(
            "message",
            width=500,
            stretch=True,
        )
        self.stage_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        tree_scroll = ttk.Scrollbar(
            stages_tab,
            orient="vertical",
            command=self.stage_tree.yview,
        )
        tree_scroll.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        self.stage_tree.configure(
            yscrollcommand=tree_scroll.set
        )

        messages_tab.columnconfigure(0, weight=1)
        messages_tab.rowconfigure(0, weight=1)

        self.messages_text = tk.Text(
            messages_tab,
            wrap="word",
            height=12,
            font=("Consolas", 9),
            state="disabled",
            padx=8,
            pady=8,
        )
        self.messages_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        messages_scroll = ttk.Scrollbar(
            messages_tab,
            orient="vertical",
            command=self.messages_text.yview,
        )
        messages_scroll.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        self.messages_text.configure(
            yscrollcommand=messages_scroll.set
        )

    def _build_status_bar(self) -> None:
        frame = ttk.Frame(self)
        frame.grid(row=3, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).grid(row=0, column=0, sticky="w")

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
        self.status_var.set(
            "Planilha selecionada. Pronto para converter."
        )
        self._append_message(
            f"Arquivo selecionado: {selected}"
        )

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
        self._append_message(
            f"Arquivo selecionado: {path}"
        )
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
            self.status_var.set(event.message)
            self._append_message(event.message)
            return

        if event.kind == GuiEventKind.REJECTED:
            self.status_var.set(event.message)
            self._append_message(event.message)
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
        self.result_var.set(result.status.value)

        style = {
            FinalExecutionStatus.APT: "ResultApt.TLabel",
            FinalExecutionStatus.NOT_APT: (
                "ResultNotApt.TLabel"
            ),
            FinalExecutionStatus.TECHNICAL_FAILURE: (
                "ResultFailure.TLabel"
            ),
        }[result.status]
        self.result_label.configure(style=style)

        for item in self.stage_tree.get_children():
            self.stage_tree.delete(item)

        for record in result.stage_records:
            self.stage_tree.insert(
                "",
                "end",
                text=record.stage.value,
                values=(
                    record.status.value,
                    f"{record.duration_seconds:.3f}s",
                    record.message,
                ),
            )

        self._append_message(
            f"Resultado final: {result.status.value}"
        )
        self._append_message(
            f"Execução: {result.execution_id}"
        )
        self._append_message(
            f"Mensagem: {result.final_message}"
        )

        for reason in result.decision.reasons:
            self._append_message(
                (
                    f"[{reason.severity}] "
                    f"{reason.code} — "
                    f"{reason.message}"
                )
            )

        self._artifact_paths = {
            "xml": result.artifacts.xml_path,
            "xlsx": result.artifacts.xlsx_path,
        }
        self._set_artifact_buttons_state(True)

        self.status_var.set(
            (
                "Execução concluída em "
                f"{result.duration_seconds:.3f}s."
            )
        )

        if result.has_technical_failure:
            messagebox.showerror(
                "Falha técnica",
                result.final_message,
                parent=self.master,
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

        self.status_var.set(
            "Falha técnica na interface."
        )
        self.result_var.set("FALHA TÉCNICA")
        self.result_label.configure(
            style="ResultFailure.TLabel"
        )
        self._append_message(
            (
                f"[FALHA TÉCNICA] {error.code} "
                f"— {error.message}"
            )
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

    def _update_output_hint(self) -> None:
        raw = self.output_root_var.get().strip()
        if not raw:
            self.output_hint_var.set("")
            return

        root = Path(raw).expanduser()
        self.output_hint_var.set(
            (
                f"XML e relatório Excel: {root}"
            )
        )

    def _clear_result(self) -> None:
        self._result = None
        self.result_var.set("AGUARDANDO EXECUÇÃO")
        self.result_label.configure(
            style="ResultWaiting.TLabel"
        )
        self._artifact_paths.clear()
        self._set_artifact_buttons_state(False)

        for item in self.stage_tree.get_children():
            self.stage_tree.delete(item)

        self.messages_text.configure(state="normal")
        self.messages_text.delete("1.0", "end")
        self.messages_text.configure(state="disabled")

    def _append_message(
        self,
        message: str,
    ) -> None:
        self.messages_text.configure(state="normal")
        self.messages_text.insert(
            "end",
            message.rstrip() + "\n",
        )
        self.messages_text.see("end")
        self.messages_text.configure(state="disabled")

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
