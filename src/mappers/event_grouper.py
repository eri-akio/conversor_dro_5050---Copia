"""Agrupamento determinístico das linhas da Base por ``idEvento``."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Iterable

from src.domain.base_row import (
    BaseRowsNormalizationResult,
    NormalizedBaseRow,
)
from src.domain.base_row_validation import (
    BaseRowKind,
    BaseRowsValidationResult,
    RuleExecutionStatus,
)
from src.domain.grouped_event import (
    EventGroupingResult,
    EventRuleResult,
    GroupedAccounting,
    GroupedEvent,
    GroupedProbability,
    ResolvedEventField,
)


SEVERITY_BLOCKING_ERROR = 'ERRO IMPEDITIVO'
SEVERITY_INFORMATION = 'INFORMAÇÃO'
SEVERITY_NOT_EXECUTED = 'REGRA NÃO EXECUTADA'

EVENT_FIELD_COLUMNS = (
    'categoriaNivel1',
    'categoriaNivel2',
    'tipoAvaliacao',
    'unidadeNegocio',
    'dataDescoberta',
    'dataOcorrencia',
    'totalPerdaEfetiva',
    'totalProvisao',
    'totalRecuperado',
    'valorTotalRisco',
    'naturezaContingencia',
    'codSistemaOrigem',
    'codigoEventoOrigem',
    'descricaoEvento',
    'riscoAssociado',
    'ligacaoRiscoSocioambiental',
    'ligadoRiscoCibernetico',
    'negocioDescontinuado',
    'idBacen',
    'idEventoAgregador',
    'dataExclusao',
    'motivoExclusao',
)

ACCOUNTING_COLUMNS = (
    'dataContabilizacao',
    'contaBalAnaliticoDebito',
    'contaBalAnaliticoCredito',
    'contaCosifDebito',
    'contaCosifCredito',
    'valorPerdaEfetiva',
    'valorProvisao',
    'valorRecuperacao',
    'fonteRecuperacao',
)


class EventGrouper:
    """Cria um único objeto de evento para cada identificador distinto."""

    def group(
        self,
        normalization: BaseRowsNormalizationResult,
        row_validation: BaseRowsValidationResult,
    ) -> EventGroupingResult:
        validation_by_row = {
            item.row_number: item
            for item in row_validation.rows
        }
        grouped_rows: dict[str, list[NormalizedBaseRow]] = {}
        ungrouped_rows: list[int] = []
        global_results: list[EventRuleResult] = []
        collisions = self._find_normalized_id_collisions(
            normalization.rows
        )

        for normalized_id, originals in collisions.items():
            row_numbers = tuple(sorted(
                row_number
                for rows in originals.values()
                for row_number in rows
            ))
            original_values = tuple(originals)
            global_results.append(
                EventRuleResult(
                    code='MAP-EVT-ID-COLISAO-001',
                    description=(
                        'Proibir colisões após a normalização do idEvento.'
                    ),
                    source='Regra interna de agrupamento',
                    severity=SEVERITY_BLOCKING_ERROR,
                    status=RuleExecutionStatus.FAILED,
                    id_evento=normalized_id,
                    row_numbers=row_numbers,
                    columns=('idEvento',),
                    message=(
                        'Identificadores originais distintos resultaram no '
                        'mesmo idEvento normalizado: '
                        f'{normalized_id}. Originais: '
                        f'{", ".join(original_values)}.'
                    ),
                    suggestion=(
                        'Corrigir os identificadores na planilha para que '
                        'cada evento possua um idEvento normalizado único.'
                    ),
                    values=(
                        ('idEvento normalizado', normalized_id),
                        ('idEventos originais', original_values),
                    ),
                )
            )

        for row in normalization.rows:
            if (
                row.get_field('idEvento').is_invalid
                or row.get_field('idEvento').is_absent
                or not row.id_evento
            ):
                ungrouped_rows.append(row.row_number)
                global_results.append(
                    EventRuleResult(
                        code='MAP-EVT-000',
                        description=(
                            'Exigir idEvento válido antes do agrupamento.'
                        ),
                        source='Regra interna de agrupamento',
                        severity=SEVERITY_BLOCKING_ERROR,
                        status=RuleExecutionStatus.FAILED,
                        id_evento=None,
                        row_numbers=(row.row_number,),
                        columns=('idEvento',),
                        message=(
                            'A linha não pôde ser associada a um evento.'
                        ),
                        suggestion=(
                            'Informar o idEvento real sem alterar zeros ou '
                            'caracteres significativos.'
                        ),
                    )
                )
                continue

            if row.id_evento in collisions:
                ungrouped_rows.append(row.row_number)
                continue

            grouped_rows.setdefault(row.id_evento, []).append(row)

        events: list[GroupedEvent] = []

        for id_evento, rows in grouped_rows.items():
            event = self._build_event(
                id_evento=id_evento,
                rows=tuple(rows),
                profile_code=normalization.profile_code,
                validation_by_row=validation_by_row,
            )
            events.append(event)
            global_results.extend(event.grouping_results)

        return EventGroupingResult(
            profile_code=normalization.profile_code,
            events=tuple(events),
            ungrouped_row_numbers=tuple(ungrouped_rows),
            rule_results=tuple(global_results),
        )

    @staticmethod
    def _find_normalized_id_collisions(
        rows: tuple[NormalizedBaseRow, ...],
    ) -> dict[str, dict[str, tuple[int, ...]]]:
        """Localiza origens distintas que convergem para o mesmo ID."""

        origins_by_id: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in rows:
            field = row.get_field('idEvento')
            if field.is_invalid or field.is_absent or not row.id_evento:
                continue

            original = field.original_value
            original_text = (
                original.strip()
                if isinstance(original, str)
                else str(original)
            )
            origins_by_id[row.id_evento][original_text].append(
                row.row_number
            )

        return {
            normalized_id: {
                original: tuple(row_numbers)
                for original, row_numbers in originals.items()
            }
            for normalized_id, originals in origins_by_id.items()
            if len(originals) > 1
        }

    def _build_event(
        self,
        *,
        id_evento: str,
        rows: tuple[NormalizedBaseRow, ...],
        profile_code: str,
        validation_by_row: dict[int, Any],
    ) -> GroupedEvent:
        row_numbers = tuple(row.row_number for row in rows)
        results: list[EventRuleResult] = []

        row_kinds = tuple(
            dict.fromkeys(
                validation_by_row[row.row_number].row_kind
                for row in rows
                if row.row_number in validation_by_row
            )
        )
        row_kind = row_kinds[0] if len(row_kinds) == 1 else None

        if len(row_kinds) > 1:
            results.append(
                EventRuleResult(
                    code='MAP-EVT-TIPO-001',
                    description=(
                        'Exigir um único tipo lógico para todas as linhas '
                        'do evento.'
                    ),
                    source='Regra interna de agrupamento',
                    severity=SEVERITY_BLOCKING_ERROR,
                    status=RuleExecutionStatus.FAILED,
                    id_evento=id_evento,
                    row_numbers=row_numbers,
                    columns=(
                        'dataExclusao',
                        'motivoExclusao',
                    ),
                    message=(
                        'O mesmo idEvento foi classificado simultaneamente '
                        'como individualizado e excluído.'
                    ),
                    suggestion=(
                        'Separar ou corrigir as linhas conforme o tipo real '
                        'do evento.'
                    ),
                    values=(
                        (
                            'tipos',
                            tuple(kind.value for kind in row_kinds),
                        ),
                    ),
                )
            )

        event_fields = {
            column_name: self._resolve_event_field(
                rows,
                column_name,
            )
            for column_name in EVENT_FIELD_COLUMNS
        }

        conflicting_fields = tuple(
            field.column_name
            for field in event_fields.values()
            if field.has_conflict
        )
        invalid_fields = tuple(
            field.column_name
            for field in event_fields.values()
            if field.invalid_rows
        )

        if conflicting_fields:
            results.append(
                EventRuleResult(
                    code='MAP-EVT-001',
                    description=(
                        'Proibir valores conflitantes nos atributos '
                        'repetidos do mesmo evento.'
                    ),
                    source='Regra interna de agrupamento',
                    severity=SEVERITY_BLOCKING_ERROR,
                    status=RuleExecutionStatus.FAILED,
                    id_evento=id_evento,
                    row_numbers=row_numbers,
                    columns=conflicting_fields,
                    message=(
                        'Foram encontrados valores normalizados diferentes '
                        'para o mesmo atributo do evento.'
                    ),
                    suggestion=(
                        'Revisar as linhas. O sistema não escolhe um valor '
                        'arbitrariamente.'
                    ),
                    values=tuple(
                        (
                            field_name,
                            event_fields[
                                field_name
                            ].distinct_serialized_values,
                        )
                        for field_name in conflicting_fields
                    ),
                )
            )
        elif invalid_fields:
            results.append(
                EventRuleResult(
                    code='MAP-EVT-NORM-001',
                    description=(
                        'Resolver atributos do evento somente com campos '
                        'normalizados.'
                    ),
                    source='Regra interna de agrupamento',
                    severity=SEVERITY_NOT_EXECUTED,
                    status=RuleExecutionStatus.NOT_EXECUTED,
                    id_evento=id_evento,
                    row_numbers=row_numbers,
                    columns=invalid_fields,
                    message=(
                        'Há campos inválidos que impedem resolver todos os '
                        'atributos do evento.'
                    ),
                )
            )
        else:
            results.append(
                EventRuleResult(
                    code='MAP-EVT-001',
                    description=(
                        'Proibir valores conflitantes nos atributos '
                        'repetidos do mesmo evento.'
                    ),
                    source='Regra interna de agrupamento',
                    severity=SEVERITY_INFORMATION,
                    status=RuleExecutionStatus.PASSED,
                    id_evento=id_evento,
                    row_numbers=row_numbers,
                    columns=EVENT_FIELD_COLUMNS,
                    message=(
                        'Os atributos repetidos possuem no máximo um valor '
                        'normalizado distinto.'
                    ),
                )
            )

        probabilities, probability_result = self._group_probabilities(
            id_evento=id_evento,
            rows=rows,
        )
        results.append(probability_result)

        accountings = tuple(
            self._build_accounting(row)
            for row in rows
            if self._has_accounting(row)
        )

        source_names = tuple(
            dict.fromkeys(
                value
                for row in rows
                if (
                    value := row.get_serialized_value('Source.Name')
                )
            )
        )

        return GroupedEvent(
            id_evento=id_evento,
            profile_code=profile_code,
            row_kind=row_kind,
            row_numbers=row_numbers,
            source_names=source_names,
            event_fields=MappingProxyType(event_fields),
            probabilities=probabilities,
            accountings=accountings,
            grouping_results=tuple(results),
        )

    @staticmethod
    def _resolve_event_field(
        rows: tuple[NormalizedBaseRow, ...],
        column_name: str,
    ) -> ResolvedEventField:
        valid_by_serialized: dict[str, Any] = {}
        source_rows: list[int] = []
        absent_rows: list[int] = []
        invalid_rows: list[int] = []

        for row in rows:
            field = row.get_field(column_name)
            if not field.applicable:
                continue
            if field.is_invalid:
                invalid_rows.append(row.row_number)
                continue
            if field.is_absent or field.serialized_value is None:
                absent_rows.append(row.row_number)
                continue

            source_rows.append(row.row_number)
            valid_by_serialized.setdefault(
                field.serialized_value,
                field.normalized_value,
            )

        distinct = tuple(valid_by_serialized)
        if len(distinct) == 1:
            serialized = distinct[0]
            normalized = valid_by_serialized[serialized]
        else:
            serialized = None
            normalized = None

        return ResolvedEventField(
            column_name=column_name,
            normalized_value=normalized,
            serialized_value=serialized,
            source_rows=tuple(source_rows),
            absent_rows=tuple(absent_rows),
            invalid_rows=tuple(invalid_rows),
            distinct_serialized_values=distinct,
        )

    def _group_probabilities(
        self,
        *,
        id_evento: str,
        rows: tuple[NormalizedBaseRow, ...],
    ) -> tuple[tuple[GroupedProbability, ...], EventRuleResult]:
        by_code: dict[str, list[tuple[int, Decimal]]] = defaultdict(list)

        for row in rows:
            probability = row.get_field('probabilidadePerda')
            risk = row.get_field('valorRisco')

            if (
                not probability.applicable
                or probability.is_absent
                or probability.is_invalid
                or risk.is_absent
                or risk.is_invalid
            ):
                continue

            code = probability.serialized_value
            value = risk.normalized_value
            if code is not None and isinstance(value, Decimal):
                by_code[code].append((row.row_number, value))

        grouped: list[GroupedProbability] = []
        conflicts: list[tuple[str, tuple[Decimal, ...]]] = []

        for code, entries in by_code.items():
            distinct_values = tuple(
                dict.fromkeys(value for _, value in entries)
            )
            has_conflict = len(distinct_values) > 1
            if has_conflict:
                conflicts.append((code, distinct_values))
                resolved_value = None
            else:
                resolved_value = distinct_values[0]

            grouped.append(
                GroupedProbability(
                    probability_code=code,
                    value_risk=resolved_value,
                    source_rows=tuple(row for row, _ in entries),
                    distinct_values=distinct_values,
                )
            )

        row_numbers = tuple(row.row_number for row in rows)
        if conflicts:
            result = EventRuleResult(
                code='MAP-PROB-001',
                description=(
                    'Proibir valores de risco conflitantes para a mesma '
                    'probabilidade do evento.'
                ),
                source='Regra interna de agrupamento',
                severity=SEVERITY_BLOCKING_ERROR,
                status=RuleExecutionStatus.FAILED,
                id_evento=id_evento,
                row_numbers=row_numbers,
                columns=('probabilidadePerda', 'valorRisco'),
                message=(
                    'A mesma probabilidade foi repetida com valores de '
                    'risco diferentes.'
                ),
                suggestion=(
                    'Revisar os valores. O sistema não soma nem escolhe '
                    'arbitrariamente probabilidades duplicadas.'
                ),
                values=tuple(conflicts),
            )
        elif grouped:
            result = EventRuleResult(
                code='MAP-PROB-001',
                description=(
                    'Proibir valores de risco conflitantes para a mesma '
                    'probabilidade do evento.'
                ),
                source='Regra interna de agrupamento',
                severity=SEVERITY_INFORMATION,
                status=RuleExecutionStatus.PASSED,
                id_evento=id_evento,
                row_numbers=row_numbers,
                columns=('probabilidadePerda', 'valorRisco'),
                message=(
                    'As probabilidades foram agrupadas por código sem '
                    'conflito de valor.'
                ),
            )
        else:
            result = EventRuleResult(
                code='MAP-PROB-001',
                description=(
                    'Proibir valores de risco conflitantes para a mesma '
                    'probabilidade do evento.'
                ),
                source='Regra interna de agrupamento',
                severity=SEVERITY_INFORMATION,
                status=RuleExecutionStatus.NOT_APPLICABLE,
                id_evento=id_evento,
                row_numbers=row_numbers,
                columns=('probabilidadePerda', 'valorRisco'),
                message='O evento não possui probabilidades completas.',
            )

        return tuple(grouped), result

    @staticmethod
    def _has_accounting(row: NormalizedBaseRow) -> bool:
        return any(
            not row.get_field(column_name).is_absent
            for column_name in ACCOUNTING_COLUMNS
        )

    @staticmethod
    def _build_accounting(row: NormalizedBaseRow) -> GroupedAccounting:
        normalized = {
            column_name: row.get_value(column_name)
            for column_name in ACCOUNTING_COLUMNS
        }
        serialized = {
            column_name: row.get_serialized_value(column_name)
            for column_name in ACCOUNTING_COLUMNS
        }
        return GroupedAccounting(
            row_number=row.row_number,
            normalized_values=MappingProxyType(normalized),
            serialized_values=MappingProxyType(serialized),
        )


def group_base_rows(
    normalization: BaseRowsNormalizationResult,
    row_validation: BaseRowsValidationResult,
) -> EventGroupingResult:
    """Atalho funcional para o agrupador padrão."""

    return EventGrouper().group(
        normalization,
        row_validation,
    )
