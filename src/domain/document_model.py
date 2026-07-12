"""Objetos finais do Documento 5050 antes da geração do XML.

As classes deste módulo representam exatamente os blocos disponíveis
nos XSDs fornecidos:

- documento;
- eventosIndividualizados;
- probabilidadesPerdas;
- contabilizacoes;
- eventosConsolidados;
- sistemasOrigem;
- contasSubtitulosInternos.

Os objetos mantêm tipos Python adequados, como ``date`` e ``Decimal``.
Cada classe fornece ``as_xml_attributes()`` para a próxima etapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from src.domain.document_header import DocumentHeader


def _decimal_text(value: Decimal) -> str:
    """Serializa valor monetário validado com duas casas."""

    normalized = abs(value) if value == 0 else value
    return format(normalized, ".2f")


def _optional_attribute(
    attributes: dict[str, str],
    name: str,
    value: Any,
) -> None:
    """Inclui atributo somente quando houver valor real."""

    if value is None:
        return

    if isinstance(value, Decimal):
        attributes[name] = _decimal_text(value)
    elif isinstance(value, date):
        attributes[name] = value.isoformat()
    else:
        attributes[name] = str(value)


@dataclass(frozen=True, slots=True)
class FinalProbability:
    """Registro final do elemento ``probabilidadePerda``."""

    probability: str
    value_risk: Decimal
    source_rows: tuple[int, ...]

    def as_xml_attributes(self) -> dict[str, str]:
        return {
            "probabilidade": self.probability,
            "valorRisco": _decimal_text(self.value_risk),
        }


@dataclass(frozen=True, slots=True)
class FinalAccounting:
    """Registro final do elemento ``contabilizacao``."""

    accounting_date: date
    loss_value: Decimal
    source_row: int
    internal_debit_account: str | None = None
    internal_credit_account: str | None = None
    cosif_debit_account: str | None = None
    cosif_credit_account: str | None = None
    provision_value: Decimal | None = None
    recovery_value: Decimal | None = None
    recovery_source: str | None = None

    def as_xml_attributes(self) -> dict[str, str]:
        attributes = {
            "dataContabilizacao": (
                self.accounting_date.isoformat()
            )
        }

        _optional_attribute(
            attributes,
            "contaBalAnaliticoDebito",
            self.internal_debit_account,
        )
        _optional_attribute(
            attributes,
            "contaBalAnaliticoCredito",
            self.internal_credit_account,
        )
        _optional_attribute(
            attributes,
            "contaCosifDebito",
            self.cosif_debit_account,
        )
        _optional_attribute(
            attributes,
            "contaCosifCredito",
            self.cosif_credit_account,
        )

        attributes["valorPerdaEfetiva"] = _decimal_text(
            self.loss_value
        )

        _optional_attribute(
            attributes,
            "valorProvisao",
            self.provision_value,
        )
        _optional_attribute(
            attributes,
            "valorRecuperacao",
            self.recovery_value,
        )
        _optional_attribute(
            attributes,
            "fonteRecuperacao",
            self.recovery_source,
        )

        return attributes


@dataclass(frozen=True, slots=True)
class FinalIndividualEvent:
    """Evento individualizado pronto para serialização."""

    event_id: str
    category_level_1: str
    assessment_type: str
    business_unit: str
    occurrence_date: date
    total_loss: Decimal
    total_recovery: Decimal
    contingency_nature: str
    source_system_code: str
    origin_event_code: str
    bacen_id: str
    source_rows: tuple[int, ...]
    category_level_2: str | None = None
    discovery_date: date | None = None
    total_provision: Decimal | None = None
    total_risk: Decimal | None = None
    event_description: str | None = None
    associated_risk: str | None = None
    socioenvironmental_risk: str | None = None
    cyber_risk: str | None = None
    discontinued_business: str | None = None
    probabilities: tuple[FinalProbability, ...] = ()
    accountings: tuple[FinalAccounting, ...] = ()

    def as_xml_attributes(self) -> dict[str, str]:
        """Retorna os nomes exatos do XSD.

        O alias da planilha ``ligacaoRiscoSocioambiental`` resulta em
        ``ligadoRiscoSocioAmbiental``, conforme os XSDs fornecidos.
        """

        attributes = {
            "idEvento": self.event_id,
            "categoriaNivel1": self.category_level_1,
        }

        _optional_attribute(
            attributes,
            "categoriaNivel2",
            self.category_level_2,
        )

        attributes.update(
            {
                "tipoAvaliacao": self.assessment_type,
                "unidadeNegocio": self.business_unit,
            }
        )

        _optional_attribute(
            attributes,
            "dataDescoberta",
            self.discovery_date,
        )

        attributes.update(
            {
                "dataOcorrencia": (
                    self.occurrence_date.isoformat()
                ),
                "totalPerdaEfetiva": _decimal_text(
                    self.total_loss
                ),
            }
        )

        _optional_attribute(
            attributes,
            "totalProvisao",
            self.total_provision,
        )

        attributes["totalRecuperado"] = _decimal_text(
            self.total_recovery
        )

        _optional_attribute(
            attributes,
            "valorTotalRisco",
            self.total_risk,
        )

        attributes.update(
            {
                "naturezaContingencia": (
                    self.contingency_nature
                ),
                "codSistemaOrigem": (
                    self.source_system_code
                ),
                "codigoEventoOrigem": (
                    self.origin_event_code
                ),
            }
        )

        _optional_attribute(
            attributes,
            "descricaoEvento",
            self.event_description,
        )
        _optional_attribute(
            attributes,
            "riscoAssociado",
            self.associated_risk,
        )
        _optional_attribute(
            attributes,
            "ligadoRiscoSocioAmbiental",
            self.socioenvironmental_risk,
        )
        _optional_attribute(
            attributes,
            "ligadoRiscoCibernetico",
            self.cyber_risk,
        )
        _optional_attribute(
            attributes,
            "negocioDescontinuado",
            self.discontinued_business,
        )

        attributes["idBacen"] = self.bacen_id
        return attributes


@dataclass(frozen=True, slots=True)
class FinalConsolidatedEvent:
    """Evento consolidado calculado por categoria de nível 1."""

    category_level_1: str
    total_event_count: int
    semester_event_count: int
    total_loss: Decimal
    semester_loss: Decimal
    total_provision: Decimal
    semester_provision: Decimal
    source_event_ids: tuple[str, ...] = ()
    source_rows: tuple[int, ...] = ()
    source_original_values: tuple[tuple[str, Any], ...] = ()

    def as_xml_attributes(self) -> dict[str, str]:
        return {
            "categoriaNivel1Consol": self.category_level_1,
            "numEventosTotalConsol": str(
                self.total_event_count
            ),
            "numEventosSemestreConsol": str(
                self.semester_event_count
            ),
            "perdaEfetivaTotalConsol": _decimal_text(
                self.total_loss
            ),
            "perdaEfetivaSemestreConsol": _decimal_text(
                self.semester_loss
            ),
            "provisaoTotalConsol": _decimal_text(
                self.total_provision
            ),
            "provisaoSemestreConsol": _decimal_text(
                self.semester_provision
            ),
        }


@dataclass(frozen=True, slots=True)
class FinalSourceSystem:
    """Registro final do elemento ``sistema``."""

    code: str
    name: str
    source_row: int

    def as_xml_attributes(self) -> dict[str, str]:
        return {
            "codigoSistema": self.code,
            "nomeSistema": self.name,
        }


@dataclass(frozen=True, slots=True)
class FinalInternalAccount:
    """Registro final do elemento ``conta``."""

    code: str
    name: str
    source_row: int

    def as_xml_attributes(self) -> dict[str, str]:
        return {
            "codigoConta": self.code,
            "nomeConta": self.name,
        }


@dataclass(frozen=True, slots=True)
class UnsupportedProfileValue:
    """Valor preservado que não cabe no XSD selecionado."""

    event_id: str
    source_rows: tuple[int, ...]
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class FinalDocument:
    """Documento final em memória, anterior ao XML."""

    header: DocumentHeader
    profile_code: str
    xsd_path: Path
    individualized_events: tuple[
        FinalIndividualEvent,
        ...,
    ]
    consolidated_events: tuple[
        FinalConsolidatedEvent,
        ...,
    ]
    source_systems: tuple[FinalSourceSystem, ...]
    internal_accounts: tuple[
        FinalInternalAccount,
        ...,
    ]
    unsupported_profile_values: tuple[
        UnsupportedProfileValue,
        ...,
    ] = ()

    def as_xml_attributes(self) -> dict[str, str]:
        return self.header.as_xml_attributes()

    @property
    def individualized_event_count(self) -> int:
        return len(self.individualized_events)

    @property
    def consolidated_event_count(self) -> int:
        return len(self.consolidated_events)

    @property
    def source_system_count(self) -> int:
        return len(self.source_systems)

    @property
    def internal_account_count(self) -> int:
        return len(self.internal_accounts)


@dataclass(frozen=True, slots=True)
class DocumentBuildIssue:
    """Ocorrência da montagem do objeto final."""

    code: str
    severity: str
    message: str
    source: str
    blocks_xml: bool
    blocks_apt: bool
    event_id: str | None = None
    row_numbers: tuple[int, ...] = ()
    fields: tuple[str, ...] = ()
    values: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentBuildResult:
    """Resultado da montagem do documento."""

    document: FinalDocument | None
    issues: tuple[DocumentBuildIssue, ...]

    @property
    def is_built(self) -> bool:
        return self.document is not None

    @property
    def is_xml_ready(self) -> bool:
        return (
            self.document is not None
            and not any(
                issue.blocks_xml
                for issue in self.issues
            )
        )

    @property
    def blocks_apt(self) -> bool:
        return any(
            issue.blocks_apt
            for issue in self.issues
        )

    @property
    def blocking_xml_issues(
        self,
    ) -> tuple[DocumentBuildIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_xml
        )

    @property
    def apt_blocking_issues(
        self,
    ) -> tuple[DocumentBuildIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.blocks_apt
        )

    @property
    def issue_counts(
        self,
    ) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity] = (
                counts.get(issue.severity, 0) + 1
            )
        return MappingProxyType(counts)
