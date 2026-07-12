"""Garante que somente XML e XLSX pertencem à saída da aplicação."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.domain.conversion import ConversionRequest
from src.domain.reporting import ExecutionReportData, FinalExecutionStatus
from src.gui.models import GuiOutputDirectories
from src.services.reporting_service import ReportingService


class OutputArtifactsOnlyTests(unittest.TestCase):
    def test_reporting_service_creates_only_xlsx(self) -> None:
        now = datetime.now().astimezone()
        data = ExecutionReportData(
            execution_id="exec-1",
            started_at=now,
            finished_at=now,
            input_path=Path("entrada.xlsx"),
            xml_path=Path("saida.xml"),
            xsd_path=None,
            data_base="2026-06",
            profile_code="DRO_2025_06",
            final_status=FinalExecutionStatus.APT,
            final_message="Processamento concluído.",
            records=(),
            pre_rules=(),
            post_rules=(),
            metrics=(),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = ReportingService().generate(
                data,
                output_dir=root,
            )

            self.assertTrue(result.is_generated)
            self.assertEqual(
                list(root.iterdir()),
                [result.artifacts.xlsx_path],
            )
            self.assertFalse((root / "logs").exists())
            self.assertFalse(any(root.rglob("*.txt")))
            self.assertFalse(any(root.rglob("*.log")))

    def test_gui_and_request_have_no_logs_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "saida"
            directories = GuiOutputDirectories.from_root(root)
            directories.ensure()

            self.assertTrue(directories.root.is_dir())
            self.assertFalse((root / "xml").exists())
            self.assertFalse((root / "relatorios").exists())
            self.assertFalse((root / "logs").exists())

            request = ConversionRequest.create(
                "entrada.xlsx",
                output_dir=directories.root,
            )
            self.assertFalse(hasattr(request, "logs_dir"))
            self.assertFalse(hasattr(request, "reports_dir"))


if __name__ == "__main__":
    unittest.main()
