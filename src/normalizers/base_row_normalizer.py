"""Normalização campo a campo de uma linha da aba ``Base``."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable

from src.config import (
    BASE_ALL_COLUMNS,
    BASE_CREDIT_ACCOUNT_NAME_COLUMN,
    BASE_DEBIT_ACCOUNT_NAME_COLUMN,
    BASE_FUTURE_COLUMNS,
    BASE_SOURCE_SYSTEM_NAME_COLUMN,
)
from src.domain.base_row import (
    BaseRowIssue,
    NormalizedBaseField,
    NormalizedBaseRow,
)
from src.domain.normalization import (
    NormalizationResult,
    absent_result,
    invalid_result,
)
from src.domain.regulatory_version import RegulatoryVersion
from src.normalizers.date_normalizer import normalize_date
from src.normalizers.decimal_normalizer import normalize_decimal
from src.normalizers.domain_normalizer import (
    extract_unconfirmed_domain_code,
    normalize_domain,
)
from src.normalizers.identifier_normalizer import (
    normalize_bacen_id,
    normalize_cosif_account,
    normalize_event_id,
    normalize_internal_account_code,
    normalize_origin_event_code,
    normalize_source_system_code,
)
from src.normalizers.null_normalizer import is_null_candidate
from src.normalizers.reference_table_normalizer import (
    normalize_reference_name,
)
from src.normalizers.text_normalizer import normalize_text
if TYPE_CHECKING:
    from src.readers.excel_reader import RawCell, RawRow


SEVERITY_ERROR = "ERRO"
SEVERITY_WARNING = "AVISO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"

CATEGORY_LEVEL_1_CODES = frozenset(
    str(value)
    for value in range(1, 9)
)
CATEGORY_LEVEL_2_CODES = frozenset(
    {
        "11", "12", "21", "22", "31", "32", "33",
        "41", "42", "43", "44", "45", "51", "61",
        "71", "81", "82", "83", "84", "85", "86",
    }
)
BUSINESS_UNIT_CODES = CATEGORY_LEVEL_1_CODES
LEGACY_ASSESSMENT_CODES = frozenset(
    {"I", "M", "NA"}
)
FUTURE_ASSESSMENT_CODES = frozenset(
    {"I", "IE", "M", "ME", "NA"}
)
LEGACY_CONTINGENCY_CODES = frozenset(
    {"TRI", "TRA", "CIV", "NA"}
)
FUTURE_CONTINGENCY_CODES = frozenset(
    {"TRI", "TRA", "CIV", "OUT", "NA"}
)
RISK_CODES = frozenset({"C", "M", "NA"})
YES_NO_CODES = frozenset({"S", "N"})
PROBABILITY_CODES = frozenset({"PR", "PO", "RE"})
RECOVERY_SOURCE_CODES = frozenset({"S", "O", "NA"})

LEGACY_PROFILE_CODES = frozenset(
    {"DRO_2020_12", "DRO_2025_06"}
)

FORMULA_IDENTIFICATION_FIELDS = frozenset({
    "idEvento",
    "idEventoAgregador",
    "idBacen",
    "codigoEventoOrigem",
    "codSistemaOrigem",
    "contaBalAnaliticoDebito",
    "contaBalAnaliticoCredito",
    "contaCosifDebito",
    "contaCosifCredito",
})
FORMULA_MONETARY_FIELDS = frozenset({
    "totalPerdaEfetiva",
    "totalProvisao",
    "totalRecuperado",
    "valorTotalRisco",
    "valorRisco",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
})
FORMULA_DATE_FIELDS = frozenset({
    "dataDescoberta",
    "dataOcorrencia",
    "dataContabilizacao",
    "dataExclusao",
})
AUDITABLE_DECIMAL_RULES = frozenset({
    "REMOCAO_SIMBOLO_BRL",
    "CONVERSAO_PARENTESES_CONTABEIS",
})


class BaseRowNormalizer:
    """Normaliza as células conhecidas de uma linha."""

    def __init__(
        self,
        profile: RegulatoryVersion,
    ) -> None:
        self.profile = profile
        self.cosif_lengths = (
            frozenset({8})
            if profile.code == "DRO_2020_12"
            else frozenset({8, 10})
        )

        if profile.code in LEGACY_PROFILE_CODES:
            self.assessment_codes = (
                LEGACY_ASSESSMENT_CODES
            )
            self.contingency_codes = (
                LEGACY_CONTINGENCY_CODES
            )
        else:
            self.assessment_codes = (
                FUTURE_ASSESSMENT_CODES
            )
            self.contingency_codes = (
                FUTURE_CONTINGENCY_CODES
            )

    def normalize(
        self,
        row: RawRow,
        *,
        available_columns: tuple[str, ...],
    ) -> NormalizedBaseRow:
        fields: dict[str, NormalizedBaseField] = {}
        issues: list[BaseRowIssue] = []

        for column_name in BASE_ALL_COLUMNS:
            applicable = self._is_applicable(
                column_name
            )

            if column_name not in available_columns:
                result = absent_result(
                    original_value=None,
                    rule_code=(
                        "NORM-COLUNA-OPCIONAL-AUSENTE-001"
                    ),
                    issue_code=(
                        "BASE-COLUNA-AUSENTE-OPCIONAL"
                    ),
                    issue_message=(
                        "Coluna opcional ausente no perfil atual."
                    ),
                )
                fields[column_name] = NormalizedBaseField(
                    column_name=column_name,
                    coordinate=None,
                    applicable=applicable,
                    result=result,
                )
                continue

            cell = row.get_cell(column_name)
            result = self._normalize_cell(
                column_name=column_name,
                cell=cell,
            )

            fields[column_name] = NormalizedBaseField(
                column_name=column_name,
                coordinate=cell.coordinate,
                applicable=applicable,
                result=result,
            )

            if result.is_invalid:
                issues.append(
                    self._issue_from_result(
                        row=row,
                        column_name=column_name,
                        cell=cell,
                        result=result,
                        severity=(
                            SEVERITY_ERROR
                            if applicable
                            else SEVERITY_WARNING
                        ),
                    )
                )

            if (
                column_name in {"idEvento", "idEventoAgregador"}
                and result.is_valid
                and isinstance(result.original_value, str)
                and "-" in result.original_value.strip()
                and result.original_value.strip().replace("-", "")
                == result.serialized_value
            ):
                issues.append(
                    BaseRowIssue(
                        code="BASE-NORM-ID-EVENTO-INFO-001",
                        severity=SEVERITY_INFORMATION,
                        message=(
                            "Separadores permitidos foram removidos do "
                            f"{column_name}."
                        ),
                        row_number=row.row_number,
                        column_name=column_name,
                        coordinate=cell.coordinate,
                        original_value=result.original_value,
                        normalized_value=result.serialized_value,
                        rule_code="NORM-ID-EVENTO-001",
                    )
                )

            if cell.is_formula and result.is_valid:
                issues.append(
                    BaseRowIssue(
                        code="BASE-NORM-FORMULA-AVISO-001",
                        severity=SEVERITY_WARNING,
                        message=(
                            "Fórmula aceita com o último resultado "
                            "calculado e armazenado no arquivo Excel."
                        ),
                        row_number=row.row_number,
                        column_name=column_name,
                        coordinate=cell.coordinate,
                        original_value=cell.formula,
                        normalized_value=result.serialized_value,
                        rule_code="NORM-FORMULA-RESULTADO-001",
                    )
                )

            if (
                result.is_valid
                and result.rule_code in AUDITABLE_DECIMAL_RULES
            ):
                issues.append(
                    BaseRowIssue(
                        code="BASE-NORM-MONETARIO-AVISO-001",
                        severity=SEVERITY_WARNING,
                        message=(
                            "Transformação monetária não trivial "
                            "aplicada conforme a política de entrada."
                        ),
                        row_number=row.row_number,
                        column_name=column_name,
                        coordinate=cell.coordinate,
                        original_value=cell.value,
                        normalized_value=result.serialized_value,
                        rule_code=result.rule_code,
                    )
                )

            if (
                column_name in BASE_FUTURE_COLUMNS
                and not applicable
                and not is_null_candidate(cell.value)
            ):
                issues.append(
                    BaseRowIssue(
                        code="BASE-LINHA-INFO-001",
                        severity=SEVERITY_INFORMATION,
                        message=(
                            "Campo 12/2026 preenchido em perfil "
                            "anterior. O valor não será usado no "
                            "XML deste perfil."
                        ),
                        row_number=row.row_number,
                        column_name=column_name,
                        coordinate=cell.coordinate,
                        original_value=cell.value,
                        normalized_value=(
                            result.serialized_value
                        ),
                        rule_code=result.rule_code,
                    )
                )

            if (
                column_name == "motivoExclusao"
                and applicable
                and result.is_valid
            ):
                issues.append(
                    BaseRowIssue(
                        code="BASE-REGRA-NE-001",
                        severity=SEVERITY_NOT_EXECUTED,
                        message=(
                            "O código foi extraído, mas o domínio "
                            "definitivo de motivoExclusao não foi "
                            "validado por conflito documental."
                        ),
                        row_number=row.row_number,
                        column_name=column_name,
                        coordinate=cell.coordinate,
                        original_value=cell.value,
                        normalized_value=(
                            result.serialized_value
                        ),
                        rule_code=result.rule_code,
                    )
                )

        return NormalizedBaseRow(
            row_number=row.row_number,
            profile_code=self.profile.code,
            fields=MappingProxyType(fields),
            issues=tuple(issues),
        )

    def _normalize_cell(
        self,
        *,
        column_name: str,
        cell: RawCell,
    ) -> NormalizationResult[Any]:
        if cell.is_formula:
            if column_name in FORMULA_IDENTIFICATION_FIELDS:
                return invalid_result(
                    original_value=cell.formula,
                    rule_code="NORM-FORMULA-PROIBIDA-001",
                    issue_code="BASE-NORM-FORMULA-ID-001",
                    issue_message=(
                        "Fórmulas são proibidas em campos de "
                        "identificação."
                    ),
                )

            if column_name not in (
                FORMULA_MONETARY_FIELDS | FORMULA_DATE_FIELDS
            ):
                return invalid_result(
                    original_value=cell.formula,
                    rule_code="NORM-FORMULA-PROIBIDA-001",
                    issue_code="BASE-NORM-FORMULA-CAMPO-001",
                    issue_message=(
                        "Fórmulas não são permitidas neste campo."
                    ),
                )

            if not cell.has_cached_formula_result:
                return invalid_result(
                    original_value=cell.formula,
                    rule_code="NORM-FORMULA-SEM-RESULTADO-001",
                    issue_code="BASE-NORM-FORMULA-SEM-RESULTADO-001",
                    issue_message=(
                        "A célula contém fórmula, mas não possui "
                        "resultado calculado armazenado. Abra a planilha "
                        "no Excel, recalcule e salve antes da conversão."
                    ),
                )

            value = cell.cached_value
        else:
            value = cell.value

        normalizers: dict[
            str,
            Callable[[], NormalizationResult[Any]],
        ] = {
            "Source.Name": lambda: normalize_text(
                value,
                rule_code="NORM-METADADO-ORIGEM-001",
                collapse_whitespace=False,
            ),
            "idEvento": lambda: normalize_event_id(value),
            "categoriaNivel1": lambda: normalize_domain(
                value,
                allowed_codes=CATEGORY_LEVEL_1_CODES,
            ),
            "categoriaNivel2": lambda: normalize_domain(
                value,
                allowed_codes=CATEGORY_LEVEL_2_CODES,
            ),
            "tipoAvaliacao": lambda: normalize_domain(
                value,
                allowed_codes=self.assessment_codes,
            ),
            "unidadeNegocio": lambda: normalize_domain(
                value,
                allowed_codes=BUSINESS_UNIT_CODES,
            ),
            "dataDescoberta": lambda: normalize_date(
                value,
                excel_number_format=cell.number_format,
            ),
            "dataOcorrencia": lambda: normalize_date(
                value,
                excel_number_format=cell.number_format,
            ),
            "totalPerdaEfetiva": lambda: normalize_decimal(
                value
            ),
            "totalProvisao": lambda: normalize_decimal(value),
            "totalRecuperado": lambda: normalize_decimal(
                value
            ),
            "valorTotalRisco": lambda: normalize_decimal(
                value
            ),
            "naturezaContingencia": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=self.contingency_codes,
                )
            ),
            "codSistemaOrigem": (
                lambda: normalize_source_system_code(value)
            ),
            BASE_SOURCE_SYSTEM_NAME_COLUMN: (
                lambda: normalize_reference_name(
                    value,
                    field_label=(
                        BASE_SOURCE_SYSTEM_NAME_COLUMN
                    ),
                )
            ),
            "codigoEventoOrigem": (
                lambda: normalize_origin_event_code(value)
            ),
            "descricaoEvento": lambda: normalize_text(
                value,
                rule_code="NORM-DESCRICAO-EVENTO-001",
                max_length=200,
                collapse_whitespace=True,
            ),
            "riscoAssociado": lambda: normalize_domain(
                value,
                allowed_codes=RISK_CODES,
            ),
            "ligacaoRiscoSocioambiental": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=YES_NO_CODES,
                )
            ),
            "ligadoRiscoCibernetico": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=YES_NO_CODES,
                )
            ),
            "negocioDescontinuado": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=YES_NO_CODES,
                )
            ),
            "idBacen": lambda: normalize_bacen_id(value),
            "probabilidadePerda": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=PROBABILITY_CODES,
                )
            ),
            "valorRisco": lambda: normalize_decimal(value),
            "dataContabilizacao": (
                lambda: normalize_date(
                    value,
                    excel_number_format=cell.number_format,
                )
            ),
            "contaBalAnaliticoDebito": (
                lambda: normalize_internal_account_code(
                    value
                )
            ),
            "contaBalAnaliticoCredito": (
                lambda: normalize_internal_account_code(
                    value
                )
            ),
            BASE_DEBIT_ACCOUNT_NAME_COLUMN: (
                lambda: normalize_reference_name(
                    value,
                    field_label=(
                        BASE_DEBIT_ACCOUNT_NAME_COLUMN
                    ),
                )
            ),
            BASE_CREDIT_ACCOUNT_NAME_COLUMN: (
                lambda: normalize_reference_name(
                    value,
                    field_label=(
                        BASE_CREDIT_ACCOUNT_NAME_COLUMN
                    ),
                )
            ),
            "contaCosifDebito": (
                lambda: normalize_cosif_account(
                    value,
                    allowed_lengths=self.cosif_lengths,
                )
            ),
            "contaCosifCredito": (
                lambda: normalize_cosif_account(
                    value,
                    allowed_lengths=self.cosif_lengths,
                )
            ),
            "valorPerdaEfetiva": (
                lambda: normalize_decimal(value)
            ),
            "valorProvisao": (
                lambda: normalize_decimal(value)
            ),
            "valorRecuperacao": (
                lambda: normalize_decimal(value)
            ),
            "fonteRecuperacao": (
                lambda: normalize_domain(
                    value,
                    allowed_codes=RECOVERY_SOURCE_CODES,
                )
            ),
            "idEventoAgregador": (
                lambda: normalize_event_id(value)
            ),
            "dataExclusao": lambda: normalize_date(
                value,
                excel_number_format=cell.number_format,
            ),
            "motivoExclusao": (
                lambda: extract_unconfirmed_domain_code(
                    value
                )
            ),
        }

        normalizer = normalizers.get(column_name)

        if normalizer is None:
            return invalid_result(
                original_value=value,
                rule_code="NORM-CAMPO-NAO-MAPEADO-001",
                issue_code="BASE-NORM-MAPA-001",
                issue_message=(
                    "Não existe normalizador para a coluna."
                ),
            )

        result = normalizer()
        if cell.is_formula and result.is_absent:
            return invalid_result(
                original_value=cell.formula,
                rule_code="NORM-FORMULA-RESULTADO-INVALIDO-001",
                issue_code="BASE-NORM-FORMULA-RESULTADO-INVALIDO-001",
                issue_message=(
                    "A fórmula possui resultado armazenado vazio ou "
                    "incompatível com o campo."
                ),
            )
        return result

    def _is_applicable(
        self,
        column_name: str,
    ) -> bool:
        return not (
            column_name in BASE_FUTURE_COLUMNS
            and self.profile.code in LEGACY_PROFILE_CODES
        )

    @staticmethod
    def _issue_from_result(
        *,
        row: RawRow,
        column_name: str,
        cell: RawCell,
        result: NormalizationResult[Any],
        severity: str,
    ) -> BaseRowIssue:
        return BaseRowIssue(
            code=result.issue_code or "BASE-NORM-001",
            severity=severity,
            message=(
                result.issue_message
                or "Falha de normalização."
            ),
            row_number=row.row_number,
            column_name=column_name,
            coordinate=cell.coordinate,
            original_value=cell.value,
            normalized_value=(
                cell.cached_value
                if cell.is_formula and result.is_invalid
                else result.serialized_value
            ),
            rule_code=result.rule_code,
        )
