"""Leitura e normalização de todas as linhas da aba ``Base``."""

from __future__ import annotations

from src.config import BASE_ALL_COLUMNS, SHEET_BASE
from src.domain.base_row import BaseRowsNormalizationResult
from src.domain.regulatory_version import RegulatoryVersion
from src.normalizers.base_row_normalizer import (
    BaseRowNormalizer,
)
from src.readers.excel_reader import ExcelReadResult


class BaseSheetReader:
    """Coordena a leitura bruta e a normalização linha a linha."""

    def read_and_normalize(
        self,
        excel_result: ExcelReadResult,
        profile: RegulatoryVersion,
    ) -> BaseRowsNormalizationResult:
        sheet = excel_result.get_sheet(SHEET_BASE)
        normalizer = BaseRowNormalizer(profile)

        rows = tuple(
            normalizer.normalize(
                row,
                available_columns=sheet.headers,
            )
            for row in sheet.rows
        )
        issues = tuple(
            issue
            for row in rows
            for issue in row.issues
        )
        ignored_extra_columns = tuple(
            column_name
            for column_name in sheet.headers
            if column_name not in BASE_ALL_COLUMNS
        )

        return BaseRowsNormalizationResult(
            sheet_name=sheet.name,
            profile_code=profile.code,
            rows=rows,
            issues=issues,
            ignored_extra_columns=ignored_extra_columns,
        )


def read_and_normalize_base(
    excel_result: ExcelReadResult,
    profile: RegulatoryVersion,
) -> BaseRowsNormalizationResult:
    """Atalho funcional para o leitor da Base."""

    return BaseSheetReader().read_and_normalize(
        excel_result,
        profile,
    )
