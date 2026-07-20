"""Validação estrutural da aba ``Base``.

Esta etapa valida somente o contrato de colunas e a existência de
linhas. Não valida valores, domínios, obrigatoriedades condicionais,
agrupamentos ou totais.

Contratos por versão:

- ``DRO_2020_12`` e ``DRO_2025_06``:
  exigem as 32 colunas do leiaute confirmado;
  as três colunas 12/2026 são opcionais;
- ``DRO_2026_12_PRESUMIDA``:
  exige as 35 colunas, embora o perfil continue bloqueado para APTO
  pela incompatibilidade documental registrada.

Quando as referências não estão em abas próprias, três colunas de nomes
também são obrigatórias na ``Base``. Elas são opcionais no formato legado
de quatro abas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import (
    BASE_ALL_COLUMNS,
    BASE_CONFIRMED_REQUIRED_COLUMNS,
    BASE_EMBEDDED_REFERENCE_COLUMNS,
    BASE_FUTURE_COLUMNS,
    BASE_KNOWN_COLUMN_ALIASES,
    BASE_METADATA_COLUMNS,
    OPTIONAL_REFERENCE_SHEETS,
    SHEET_BASE,
)
from src.domain.regulatory_version import RegulatoryVersion
from src.readers.excel_reader import (
    ExcelReadResult,
    RawSheet,
)


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"

LEGACY_PROFILE_CODES = frozenset(
    {
        "DRO_2020_12",
        "DRO_2025_06",
    }
)
FUTURE_PROFILE_CODES = frozenset(
    {
        "DRO_2026_12_PRESUMIDA",
    }
)


@dataclass(frozen=True, slots=True)
class BaseColumnContract:
    """Contrato de colunas aplicável a um perfil regulatório."""

    profile_code: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    recognized_columns: tuple[str, ...]
    metadata_columns: tuple[str, ...] = (
        BASE_METADATA_COLUMNS
    )

    def is_required(self, column_name: str) -> bool:
        """Confirma se a coluna pertence ao conjunto obrigatório."""

        return column_name in self.required_columns

    def is_recognized(self, column_name: str) -> bool:
        """Confirma se a coluna faz parte do contrato conhecido."""

        return column_name in self.recognized_columns


@dataclass(frozen=True, slots=True)
class BaseStructureIssue:
    """Ocorrência produzida pela validação estrutural."""

    code: str
    severity: str
    message: str
    column_name: str | None = None
    suggested_column_name: str | None = None
    details: tuple[Any, ...] = ()

    @property
    def blocks_processing(self) -> bool:
        """Indica se a ocorrência impede continuar o fluxo."""

        return self.severity == SEVERITY_BLOCKING_ERROR


@dataclass(frozen=True, slots=True)
class BaseStructureValidationResult:
    """Resultado da validação estrutural da aba Base."""

    sheet_name: str
    profile_code: str
    row_count: int
    actual_columns: tuple[str, ...]
    contract: BaseColumnContract
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]
    future_columns_present: tuple[str, ...]
    issues: tuple[BaseStructureIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Verdadeiro quando não existem erros impeditivos."""

        return not any(
            issue.blocks_processing
            for issue in self.issues
        )

    @property
    def blocking_errors(
        self,
    ) -> tuple[BaseStructureIssue, ...]:
        """Retorna somente erros impeditivos."""

        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_processing
        )

    @property
    def warnings(
        self,
    ) -> tuple[BaseStructureIssue, ...]:
        """Retorna somente avisos."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == SEVERITY_WARNING
        )

    @property
    def information(
        self,
    ) -> tuple[BaseStructureIssue, ...]:
        """Retorna somente ocorrências informativas."""

        return tuple(
            issue
            for issue in self.issues
            if issue.severity == SEVERITY_INFORMATION
        )


class BaseStructureValidator:
    """Valida as colunas da Base conforme o perfil selecionado."""

    def validate(
        self,
        excel_result: ExcelReadResult,
        profile: RegulatoryVersion,
    ) -> BaseStructureValidationResult:
        """Executa a validação estrutural sem alterar a planilha."""

        sheet = excel_result.get_sheet(SHEET_BASE)
        embedded_references = not all(
            sheet_name in excel_result.sheets
            for sheet_name in OPTIONAL_REFERENCE_SHEETS
        )
        contract = self._contract_for_profile(
            profile,
            embedded_references=embedded_references,
        )

        actual_columns = sheet.headers
        missing_columns = tuple(
            column_name
            for column_name in contract.required_columns
            if column_name not in actual_columns
        )
        extra_columns = tuple(
            column_name
            for column_name in actual_columns
            if column_name not in contract.recognized_columns
        )
        future_columns_present = tuple(
            column_name
            for column_name in BASE_FUTURE_COLUMNS
            if column_name in actual_columns
        )

        issues: list[BaseStructureIssue] = []

        if sheet.row_count == 0:
            issues.append(
                BaseStructureIssue(
                    code="BASE-EST-001",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "A aba Base não possui nenhuma linha de dados."
                    ),
                )
            )

        for column_name in missing_columns:
            issues.append(
                BaseStructureIssue(
                    code="BASE-EST-002",
                    severity=SEVERITY_BLOCKING_ERROR,
                    message=(
                        "Coluna obrigatória ausente para o perfil "
                        f"{profile.code}."
                    ),
                    column_name=column_name,
                    suggested_column_name=column_name,
                )
            )

        issues.extend(
            self._known_alias_issues(
                actual_columns=actual_columns,
            )
        )

        known_alias_columns = frozenset(
            BASE_KNOWN_COLUMN_ALIASES
        )
        unknown_extra_columns = tuple(
            column_name
            for column_name in extra_columns
            if column_name not in known_alias_columns
        )

        if unknown_extra_columns:
            issues.append(
                BaseStructureIssue(
                    code="BASE-AVISO-001",
                    severity=SEVERITY_WARNING,
                    message=(
                        "A aba Base possui colunas adicionais sem "
                        "mapeamento. Elas serão ignoradas nesta etapa."
                    ),
                    details=unknown_extra_columns,
                )
            )

        if (
            profile.code in LEGACY_PROFILE_CODES
            and future_columns_present
        ):
            issues.append(
                BaseStructureIssue(
                    code="BASE-INFO-001",
                    severity=SEVERITY_INFORMATION,
                    message=(
                        "Colunas previstas para 12/2026 estão "
                        "presentes, mas não fazem parte do leiaute "
                        "confirmado desta dataBase."
                    ),
                    details=future_columns_present,
                )
            )

        issues.append(
            BaseStructureIssue(
                code="BASE-INFO-002",
                severity=SEVERITY_INFORMATION,
                message=(
                    "Source.Name foi reconhecida somente como "
                    "metadado e não será enviada ao XML."
                ),
                column_name="Source.Name",
            )
        )

        return BaseStructureValidationResult(
            sheet_name=sheet.name,
            profile_code=profile.code,
            row_count=sheet.row_count,
            actual_columns=actual_columns,
            contract=contract,
            missing_columns=missing_columns,
            extra_columns=extra_columns,
            future_columns_present=future_columns_present,
            issues=tuple(issues),
        )

    @staticmethod
    def _contract_for_profile(
        profile: RegulatoryVersion,
        *,
        embedded_references: bool = False,
    ) -> BaseColumnContract:
        """Monta o contrato sem misturar obrigatoriedade de células."""

        reference_required = (
            BASE_EMBEDDED_REFERENCE_COLUMNS
            if embedded_references
            else ()
        )
        reference_optional = (
            ()
            if embedded_references
            else BASE_EMBEDDED_REFERENCE_COLUMNS
        )

        if profile.code in LEGACY_PROFILE_CODES:
            return BaseColumnContract(
                profile_code=profile.code,
                required_columns=(
                    *BASE_CONFIRMED_REQUIRED_COLUMNS,
                    *reference_required,
                ),
                optional_columns=(
                    *BASE_FUTURE_COLUMNS,
                    *reference_optional,
                ),
                recognized_columns=BASE_ALL_COLUMNS,
            )

        if profile.code in FUTURE_PROFILE_CODES:
            return BaseColumnContract(
                profile_code=profile.code,
                required_columns=(
                    *BASE_CONFIRMED_REQUIRED_COLUMNS,
                    *BASE_FUTURE_COLUMNS,
                    *reference_required,
                ),
                optional_columns=reference_optional,
                recognized_columns=BASE_ALL_COLUMNS,
            )

        raise ValueError(
            "Não existe contrato de colunas da Base para o perfil "
            f"{profile.code!r}."
        )

    @staticmethod
    def _known_alias_issues(
        *,
        actual_columns: tuple[str, ...],
    ) -> list[BaseStructureIssue]:
        """Informa aliases conhecidos sem renomeá-los."""

        issues: list[BaseStructureIssue] = []

        for alias, canonical_name in (
            BASE_KNOWN_COLUMN_ALIASES.items()
        ):
            if alias not in actual_columns:
                continue

            issues.append(
                BaseStructureIssue(
                    code="BASE-EST-003",
                    severity=SEVERITY_WARNING,
                    message=(
                        "Foi encontrada uma grafia conhecida, mas "
                        "ela não será renomeada silenciosamente."
                    ),
                    column_name=alias,
                    suggested_column_name=canonical_name,
                )
            )

        return issues


def validate_base_structure(
    excel_result: ExcelReadResult,
    profile: RegulatoryVersion,
) -> BaseStructureValidationResult:
    """Atalho funcional para o validador padrão."""

    return BaseStructureValidator().validate(
        excel_result,
        profile,
    )
