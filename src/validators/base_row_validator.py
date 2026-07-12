"""Validação local de obrigatoriedades e relações da aba ``Base``.

Esta etapa executa somente regras que podem ser decididas com os campos de uma
única linha. Regras que dependem do conjunto completo de linhas do mesmo
``idEvento`` são registradas como ``REGRA NÃO EXECUTADA`` e serão tratadas na
etapa de agrupamento por evento.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable, Iterable

from src.domain.base_row import (
    BaseRowsNormalizationResult,
    NormalizedBaseRow,
)
from src.domain.base_row_validation import (
    BaseRowKind,
    BaseRowsValidationResult,
    BaseRowValidationResult,
    RowRuleResult,
    RuleExecutionStatus,
)
from src.domain.normalization import NormalizationStatus
from src.domain.regulatory_version import RegulatoryVersion


SEVERITY_BLOCKING_ERROR = "ERRO IMPEDITIVO"
SEVERITY_ERROR = "ERRO"
SEVERITY_INFORMATION = "INFORMAÇÃO"
SEVERITY_NOT_EXECUTED = "REGRA NÃO EXECUTADA"

CIRCULAR_START_DATE = date(2021, 1, 1)
INDIVIDUAL_THRESHOLD = Decimal("1000.00")
DESCRIPTION_THRESHOLD = Decimal("1000000.00")
TOTAL_RISK_MINIMUM = Decimal("10000000.00")

EVENT_REQUIRED_FIELDS = (
    "idEvento",
    "categoriaNivel1",
    "tipoAvaliacao",
    "unidadeNegocio",
    "dataOcorrencia",
    "totalPerdaEfetiva",
    "totalRecuperado",
    "naturezaContingencia",
    "codSistemaOrigem",
    "codigoEventoOrigem",
    "idBacen",
)

EXCLUDED_REQUIRED_FIELDS = (
    "idEvento",
    "dataExclusao",
    "motivoExclusao",
)

ACCOUNTING_FIELDS = (
    "dataContabilizacao",
    "contaBalAnaliticoDebito",
    "contaBalAnaliticoCredito",
    "contaCosifDebito",
    "contaCosifCredito",
    "valorPerdaEfetiva",
    "valorProvisao",
    "valorRecuperacao",
    "fonteRecuperacao",
)

ACCOUNT_FIELDS = (
    "contaBalAnaliticoDebito",
    "contaBalAnaliticoCredito",
    "contaCosifDebito",
    "contaCosifCredito",
)

CONTINGENCY_ASSESSMENT_CODES = frozenset(
    {"I", "M", "IE", "ME"}
)
MASSIFIED_ASSESSMENT_CODES = frozenset({"M", "ME"})
INDIVIDUAL_ASSESSMENT_CODES = frozenset({"I", "IE"})
CONTINGENCY_NATURE_CODES = frozenset(
    {"TRI", "TRA", "CIV", "OUT"}
)


class BaseRowBusinessValidator:
    """Executa regras locais sobre as linhas já normalizadas."""

    def validate(
        self,
        normalization: BaseRowsNormalizationResult,
        profile: RegulatoryVersion,
    ) -> BaseRowsValidationResult:
        row_results = tuple(
            self._validate_row(row, profile)
            for row in normalization.rows
        )
        all_results = tuple(
            result
            for row_result in row_results
            for result in row_result.rule_results
        )

        return BaseRowsValidationResult(
            profile_code=profile.code,
            rows=row_results,
            rule_results=all_results,
        )

    def _validate_row(
        self,
        row: NormalizedBaseRow,
        profile: RegulatoryVersion,
    ) -> BaseRowValidationResult:
        row_kind = self._classify_row(row, profile)

        if row_kind == BaseRowKind.EXCLUDED:
            rule_functions: tuple[
                Callable[[], RowRuleResult], ...
            ] = (
                lambda: self._validate_required_fields(
                    row,
                    row_kind,
                    EXCLUDED_REQUIRED_FIELDS,
                ),
                lambda: self._validate_exclusion_pair(
                    row,
                    row_kind,
                ),
                lambda: self._defer_exclusion_reason_domain(
                    row,
                    row_kind,
                ),
            )
        else:
            rule_functions = (
                lambda: self._validate_required_fields(
                    row,
                    row_kind,
                    EVENT_REQUIRED_FIELDS,
                ),
                lambda: self._validate_category_compatibility(
                    row,
                    row_kind,
                ),
                lambda: self._validate_discovery_required(
                    row,
                    row_kind,
                ),
                lambda: self._validate_event_date_order(
                    row,
                    row_kind,
                ),
                lambda: self._validate_category_level_2_required(
                    row,
                    row_kind,
                ),
                lambda: self._validate_individual_threshold(
                    row,
                    row_kind,
                ),
                lambda: self._validate_recovery_total_limit(
                    row,
                    row_kind,
                ),
                lambda: self._validate_risk_nature(
                    row,
                    row_kind,
                ),
                lambda: self._validate_total_risk_minimum(
                    row,
                    row_kind,
                ),
                lambda: self._validate_description_required(
                    row,
                    row_kind,
                ),
                lambda: self._defer_pre_critique_description_rule(
                    row,
                    row_kind,
                ),
                lambda: self._validate_risk_associated_required(
                    row,
                    row_kind,
                ),
                lambda: self._validate_rsac_required(
                    row,
                    row_kind,
                ),
                lambda: self._validate_cyber_required(
                    row,
                    row_kind,
                ),
                lambda: self._validate_assessment_nature_relation(
                    row,
                    row_kind,
                ),
                lambda: self._validate_provision_for_na(
                    row,
                    row_kind,
                ),
                lambda: self._validate_provision_for_contingency(
                    row,
                    row_kind,
                ),
                lambda: self._validate_probability_pair(
                    row,
                    row_kind,
                ),
                lambda: self._validate_no_probability_massified(
                    row,
                    row_kind,
                ),
                lambda: self._defer_probability_required(
                    row,
                    row_kind,
                ),
                lambda: self._defer_risk_sum_positive(
                    row,
                    row_kind,
                ),
                lambda: self._validate_accounting_required_fields(
                    row,
                    row_kind,
                ),
                lambda: self._validate_accounting_date_order(
                    row,
                    row_kind,
                ),
                lambda: self._validate_event_signs(
                    row,
                    row_kind,
                ),
                lambda: self._validate_accounting_loss_sign(
                    row,
                    row_kind,
                ),
                lambda: self._validate_recovery_sign(
                    row,
                    row_kind,
                ),
                lambda: self._validate_recovery_source(
                    row,
                    row_kind,
                ),
                lambda: self._validate_debit_internal_to_cosif(
                    row,
                    row_kind,
                ),
                lambda: self._validate_credit_internal_to_cosif(
                    row,
                    row_kind,
                ),
                lambda: self._validate_debit_cosif_to_internal(
                    row,
                    row_kind,
                ),
                lambda: self._validate_credit_cosif_to_internal(
                    row,
                    row_kind,
                ),
                lambda: self._validate_account_fields_for_movement(
                    row,
                    row_kind,
                ),
                lambda: self._defer_risk_only_accounting_rule(
                    row,
                    row_kind,
                ),
                lambda: self._validate_recovery_exclusivity(
                    row,
                    row_kind,
                    profile,
                ),
            )

        results = tuple(function() for function in rule_functions)

        return BaseRowValidationResult(
            row_number=row.row_number,
            id_evento=row.id_evento,
            row_kind=row_kind,
            normalization_valid=row.is_valid,
            rule_results=results,
        )

    @staticmethod
    def _classify_row(
        row: NormalizedBaseRow,
        profile: RegulatoryVersion,
    ) -> BaseRowKind:
        if profile.code == "DRO_2026_12_PRESUMIDA":
            if (
                not row.get_field("dataExclusao").is_absent
                or not row.get_field("motivoExclusao").is_absent
            ):
                return BaseRowKind.EXCLUDED

        return BaseRowKind.INDIVIDUALIZED

    def _validate_required_fields(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        required_fields: tuple[str, ...],
    ) -> RowRuleResult:
        invalid_dependencies = self._invalid_fields(
            row,
            required_fields,
        )
        if invalid_dependencies:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-XSD-REQ-001",
                description=(
                    "Verificar os campos obrigatórios do tipo de linha."
                ),
                source="XSD e instruções",
                columns=required_fields,
                message=(
                    "A regra não foi executada porque há campos "
                    "obrigatórios com falha de normalização: "
                    f"{', '.join(invalid_dependencies)}."
                ),
            )

        missing = tuple(
            field_name
            for field_name in required_fields
            if row.get_field(field_name).is_absent
        )

        if missing:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-XSD-REQ-001",
                description=(
                    "Verificar os campos obrigatórios do tipo de linha."
                ),
                source="XSD e instruções",
                columns=missing,
                message=(
                    "Campos obrigatórios ausentes: "
                    f"{', '.join(missing)}."
                ),
                suggestion=(
                    "Preencher os campos com os dados reais; não usar "
                    "valores fictícios para satisfazer o leiaute."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-XSD-REQ-001",
            description=(
                "Verificar os campos obrigatórios do tipo de linha."
            ),
            source="XSD e instruções",
            columns=required_fields,
            message="Todos os campos obrigatórios locais estão presentes.",
        )

    def _validate_category_compatibility(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("categoriaNivel1", "categoriaNivel2")
        dependency = self._dependency_result(
            row,
            row_kind,
            code="BASE-REL-CAT-001",
            description=(
                "Validar compatibilidade entre categoriaNivel1 e "
                "categoriaNivel2."
            ),
            source="Instruções, Anexos I e II",
            columns=fields,
        )
        if dependency is not None:
            return dependency

        if row.get_field("categoriaNivel2").is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-REL-CAT-001",
                description=(
                    "Validar compatibilidade entre categoriaNivel1 e "
                    "categoriaNivel2."
                ),
                source="Instruções, Anexos I e II",
                columns=fields,
                message="categoriaNivel2 não foi informada.",
            )

        level_1 = str(row.get_value("categoriaNivel1"))
        level_2 = str(row.get_value("categoriaNivel2"))

        if not level_2.startswith(level_1):
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-REL-CAT-001",
                description=(
                    "Validar compatibilidade entre categoriaNivel1 e "
                    "categoriaNivel2."
                ),
                source="Instruções, Anexos I e II",
                columns=fields,
                message=(
                    f"categoriaNivel2={level_2} não pertence à "
                    f"categoriaNivel1={level_1}."
                ),
                suggestion=(
                    "Revisar a classificação sem alterar códigos "
                    "automaticamente."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-REL-CAT-001",
            description=(
                "Validar compatibilidade entre categoriaNivel1 e "
                "categoriaNivel2."
            ),
            source="Instruções, Anexos I e II",
            columns=fields,
            message="As categorias de nível 1 e 2 são compatíveis.",
        )

    def _validate_discovery_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._required_after_occurrence_date(
            row=row,
            row_kind=row_kind,
            code="DRO001202",
            field_name="dataDescoberta",
            description=(
                "Exigir dataDescoberta para ocorrências a partir de "
                "01/01/2021."
            ),
        )

    def _validate_category_level_2_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._required_after_occurrence_date(
            row=row,
            row_kind=row_kind,
            code="DRO001212",
            field_name="categoriaNivel2",
            description=(
                "Exigir categoriaNivel2 para ocorrências a partir de "
                "01/01/2021."
            ),
        )

    def _validate_risk_associated_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._required_after_occurrence_date(
            row=row,
            row_kind=row_kind,
            code="DRO001251",
            field_name="riscoAssociado",
            description=(
                "Exigir riscoAssociado para ocorrências a partir de "
                "01/01/2021."
            ),
        )

    def _validate_rsac_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._required_after_occurrence_date(
            row=row,
            row_kind=row_kind,
            code="DRO001252",
            field_name="ligacaoRiscoSocioambiental",
            description=(
                "Exigir a indicação de risco socioambiental para "
                "ocorrências a partir de 01/01/2021."
            ),
        )

    def _validate_cyber_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._required_after_occurrence_date(
            row=row,
            row_kind=row_kind,
            code="DRO001253",
            field_name="ligadoRiscoCibernetico",
            description=(
                "Exigir a indicação de risco cibernético para "
                "ocorrências a partir de 01/01/2021."
            ),
        )

    def _required_after_occurrence_date(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        field_name: str,
        description: str,
    ) -> RowRuleResult:
        fields = ("dataOcorrencia", field_name)
        dependency = self._dependency_result(
            row,
            row_kind,
            code=code,
            description=description,
            source="Crítica de pré-processamento",
            columns=fields,
            required_valid_fields=("dataOcorrencia",),
        )
        if dependency is not None:
            return dependency

        occurrence = row.get_value("dataOcorrencia")
        assert isinstance(occurrence, date)

        if occurrence < CIRCULAR_START_DATE:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    "A data de ocorrência é anterior a 01/01/2021."
                ),
            )

        field = row.get_field(field_name)
        if field.is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    f"{field_name} possui falha de normalização."
                ),
            )

        if field.is_absent:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=(field_name,),
                message=(
                    f"{field_name} é obrigatório para esta data de "
                    "ocorrência."
                ),
                suggestion=f"Informar {field_name} com o dado real.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source="Crítica de pré-processamento",
            columns=fields,
            message=f"{field_name} foi informado.",
        )

    def _validate_event_date_order(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("dataOcorrencia", "dataDescoberta")
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001201",
            description=(
                "Verificar se dataOcorrencia é menor ou igual a "
                "dataDescoberta."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            required_valid_fields=("dataOcorrencia",),
        )
        if dependency is not None:
            return dependency

        if row.get_field("dataDescoberta").is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001201",
                description=(
                    "Verificar se dataOcorrencia é menor ou igual a "
                    "dataDescoberta."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="dataDescoberta não foi informada.",
            )

        if row.get_field("dataDescoberta").is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001201",
                description=(
                    "Verificar se dataOcorrencia é menor ou igual a "
                    "dataDescoberta."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="dataDescoberta possui falha de normalização.",
            )

        occurrence = row.get_value("dataOcorrencia")
        discovery = row.get_value("dataDescoberta")
        assert isinstance(occurrence, date)
        assert isinstance(discovery, date)

        if occurrence > discovery:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001201",
                description=(
                    "Verificar se dataOcorrencia é menor ou igual a "
                    "dataDescoberta."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    "dataOcorrencia é posterior a dataDescoberta."
                ),
                suggestion="Revisar as datas informadas para o evento.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001201",
            description=(
                "Verificar se dataOcorrencia é menor ou igual a "
                "dataDescoberta."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="A ordem das datas do evento é válida.",
        )

    def _validate_individual_threshold(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("totalPerdaEfetiva", "totalProvisao")
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001231",
            description=(
                "Verificar o limite mínimo de R$ 1.000,00 para evento "
                "individualizado."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            required_valid_fields=("totalPerdaEfetiva",),
        )
        if dependency is not None:
            return dependency

        loss = self._decimal_or_zero(row, "totalPerdaEfetiva")
        provision = self._decimal_or_zero(row, "totalProvisao")
        total = loss + provision

        if total < INDIVIDUAL_THRESHOLD:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001231",
                description=(
                    "Verificar o limite mínimo de R$ 1.000,00 para evento "
                    "individualizado."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=fields,
                message=(
                    f"A soma de perda e provisão é {total:.2f}. O destino "
                    "será decidido após agrupar todas as linhas do evento "
                    "e validar também o risco não coberto."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001231",
            description=(
                "Verificar o limite mínimo de R$ 1.000,00 para evento "
                "individualizado."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            message="O limite mínimo de individualização foi atendido.",
        )

    def _validate_recovery_total_limit(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "totalRecuperado",
            "totalPerdaEfetiva",
            "totalProvisao",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001232",
            description=(
                "Verificar se o módulo do total recuperado não supera "
                "perda e provisão."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            required_valid_fields=(
                "totalRecuperado",
                "totalPerdaEfetiva",
            ),
        )
        if dependency is not None:
            return dependency

        recovered = abs(
            self._decimal_or_zero(row, "totalRecuperado")
        )
        limit = (
            abs(self._decimal_or_zero(row, "totalPerdaEfetiva"))
            + abs(self._decimal_or_zero(row, "totalProvisao"))
        )

        if recovered > limit:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001232",
                description=(
                    "Verificar se o módulo do total recuperado não supera "
                    "perda e provisão."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    f"O módulo do total recuperado ({recovered:.2f}) "
                    f"supera o limite calculado ({limit:.2f})."
                ),
                suggestion="Revisar os totais informados.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001232",
            description=(
                "Verificar se o módulo do total recuperado não supera "
                "perda e provisão."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="O total recuperado está dentro do limite.",
        )

    def _validate_risk_nature(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("valorTotalRisco", "naturezaContingencia")
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001233",
            description=(
                "Exigir natureza de contingência quando valorTotalRisco "
                "for informado."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
        )
        if dependency is not None:
            return dependency

        risk_field = row.get_field("valorTotalRisco")
        if risk_field.is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001233",
                description=(
                    "Exigir natureza de contingência quando "
                    "valorTotalRisco for informado."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="valorTotalRisco não foi informado.",
            )

        nature = row.get_value("naturezaContingencia")
        if nature not in CONTINGENCY_NATURE_CODES:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001233",
                description=(
                    "Exigir natureza de contingência quando "
                    "valorTotalRisco for informado."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    "valorTotalRisco foi informado, mas a natureza da "
                    "contingência está ausente ou como NA."
                ),
                suggestion=(
                    "Informar a natureza real da contingência."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001233",
            description=(
                "Exigir natureza de contingência quando valorTotalRisco "
                "for informado."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="A natureza da contingência foi informada.",
        )

    def _validate_total_risk_minimum(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        field_name = "valorTotalRisco"
        dependency = self._dependency_result(
            row,
            row_kind,
            code="BASE-RISCO-001",
            description=(
                "Verificar o valor mínimo de R$ 10.000.000,00 para "
                "valorTotalRisco informado."
            ),
            source="Instruções de preenchimento",
            columns=(field_name,),
        )
        if dependency is not None:
            return dependency

        field = row.get_field(field_name)
        if field.is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-RISCO-001",
                description=(
                    "Verificar o valor mínimo de R$ 10.000.000,00 para "
                    "valorTotalRisco informado."
                ),
                source="Instruções de preenchimento",
                columns=(field_name,),
                message="valorTotalRisco não foi informado.",
            )

        value = self._decimal_or_zero(row, field_name)
        if value < TOTAL_RISK_MINIMUM:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-RISCO-001",
                description=(
                    "Verificar o valor mínimo de R$ 10.000.000,00 para "
                    "valorTotalRisco informado."
                ),
                source="Instruções de preenchimento",
                columns=(field_name,),
                message=(
                    f"valorTotalRisco={value:.2f} está abaixo do limite "
                    "mínimo para informação individual."
                ),
                suggestion=(
                    "Revisar o valor ou a necessidade de informar o campo."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-RISCO-001",
            description=(
                "Verificar o valor mínimo de R$ 10.000.000,00 para "
                "valorTotalRisco informado."
            ),
            source="Instruções de preenchimento",
            columns=(field_name,),
            message="O valor total em risco atende ao limite mínimo.",
        )

    def _validate_description_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "dataOcorrencia",
            "totalPerdaEfetiva",
            "totalProvisao",
            "descricaoEvento",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="BASE-OBR-DESC-001",
            description=(
                "Exigir descricaoEvento quando perdas e provisões "
                "atingirem R$ 1.000.000,00."
            ),
            source="Instruções de preenchimento",
            columns=fields,
            required_valid_fields=(
                "dataOcorrencia",
                "totalPerdaEfetiva",
            ),
        )
        if dependency is not None:
            return dependency

        occurrence = row.get_value("dataOcorrencia")
        assert isinstance(occurrence, date)

        total = (
            self._decimal_or_zero(row, "totalPerdaEfetiva")
            + self._decimal_or_zero(row, "totalProvisao")
        )

        if (
            occurrence < CIRCULAR_START_DATE
            or total < DESCRIPTION_THRESHOLD
        ):
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-OBR-DESC-001",
                description=(
                    "Exigir descricaoEvento quando perdas e provisões "
                    "atingirem R$ 1.000.000,00."
                ),
                source="Instruções de preenchimento",
                columns=fields,
                message=(
                    "A data ou o valor não alcança a condição de "
                    "obrigatoriedade."
                ),
            )

        description_field = row.get_field("descricaoEvento")
        if description_field.is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-OBR-DESC-001",
                description=(
                    "Exigir descricaoEvento quando perdas e provisões "
                    "atingirem R$ 1.000.000,00."
                ),
                source="Instruções de preenchimento",
                columns=fields,
                message="descricaoEvento possui falha de normalização.",
            )

        if description_field.is_absent:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-OBR-DESC-001",
                description=(
                    "Exigir descricaoEvento quando perdas e provisões "
                    "atingirem R$ 1.000.000,00."
                ),
                source="Instruções de preenchimento",
                columns=("descricaoEvento",),
                message=(
                    "descricaoEvento é obrigatório porque a soma de "
                    f"perdas e provisões é {total:.2f}."
                ),
                suggestion="Descrever o evento sem exceder 200 caracteres.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-OBR-DESC-001",
            description=(
                "Exigir descricaoEvento quando perdas e provisões "
                "atingirem R$ 1.000.000,00."
            ),
            source="Instruções de preenchimento",
            columns=fields,
            message="descricaoEvento foi informado quando exigido.",
        )

    def _defer_pre_critique_description_rule(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code="DRO001241",
            description=(
                "Exigir descricaoEvento conforme o limiar descrito na "
                "crítica de pré-processamento."
            ),
            source="Crítica de pré-processamento",
            columns=(
                "dataOcorrencia",
                "totalPerdaEfetiva",
                "valorTotalRisco",
                "descricaoEvento",
            ),
            message=(
                "Não executada por conflito documental CONF-022. As "
                "instruções usam perda + provisão, enquanto a crítica usa "
                "perda + valorTotalRisco."
            ),
        )

    def _validate_assessment_nature_relation(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("tipoAvaliacao", "naturezaContingencia")
        dependency = self._dependency_result(
            row,
            row_kind,
            code="BASE-REL-CONT-001",
            description=(
                "Validar coerência entre tipoAvaliacao e "
                "naturezaContingencia."
            ),
            source="Instruções de preenchimento",
            columns=fields,
            required_valid_fields=fields,
        )
        if dependency is not None:
            return dependency

        assessment = row.get_value("tipoAvaliacao")
        nature = row.get_value("naturezaContingencia")

        coherent = (
            assessment in CONTINGENCY_ASSESSMENT_CODES
            and nature in CONTINGENCY_NATURE_CODES
        ) or (
            assessment == "NA"
            and nature == "NA"
        )

        if not coherent:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-REL-CONT-001",
                description=(
                    "Validar coerência entre tipoAvaliacao e "
                    "naturezaContingencia."
                ),
                source="Instruções de preenchimento",
                columns=fields,
                message=(
                    f"Combinação incompatível: tipoAvaliacao={assessment} "
                    f"e naturezaContingencia={nature}."
                ),
                suggestion=(
                    "Usar I/M/IE/ME somente para contingências e NA quando "
                    "a classificação não se aplicar."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-REL-CONT-001",
            description=(
                "Validar coerência entre tipoAvaliacao e "
                "naturezaContingencia."
            ),
            source="Instruções de preenchimento",
            columns=fields,
            message="Tipo de avaliação e natureza são coerentes.",
        )

    def _validate_provision_for_na(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "tipoAvaliacao",
            "totalProvisao",
            "valorProvisao",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001301",
            description=(
                "Não permitir provisão diferente de zero para "
                "tipoAvaliacao=NA."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            required_valid_fields=("tipoAvaliacao",),
        )
        if dependency is not None:
            return dependency

        if row.get_value("tipoAvaliacao") != "NA":
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001301",
                description=(
                    "Não permitir provisão diferente de zero para "
                    "tipoAvaliacao=NA."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=fields,
                message="tipoAvaliacao não é NA.",
            )

        invalid = self._invalid_fields(
            row,
            ("totalProvisao", "valorProvisao"),
        )
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001301",
                description=(
                    "Não permitir provisão diferente de zero para "
                    "tipoAvaliacao=NA."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=fields,
                message=(
                    "Campos de provisão inválidos: "
                    f"{', '.join(invalid)}."
                ),
            )

        non_zero = tuple(
            field_name
            for field_name in ("totalProvisao", "valorProvisao")
            if self._decimal_or_zero(row, field_name) != 0
        )

        if non_zero:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001301",
                description=(
                    "Não permitir provisão diferente de zero para "
                    "tipoAvaliacao=NA."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=non_zero,
                message=(
                    "Foram informados valores de provisão diferentes de "
                    "zero para tipoAvaliacao=NA."
                ),
                suggestion="Revisar o tipo de avaliação ou os valores.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001301",
            description=(
                "Não permitir provisão diferente de zero para "
                "tipoAvaliacao=NA."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            message="Não há provisão diferente de zero para avaliação NA.",
        )

    def _validate_provision_for_contingency(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "tipoAvaliacao",
            "totalProvisao",
            "valorProvisao",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001302",
            description=(
                "Exigir informação de provisão para avaliação de "
                "contingência."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            required_valid_fields=("tipoAvaliacao",),
        )
        if dependency is not None:
            return dependency

        if row.get_value("tipoAvaliacao") not in CONTINGENCY_ASSESSMENT_CODES:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001302",
                description=(
                    "Exigir informação de provisão para avaliação de "
                    "contingência."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="A linha não representa avaliação de contingência.",
            )

        provision_fields = (
            row.get_field("totalProvisao"),
            row.get_field("valorProvisao"),
        )

        if any(field.is_invalid for field in provision_fields):
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001302",
                description=(
                    "Exigir informação de provisão para avaliação de "
                    "contingência."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="Há campo de provisão com falha de normalização.",
            )

        if all(field.is_absent for field in provision_fields):
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001302",
                description=(
                    "Exigir informação de provisão para avaliação de "
                    "contingência."
                ),
                source="Crítica de pré-processamento",
                columns=("totalProvisao", "valorProvisao"),
                message=(
                    "Nenhum campo de provisão foi informado para a "
                    "contingência."
                ),
                suggestion=(
                    "Informar os valores reais, inclusive zero quando a "
                    "instrução determinar."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001302",
            description=(
                "Exigir informação de provisão para avaliação de "
                "contingência."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="Há informação de provisão para a contingência.",
        )

    def _validate_probability_pair(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("probabilidadePerda", "valorRisco")
        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-PROB-001",
                description=(
                    "Exigir probabilidadePerda e valorRisco no mesmo "
                    "registro."
                ),
                source="XSD e instruções",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        probability_absent = row.get_field(
            "probabilidadePerda"
        ).is_absent
        risk_absent = row.get_field("valorRisco").is_absent

        if probability_absent and risk_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-PROB-001",
                description=(
                    "Exigir probabilidadePerda e valorRisco no mesmo "
                    "registro."
                ),
                source="XSD e instruções",
                columns=fields,
                message="A linha não contém registro de probabilidade.",
            )

        if probability_absent != risk_absent:
            missing = (
                "probabilidadePerda"
                if probability_absent
                else "valorRisco"
            )
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-PROB-001",
                description=(
                    "Exigir probabilidadePerda e valorRisco no mesmo "
                    "registro."
                ),
                source="XSD e instruções",
                columns=fields,
                message=f"O campo {missing} está ausente.",
                suggestion=(
                    "Preencher o par completo ou remover o registro de "
                    "probabilidade."
                ),
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-PROB-001",
            description=(
                "Exigir probabilidadePerda e valorRisco no mesmo registro."
            ),
            source="XSD e instruções",
            columns=fields,
            message="O registro de probabilidade está completo.",
        )

    def _validate_no_probability_massified(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "tipoAvaliacao",
            "probabilidadePerda",
            "valorRisco",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001313",
            description=(
                "Proibir probabilidade de perda para avaliação massificada."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            required_valid_fields=("tipoAvaliacao",),
        )
        if dependency is not None:
            return dependency

        if row.get_value("tipoAvaliacao") not in MASSIFIED_ASSESSMENT_CODES:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001313",
                description=(
                    "Proibir probabilidade de perda para avaliação "
                    "massificada."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=fields,
                message="A avaliação não é massificada.",
            )

        informed = tuple(
            field_name
            for field_name in ("probabilidadePerda", "valorRisco")
            if not row.get_field(field_name).is_absent
        )

        if informed:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001313",
                description=(
                    "Proibir probabilidade de perda para avaliação "
                    "massificada."
                ),
                source="Crítica de pré-processamento e instruções",
                columns=informed,
                message=(
                    "Foram informados dados de probabilidade para avaliação "
                    "massificada."
                ),
                suggestion="Remover o detalhamento indevido ou revisar o tipo.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001313",
            description=(
                "Proibir probabilidade de perda para avaliação massificada."
            ),
            source="Crítica de pré-processamento e instruções",
            columns=fields,
            message="Não há probabilidade para avaliação massificada.",
        )

    def _defer_probability_required(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code="DRO001312",
            description=(
                "Exigir ao menos uma probabilidade para evento individual."
            ),
            source="Crítica de pré-processamento",
            columns=(
                "dataOcorrencia",
                "tipoAvaliacao",
                "probabilidadePerda",
            ),
            message=(
                "Depende do conjunto completo de linhas do mesmo idEvento."
            ),
        )

    def _defer_risk_sum_positive(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code="DRO001314",
            description=(
                "Verificar se a soma dos valores de risco do evento é "
                "maior que zero."
            ),
            source="Crítica de pré-processamento",
            columns=(
                "dataOcorrencia",
                "tipoAvaliacao",
                "naturezaContingencia",
                "probabilidadePerda",
                "valorRisco",
            ),
            message=(
                "Depende da soma de todas as probabilidades do idEvento."
            ),
        )

    def _validate_accounting_required_fields(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        if not self._has_accounting_record(row):
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-REQ-001",
                description=(
                    "Exigir dataContabilizacao e valorPerdaEfetiva quando "
                    "houver registro contábil."
                ),
                source="XSD e instruções",
                columns=ACCOUNTING_FIELDS,
                message="A linha não contém registro contábil.",
            )

        required = ("dataContabilizacao", "valorPerdaEfetiva")
        invalid = self._invalid_fields(row, required)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-REQ-001",
                description=(
                    "Exigir dataContabilizacao e valorPerdaEfetiva quando "
                    "houver registro contábil."
                ),
                source="XSD e instruções",
                columns=required,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        missing = tuple(
            field_name
            for field_name in required
            if row.get_field(field_name).is_absent
        )
        if missing:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-REQ-001",
                description=(
                    "Exigir dataContabilizacao e valorPerdaEfetiva quando "
                    "houver registro contábil."
                ),
                source="XSD e instruções",
                columns=missing,
                message=(
                    "Registro contábil incompleto. Campos ausentes: "
                    f"{', '.join(missing)}."
                ),
                suggestion="Preencher o registro contábil completo.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-CONT-REQ-001",
            description=(
                "Exigir dataContabilizacao e valorPerdaEfetiva quando "
                "houver registro contábil."
            ),
            source="XSD e instruções",
            columns=required,
            message="Os campos obrigatórios da contabilização estão presentes.",
        )

    def _validate_accounting_date_order(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("dataDescoberta", "dataContabilizacao")
        if not self._has_accounting_record(row):
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-DATA-001",
                description=(
                    "Verificar se a contabilização não é anterior à "
                    "descoberta."
                ),
                source="Instruções e crítica de pós-processamento DRO000010",
                columns=fields,
                message="A linha não contém registro contábil.",
            )

        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-DATA-001",
                description=(
                    "Verificar se a contabilização não é anterior à "
                    "descoberta."
                ),
                source="Instruções e crítica de pós-processamento DRO000010",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        if any(row.get_field(name).is_absent for name in fields):
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-DATA-001",
                description=(
                    "Verificar se a contabilização não é anterior à "
                    "descoberta."
                ),
                source="Instruções e crítica de pós-processamento DRO000010",
                columns=fields,
                message="Uma das datas não foi informada.",
            )

        discovery = row.get_value("dataDescoberta")
        accounting = row.get_value("dataContabilizacao")
        assert isinstance(discovery, date)
        assert isinstance(accounting, date)

        if accounting < discovery:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-CONT-DATA-001",
                description=(
                    "Verificar se a contabilização não é anterior à "
                    "descoberta."
                ),
                source="Instruções e crítica de pós-processamento DRO000010",
                columns=fields,
                message="dataContabilizacao é anterior a dataDescoberta.",
                suggestion="Revisar as datas do lançamento.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-CONT-DATA-001",
            description=(
                "Verificar se a contabilização não é anterior à descoberta."
            ),
            source="Instruções e crítica de pós-processamento DRO000010",
            columns=fields,
            message="A data da contabilização é coerente.",
        )

    def _validate_event_signs(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "totalPerdaEfetiva",
            "totalProvisao",
            "totalRecuperado",
            "valorTotalRisco",
        )
        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-SINAL-EVENTO-001",
                description="Validar convenções de sinal dos totais do evento.",
                source="Instruções de preenchimento",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        violations: list[str] = []
        if self._decimal_or_zero(row, "totalPerdaEfetiva") < 0:
            violations.append("totalPerdaEfetiva")
        if self._decimal_or_zero(row, "totalProvisao") < 0:
            violations.append("totalProvisao")
        if self._decimal_or_zero(row, "totalRecuperado") > 0:
            violations.append("totalRecuperado")
        if (
            not row.get_field("valorTotalRisco").is_absent
            and self._decimal_or_zero(row, "valorTotalRisco") < 0
        ):
            violations.append("valorTotalRisco")

        if violations:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-SINAL-EVENTO-001",
                description="Validar convenções de sinal dos totais do evento.",
                source="Instruções de preenchimento",
                columns=tuple(violations),
                message=(
                    "Um ou mais totais violam a convenção de sinal: "
                    f"{', '.join(violations)}."
                ),
                suggestion="Revisar os sinais sem invertê-los automaticamente.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-SINAL-EVENTO-001",
            description="Validar convenções de sinal dos totais do evento.",
            source="Instruções de preenchimento",
            columns=fields,
            message="Os sinais dos totais do evento são válidos.",
        )

    def _validate_accounting_loss_sign(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        field_name = "valorPerdaEfetiva"
        field = row.get_field(field_name)
        if field.is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-SINAL-CONT-001",
                description=(
                    "Verificar se valorPerdaEfetiva contabilizado não é "
                    "negativo."
                ),
                source="Instruções de preenchimento",
                columns=(field_name,),
                message="valorPerdaEfetiva não foi informado.",
            )
        if field.is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-SINAL-CONT-001",
                description=(
                    "Verificar se valorPerdaEfetiva contabilizado não é "
                    "negativo."
                ),
                source="Instruções de preenchimento",
                columns=(field_name,),
                message="valorPerdaEfetiva possui falha de normalização.",
            )

        value = self._decimal_or_zero(row, field_name)
        if value < 0:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-SINAL-CONT-001",
                description=(
                    "Verificar se valorPerdaEfetiva contabilizado não é "
                    "negativo."
                ),
                source="Instruções de preenchimento",
                columns=(field_name,),
                message="valorPerdaEfetiva foi informado com sinal negativo.",
                suggestion="Revisar o lançamento; a perda usa sinal positivo.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-SINAL-CONT-001",
            description=(
                "Verificar se valorPerdaEfetiva contabilizado não é negativo."
            ),
            source="Instruções de preenchimento",
            columns=(field_name,),
            message="O sinal da perda contabilizada é válido.",
        )

    def _validate_recovery_sign(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        field_name = "valorRecuperacao"
        field = row.get_field(field_name)
        if field.is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001411",
                description=(
                    "Verificar se valorRecuperacao é menor ou igual a zero."
                ),
                source="Crítica de pré-processamento",
                columns=(field_name,),
                message="valorRecuperacao não foi informado.",
            )
        if field.is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001411",
                description=(
                    "Verificar se valorRecuperacao é menor ou igual a zero."
                ),
                source="Crítica de pré-processamento",
                columns=(field_name,),
                message="valorRecuperacao possui falha de normalização.",
            )

        value = self._decimal_or_zero(row, field_name)
        if value > 0:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001411",
                description=(
                    "Verificar se valorRecuperacao é menor ou igual a zero."
                ),
                source="Crítica de pré-processamento",
                columns=(field_name,),
                message="valorRecuperacao foi informado com sinal positivo.",
                suggestion="Revisar o sinal; o sistema não o inverterá.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001411",
            description=(
                "Verificar se valorRecuperacao é menor ou igual a zero."
            ),
            source="Crítica de pré-processamento",
            columns=(field_name,),
            message="O sinal da recuperação é válido.",
        )

    def _validate_recovery_source(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = (
            "dataOcorrencia",
            "valorRecuperacao",
            "fonteRecuperacao",
        )
        dependency = self._dependency_result(
            row,
            row_kind,
            code="DRO001421",
            description=(
                "Exigir fonteRecuperacao quando houver recuperação para "
                "evento alcançado pela vigência."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            required_valid_fields=(
                "dataOcorrencia",
                "valorRecuperacao",
            ),
        )
        if dependency is not None:
            return dependency

        occurrence = row.get_value("dataOcorrencia")
        recovery = self._decimal_or_zero(row, "valorRecuperacao")
        assert isinstance(occurrence, date)

        if (
            occurrence < CIRCULAR_START_DATE
            or recovery >= 0
        ):
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001421",
                description=(
                    "Exigir fonteRecuperacao quando houver recuperação para "
                    "evento alcançado pela vigência."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="A condição de obrigatoriedade não foi alcançada.",
            )

        source_field = row.get_field("fonteRecuperacao")
        if source_field.is_invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001421",
                description=(
                    "Exigir fonteRecuperacao quando houver recuperação para "
                    "evento alcançado pela vigência."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="fonteRecuperacao possui falha de normalização.",
            )

        source = row.get_value("fonteRecuperacao")
        if source_field.is_absent or source == "NA":
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001421",
                description=(
                    "Exigir fonteRecuperacao quando houver recuperação para "
                    "evento alcançado pela vigência."
                ),
                source="Crítica de pré-processamento",
                columns=("fonteRecuperacao",),
                message=(
                    "Há recuperação negativa, mas a fonte não foi informada "
                    "como S ou O."
                ),
                suggestion="Informar a origem real do ressarcimento.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001421",
            description=(
                "Exigir fonteRecuperacao quando houver recuperação para "
                "evento alcançado pela vigência."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="A fonte da recuperação foi informada.",
        )

    def _validate_debit_internal_to_cosif(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._validate_pair_presence(
            row=row,
            row_kind=row_kind,
            code="DRO001441",
            source_field="contaBalAnaliticoDebito",
            required_field="contaCosifDebito",
            description=(
                "Exigir contaCosifDebito quando a conta interna de débito "
                "for informada."
            ),
        )

    def _validate_credit_internal_to_cosif(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._validate_pair_presence(
            row=row,
            row_kind=row_kind,
            code="DRO001442",
            source_field="contaBalAnaliticoCredito",
            required_field="contaCosifCredito",
            description=(
                "Exigir contaCosifCredito quando a conta interna de crédito "
                "for informada."
            ),
        )

    def _validate_debit_cosif_to_internal(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._validate_pair_presence(
            row=row,
            row_kind=row_kind,
            code="DRO001443",
            source_field="contaCosifDebito",
            required_field="contaBalAnaliticoDebito",
            description=(
                "Exigir conta interna de débito quando contaCosifDebito "
                "for informada."
            ),
        )

    def _validate_credit_cosif_to_internal(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._validate_pair_presence(
            row=row,
            row_kind=row_kind,
            code="DRO001444",
            source_field="contaCosifCredito",
            required_field="contaBalAnaliticoCredito",
            description=(
                "Exigir conta interna de crédito quando contaCosifCredito "
                "for informada."
            ),
        )

    def _validate_pair_presence(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        source_field: str,
        required_field: str,
        description: str,
    ) -> RowRuleResult:
        fields = (source_field, required_field)
        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        if row.get_field(source_field).is_absent:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=fields,
                message=f"{source_field} não foi informado.",
            )

        if row.get_field(required_field).is_absent:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code=code,
                description=description,
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    f"{required_field} é obrigatório quando "
                    f"{source_field} está preenchido."
                ),
                suggestion=f"Informar {required_field} com a conta real.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source="Crítica de pré-processamento",
            columns=fields,
            message="O par de contas foi informado.",
        )

    def _validate_account_fields_for_movement(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        movement_fields = (
            "valorPerdaEfetiva",
            "valorProvisao",
            "valorRecuperacao",
        )
        fields = (*movement_fields, *ACCOUNT_FIELDS)
        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="DRO001451",
                description=(
                    "Exigir campos contábeis quando houver movimentação "
                    "que não seja exclusivamente de risco."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        has_movement = any(
            self._decimal_or_zero(row, field_name) != 0
            for field_name in movement_fields
        )
        if not has_movement:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="DRO001451",
                description=(
                    "Exigir campos contábeis quando houver movimentação "
                    "que não seja exclusivamente de risco."
                ),
                source="Crítica de pré-processamento",
                columns=fields,
                message="A linha não possui movimentação contábil diferente de zero.",
            )

        missing = tuple(
            field_name
            for field_name in ACCOUNT_FIELDS
            if row.get_field(field_name).is_absent
        )
        if missing:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="DRO001451",
                description=(
                    "Exigir campos contábeis quando houver movimentação "
                    "que não seja exclusivamente de risco."
                ),
                source="Crítica de pré-processamento",
                columns=missing,
                message=(
                    "Movimentação contábil sem todas as contas exigidas: "
                    f"{', '.join(missing)}."
                ),
                suggestion="Informar as contas reais de débito e crédito.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="DRO001451",
            description=(
                "Exigir campos contábeis quando houver movimentação que "
                "não seja exclusivamente de risco."
            ),
            source="Crítica de pré-processamento",
            columns=fields,
            message="A movimentação possui os campos contábeis necessários.",
        )

    def _defer_risk_only_accounting_rule(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code="DRO001452",
            description=(
                "Proibir contabilização quando o idEvento possuir somente "
                "valores em risco."
            ),
            source="Crítica de pré-processamento",
            columns=("valorRisco", *ACCOUNTING_FIELDS),
            message=(
                "Depende da análise de todas as linhas do mesmo idEvento."
            ),
        )

    def _validate_recovery_exclusivity(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        profile: RegulatoryVersion,
    ) -> RowRuleResult:
        fields = (
            "valorRecuperacao",
            "valorPerdaEfetiva",
            "valorProvisao",
        )
        if profile.code != "DRO_2026_12_PRESUMIDA":
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-REC-EXCL-001",
                description=(
                    "Exigir exclusividade da contabilização de recuperação."
                ),
                source="Instruções 12/2026",
                columns=fields,
                message="A regra é nova e não se aplica ao perfil selecionado.",
            )

        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-REC-EXCL-001",
                description=(
                    "Exigir exclusividade da contabilização de recuperação."
                ),
                source="Instruções 12/2026",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        recovery = self._decimal_or_zero(row, "valorRecuperacao")
        if recovery >= 0:
            return self._not_applicable(
                row=row,
                row_kind=row_kind,
                code="BASE-REC-EXCL-001",
                description=(
                    "Exigir exclusividade da contabilização de recuperação."
                ),
                source="Instruções 12/2026",
                columns=fields,
                message="Não há recuperação negativa na linha.",
            )

        loss = self._decimal_or_zero(row, "valorPerdaEfetiva")
        provision = self._decimal_or_zero(row, "valorProvisao")
        if loss != 0 or provision != 0:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-REC-EXCL-001",
                description=(
                    "Exigir exclusividade da contabilização de recuperação."
                ),
                source="Instruções 12/2026",
                columns=fields,
                message=(
                    "A recuperação deve ser exclusiva, com perda e provisão "
                    "zeradas na mesma contabilização."
                ),
                suggestion="Separar a recuperação em lançamento exclusivo.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-REC-EXCL-001",
            description=(
                "Exigir exclusividade da contabilização de recuperação."
            ),
            source="Instruções 12/2026",
            columns=fields,
            message="A recuperação foi registrada de forma exclusiva.",
        )

    def _validate_exclusion_pair(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        fields = ("dataExclusao", "motivoExclusao")
        invalid = self._invalid_fields(row, fields)
        if invalid:
            return self._not_executed(
                row=row,
                row_kind=row_kind,
                code="BASE-EXCL-001",
                description=(
                    "Exigir dataExclusao e motivoExclusao para evento "
                    "excluído."
                ),
                source="Instruções 12/2026",
                columns=fields,
                message=(
                    "Há falha de normalização em: "
                    f"{', '.join(invalid)}."
                ),
            )

        missing = tuple(
            field_name
            for field_name in fields
            if row.get_field(field_name).is_absent
        )
        if missing:
            return self._failed(
                row=row,
                row_kind=row_kind,
                code="BASE-EXCL-001",
                description=(
                    "Exigir dataExclusao e motivoExclusao para evento "
                    "excluído."
                ),
                source="Instruções 12/2026",
                columns=missing,
                message=(
                    "Evento excluído sem todos os campos obrigatórios: "
                    f"{', '.join(missing)}."
                ),
                suggestion="Informar a data e o motivo reais da exclusão.",
            )

        return self._passed(
            row=row,
            row_kind=row_kind,
            code="BASE-EXCL-001",
            description=(
                "Exigir dataExclusao e motivoExclusao para evento excluído."
            ),
            source="Instruções 12/2026",
            columns=fields,
            message="Os campos da exclusão foram informados.",
        )

    def _defer_exclusion_reason_domain(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
    ) -> RowRuleResult:
        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code="BASE-EXCL-DOM-001",
            description=(
                "Validar o domínio definitivo de motivoExclusao."
            ),
            source="Instruções 12/2026 e conflito CONF-007",
            columns=("motivoExclusao",),
            message=(
                "O leiaute ilustrativo apresenta códigos 1 a 6, enquanto "
                "o Anexo IV apresenta códigos 1 a 8."
            ),
        )

    @staticmethod
    def _has_accounting_record(row: NormalizedBaseRow) -> bool:
        return any(
            not row.get_field(field_name).is_absent
            for field_name in ACCOUNTING_FIELDS
        )

    @staticmethod
    def _invalid_fields(
        row: NormalizedBaseRow,
        fields: Iterable[str],
    ) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in fields
            if row.get_field(field_name).is_invalid
        )

    def _dependency_result(
        self,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        *,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        required_valid_fields: tuple[str, ...] | None = None,
    ) -> RowRuleResult | None:
        checked_fields = required_valid_fields or columns
        invalid = self._invalid_fields(row, checked_fields)
        if not invalid:
            return None

        return self._not_executed(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source=source,
            columns=columns,
            message=(
                "A regra depende de campos inválidos: "
                f"{', '.join(invalid)}."
            ),
        )

    @staticmethod
    def _decimal_or_zero(
        row: NormalizedBaseRow,
        field_name: str,
    ) -> Decimal:
        field = row.get_field(field_name)
        if field.is_absent:
            return Decimal("0")

        value = field.normalized_value
        if isinstance(value, Decimal):
            return value

        raise TypeError(
            f"O campo {field_name} não contém Decimal normalizado."
        )

    def _passed(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
    ) -> RowRuleResult:
        return self._build_result(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.PASSED,
            columns=columns,
            message=message,
        )

    def _failed(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
    ) -> RowRuleResult:
        return self._build_result(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_ERROR,
            status=RuleExecutionStatus.FAILED,
            columns=columns,
            message=message,
            suggestion=suggestion,
        )

    def _not_applicable(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
    ) -> RowRuleResult:
        return self._build_result(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_INFORMATION,
            status=RuleExecutionStatus.NOT_APPLICABLE,
            columns=columns,
            message=message,
        )

    def _not_executed(
        self,
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        description: str,
        source: str,
        columns: tuple[str, ...],
        message: str,
    ) -> RowRuleResult:
        return self._build_result(
            row=row,
            row_kind=row_kind,
            code=code,
            description=description,
            source=source,
            severity=SEVERITY_NOT_EXECUTED,
            status=RuleExecutionStatus.NOT_EXECUTED,
            columns=columns,
            message=message,
        )

    @staticmethod
    def _build_result(
        *,
        row: NormalizedBaseRow,
        row_kind: BaseRowKind,
        code: str,
        description: str,
        source: str,
        severity: str,
        status: RuleExecutionStatus,
        columns: tuple[str, ...],
        message: str,
        suggestion: str | None = None,
    ) -> RowRuleResult:
        original_values = tuple(
            (
                column,
                row.get_field(column).original_value,
            )
            for column in columns
            if column in row.fields
        )
        normalized_values = tuple(
            (
                column,
                row.get_field(column).serialized_value,
            )
            for column in columns
            if column in row.fields
        )

        return RowRuleResult(
            code=code,
            description=description,
            source=source,
            severity=severity,
            status=status,
            row_number=row.row_number,
            id_evento=row.id_evento,
            row_kind=row_kind,
            columns=columns,
            message=message,
            suggestion=suggestion,
            original_values=original_values,
            normalized_values=normalized_values,
        )


def validate_base_rows(
    normalization: BaseRowsNormalizationResult,
    profile: RegulatoryVersion,
) -> BaseRowsValidationResult:
    """Atalho funcional para a validação local das linhas."""

    return BaseRowBusinessValidator().validate(
        normalization,
        profile,
    )
