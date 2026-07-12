"""Testes da estrutura simplificada do relatório XLSX."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook

from src.domain.reporting import (
    ExternalValidationStatus,
    ExecutionReportData,
    FinalExecutionStatus,
    HistoricalValidationStatus,
    LocalValidationStatus,
    ReportRecord,
    XsdValidationSummaryStatus,
)
from src.reporters.xlsx_reporter import (
    OCCURRENCE_HEADERS,
    XlsxReportWriter,
)


REMOVED_SUMMARY_LABELS = {
    "Execução",
    "Início",
    "Fim",
    "Duração (segundos)",
    "dataBase",
    "Perfil",
}

REMOVED_OCCURRENCE_HEADERS = {
    "Execução",
    "Data/Hora",
    "Arquivo de Entrada",
    "Arquivo XML",
}


class SimplifiedXlsxReporterTests(unittest.TestCase):
    def test_report_contains_only_requested_summary_and_columns(self) -> None:
        now = datetime.now().astimezone()
        record = ReportRecord(
            execution_id="exec-1",
            executed_at=now,
            final_result=FinalExecutionStatus.NOT_APT,
            input_file="entrada.xlsx",
            xml_file="saida.xml",
            stage="VALIDAÇÃO",
            sheet_name="Base",
            row_numbers="2",
            id_evento="EVT-1",
            columns="A",
            original_value="x",
            normalized_value="X",
            rule_code="REG-1",
            rule_description="Regra de teste",
            source="Teste",
            version="1",
            severity="ERRO IMPEDITIVO",
            status="REPROVADA",
            suggestion="Corrigir",
            message="Valor inválido",
        )
        data = ExecutionReportData(
            execution_id="exec-1",
            started_at=now,
            finished_at=now + timedelta(seconds=2),
            input_path=Path("entrada.xlsx"),
            xml_path=Path("saida.xml"),
            xsd_path=Path("schema.xsd"),
            data_base="2026-06",
            profile_code="DRO_2025_06",
            status_local=LocalValidationStatus.APPROVED,
            status_xsd=XsdValidationSummaryStatus.APPROVED,
            status_externo=ExternalValidationStatus.NOT_EXECUTED,
            status_historico=(
                HistoricalValidationStatus.NOT_EXECUTED
            ),
            final_status=FinalExecutionStatus.NOT_APT,
            final_message="Há pendências",
            records=(record,),
            pre_rules=(),
            post_rules=(),
            metrics=(("Registros", 1),),
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "relatorio.xlsx"
            XlsxReportWriter().write(data, output)
            workbook = load_workbook(output, data_only=False)

        self.assertEqual(workbook.sheetnames, ["Resumo", "Ocorrencias"])

        summary = workbook["Resumo"]
        summary_values = {
            cell.value
            for row in summary.iter_rows()
            for cell in row
            if isinstance(cell.value, str)
        }
        self.assertTrue(REMOVED_SUMMARY_LABELS.isdisjoint(summary_values))
        self.assertEqual(summary["A4"].value, "Resultado final")
        self.assertEqual(summary["A5"].value, "Status local")
        self.assertEqual(summary["B5"].value, "APROVADO")
        self.assertEqual(summary["A6"].value, "Status XSD")
        self.assertEqual(summary["B6"].value, "APROVADO")
        self.assertEqual(summary["A7"].value, "Status externo")
        self.assertEqual(summary["B7"].value, "NAO_EXECUTADO")
        self.assertEqual(summary["A8"].value, "Status histórico")
        self.assertEqual(summary["B8"].value, "NAO_EXECUTADO")
        self.assertEqual(summary["A9"].value, "Mensagem final")
        self.assertIn("$M$2:$M$2", summary["H4"].value)
        self.assertIn("$N$2:$N$2", summary["H8"].value)

        occurrences = workbook["Ocorrencias"]
        headers = tuple(cell.value for cell in occurrences[1])
        self.assertEqual(headers, OCCURRENCE_HEADERS)
        self.assertEqual(len(headers), 19)
        self.assertTrue(REMOVED_OCCURRENCE_HEADERS.isdisjoint(headers))
        self.assertEqual(occurrences["A2"].value, "NÃO APTO PARA ENVIO")
        self.assertEqual(occurrences["M2"].value, "ERRO IMPEDITIVO")
        self.assertEqual(occurrences["N2"].value, "REPROVADA")
        self.assertEqual(occurrences.freeze_panes, "A2")
        self.assertEqual(occurrences.tables["OccurrencesTable"].ref, "A1:S2")


if __name__ == "__main__":
    unittest.main()
