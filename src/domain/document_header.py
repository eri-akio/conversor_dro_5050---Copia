"""Modelo normalizado do cabeçalho do Documento 5050."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentHeader:
    """Cabeçalho pronto para ser usado pelas próximas etapas.

    Todos os valores desta classe já passaram pelas validações locais
    de formato e domínio implementadas na etapa 3.3.
    """

    codigo_documento: str
    data_base: str
    codigo_conglomerado: str
    cnpj: str
    tipo_remessa: str
    opcao_por_provisao_acumulada: str

    def as_xml_attributes(self) -> dict[str, str]:
        """Retorna os nomes exatos esperados no elemento ``documento``."""

        return {
            "codigoDocumento": self.codigo_documento,
            "dataBase": self.data_base,
            "codigoConglomerado": self.codigo_conglomerado,
            "cnpj": self.cnpj,
            "tipoRemessa": self.tipo_remessa,
            "opcaoPorProvisaoAcumulada": (
                self.opcao_por_provisao_acumulada
            ),
        }
