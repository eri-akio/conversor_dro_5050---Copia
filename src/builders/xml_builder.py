"""Construção da árvore XML a partir de ``FinalDocument``.

Este módulo somente cria uma árvore bem-formada. A validação contra o
XSD selecionado pertence à próxima etapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from lxml import etree

from src.config import XML_ENCODING
from src.domain.document_model import FinalDocument
from src.domain.xml_generation import XmlElementCounts


ROOT_TAG: Final[str] = "documento"


@dataclass(frozen=True, slots=True)
class XmlBuildError(Exception):
    """Falha técnica durante a criação da árvore XML."""

    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class XmlDocumentBuilder:
    """Monta a hierarquia definida nos XSDs fornecidos."""

    def build_tree(
        self,
        document: FinalDocument,
    ) -> etree._ElementTree:
        try:
            root = etree.Element(
                ROOT_TAG,
                attrib=document.as_xml_attributes(),
            )

            individualized = etree.SubElement(
                root,
                "eventosIndividualizados",
            )

            for event in document.individualized_events:
                event_element = etree.SubElement(
                    individualized,
                    "evento",
                    attrib=event.as_xml_attributes(),
                )

                if event.probabilities:
                    probabilities = etree.SubElement(
                        event_element,
                        "probabilidadesPerdas",
                    )

                    for probability in event.probabilities:
                        etree.SubElement(
                            probabilities,
                            "probabilidadePerda",
                            attrib=(
                                probability
                                .as_xml_attributes()
                            ),
                        )

                if event.accountings:
                    accountings = etree.SubElement(
                        event_element,
                        "contabilizacoes",
                    )

                    for accounting in event.accountings:
                        etree.SubElement(
                            accountings,
                            "contabilizacao",
                            attrib=(
                                accounting
                                .as_xml_attributes()
                            ),
                        )

            consolidated = etree.SubElement(
                root,
                "eventosConsolidados",
            )

            for event in document.consolidated_events:
                etree.SubElement(
                    consolidated,
                    "eventoConsolidado",
                    attrib=event.as_xml_attributes(),
                )

            systems = etree.SubElement(
                root,
                "sistemasOrigem",
            )

            for system in document.source_systems:
                etree.SubElement(
                    systems,
                    "sistema",
                    attrib=system.as_xml_attributes(),
                )

            accounts = etree.SubElement(
                root,
                "contasSubtitulosInternos",
            )

            for account in document.internal_accounts:
                etree.SubElement(
                    accounts,
                    "conta",
                    attrib=account.as_xml_attributes(),
                )

            return etree.ElementTree(root)

        except (
            TypeError,
            ValueError,
            etree.LxmlError,
        ) as error:
            raise XmlBuildError(
                code="XML-BUILD-001",
                message=(
                    "Não foi possível criar a árvore XML: "
                    f"{error}"
                ),
            ) from error

    def serialize(
        self,
        document: FinalDocument,
    ) -> bytes:
        """Serializa com declaração XML 1.0 e UTF-8."""

        tree = self.build_tree(document)

        try:
            xml_bytes = etree.tostring(
                tree,
                encoding=XML_ENCODING,
                xml_declaration=True,
                pretty_print=True,
            )

            if not xml_bytes.endswith(b"\n"):
                xml_bytes += b"\n"

            parser = etree.XMLParser(
                resolve_entities=False,
                no_network=True,
                recover=False,
            )
            etree.fromstring(
                xml_bytes,
                parser=parser,
            )

            return xml_bytes

        except (
            ValueError,
            etree.XMLSyntaxError,
            etree.LxmlError,
        ) as error:
            raise XmlBuildError(
                code="XML-BUILD-002",
                message=(
                    "A serialização não produziu um XML "
                    f"bem-formado: {error}"
                ),
            ) from error

    @staticmethod
    def count_elements(
        document: FinalDocument,
    ) -> XmlElementCounts:
        return XmlElementCounts(
            individualized_events=len(
                document.individualized_events
            ),
            probabilities=sum(
                len(event.probabilities)
                for event in (
                    document.individualized_events
                )
            ),
            accountings=sum(
                len(event.accountings)
                for event in (
                    document.individualized_events
                )
            ),
            consolidated_events=len(
                document.consolidated_events
            ),
            source_systems=len(
                document.source_systems
            ),
            internal_accounts=len(
                document.internal_accounts
            ),
        )


def serialize_final_document(
    document: FinalDocument,
) -> bytes:
    """Atalho funcional para a serialização em memória."""

    return XmlDocumentBuilder().serialize(document)
